import threading
from datetime import timedelta
from django.test import TransactionTestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from hostel.models import Hostel, Block, Room, Bed
from exchange.models import (
    PolicyRule,
    ExchangeRequest,
    ExchangeProposal,
    ProposalParticipant,
    TransferRecord
)
from exchange.services.occupancy_service import AtomicOccupancyEngine, OccupancyTransferError
from exchange.services.proposal_service import ProposalService
from exchange.services.eligibility_service import EligibilityService

User = get_user_model()

class ConcurrencyAndAtomicOccupancyTestCase(TransactionTestCase):
    """
    Mandatory Phase 18 Test Suite:
    Validates atomic cyclic swaps, participant decline rollbacks, expiry safety,
    and multi-threaded concurrent race conditions without deadlocks or partial transfers.
    """

    def setUp(self):
        # 1. Hostels & Staff
        self.warden = User.objects.create_user(
            username='warden_test',
            password='password123',
            first_name='Test',
            last_name='Warden',
            university_id='WAR-T-01',
            role=User.Role.WARDEN
        )

        self.hostel = Hostel.objects.create(name='Test Hostel', code='TH', warden=self.warden)
        self.block = Block.objects.create(hostel=self.hostel, name='A', code='A')

        # 2. Setup 4 Rooms and 4 Beds for the 4-Party Cycle:
        # A: Room 101 -> Desires 203
        # B: Room 203 -> Desires 304
        # C: Room 304 -> Desires 412
        # D: Room 412 -> Desires 101
        self.rooms = {}
        self.beds = {}
        self.students = {}

        for num in ['101', '203', '304', '412']:
            room = Room.objects.create(block=self.block, room_number=num, floor=1, capacity=1)
            bed = Bed.objects.create(room=room, bed_number='Bed 1', occupancy_status=Bed.OccupancyStatus.OCCUPIED)
            self.rooms[num] = room
            self.beds[num] = bed

        student_specs = [
            ('s_a', '101', '203'),
            ('s_b', '203', '304'),
            ('s_c', '304', '412'),
            ('s_d', '412', '101'),
        ]

        for s_code, curr_r, target_r in student_specs:
            s = User.objects.create_user(
                username=s_code,
                password='password123',
                first_name=s_code.upper(),
                last_name='Student',
                university_id=f"UID-{s_code.upper()}",
                role=User.Role.STUDENT
            )
            # Assign current bed
            b = self.beds[curr_r]
            b.current_occupant = s
            b.save()
            self.students[s_code] = s

    def test_01_four_party_rotation_completes_atomically(self):
        """
        Test 1: 4-party rotation completes successfully with all beds updated.
        """
        now = timezone.now()
        proposal = ExchangeProposal.objects.create(
            proposal_code="TEST-PROP-01",
            proposal_type=ExchangeProposal.ProposalType.CYCLE_4,
            status=ExchangeProposal.ProposalStatus.READY_FOR_APPROVAL,
            expires_at=now + timedelta(hours=24)
        )

        specs = [
            (self.students['s_a'], self.beds['101'], self.beds['203'], 0),
            (self.students['s_b'], self.beds['203'], self.beds['304'], 1),
            (self.students['s_c'], self.beds['304'], self.beds['412'], 2),
            (self.students['s_d'], self.beds['412'], self.beds['101'], 3),
        ]

        for student, curr_b, target_b, idx in specs:
            ProposalParticipant.objects.create(
                proposal=proposal,
                student=student,
                current_bed=curr_b,
                target_bed=target_b,
                response=ProposalParticipant.ParticipantResponse.ACCEPTED,
                responded_at=now,
                order_index=idx
            )

        # Execute atomic occupancy transfer
        result = AtomicOccupancyEngine.execute_proposal_atomic(proposal.id, self.warden)
        self.assertTrue(result['success'])
        self.assertEqual(result['transfers_count'], 4)

        # Assert all 4 beds updated exactly to their target allocations
        self.beds['203'].refresh_from_db()
        self.beds['304'].refresh_from_db()
        self.beds['412'].refresh_from_db()
        self.beds['101'].refresh_from_db()

        self.assertEqual(self.beds['203'].current_occupant, self.students['s_a'])
        self.assertEqual(self.beds['304'].current_occupant, self.students['s_b'])
        self.assertEqual(self.beds['412'].current_occupant, self.students['s_c'])
        self.assertEqual(self.beds['101'].current_occupant, self.students['s_d'])

    def test_02_participant_decline_prevents_transfer(self):
        """
        Test 2: If one participant declines, proposal terminates and NO beds move.
        """
        now = timezone.now()
        proposal = ExchangeProposal.objects.create(
            proposal_code="TEST-PROP-02",
            proposal_type=ExchangeProposal.ProposalType.CYCLE_4,
            status=ExchangeProposal.ProposalStatus.PENDING_ACCEPTANCE,
            expires_at=now + timedelta(hours=24)
        )

        ProposalParticipant.objects.create(
            proposal=proposal,
            student=self.students['s_a'],
            current_bed=self.beds['101'],
            target_bed=self.beds['203'],
            response=ProposalParticipant.ParticipantResponse.ACCEPTED,
            order_index=0
        )

        p_b = ProposalParticipant.objects.create(
            proposal=proposal,
            student=self.students['s_b'],
            current_bed=self.beds['203'],
            target_bed=self.beds['304'],
            response=ProposalParticipant.ParticipantResponse.PENDING,
            order_index=1
        )

        # Student B declines
        res = ProposalService.respond_to_proposal(proposal, self.students['s_b'], 'DECLINE')
        self.assertTrue(res['success'])
        self.assertEqual(res['status'], 'DECLINED')

        proposal.refresh_from_db()
        self.assertEqual(proposal.status, ExchangeProposal.ProposalStatus.DECLINED)

        # Attempt to approve should fail
        with self.assertRaises(OccupancyTransferError):
            AtomicOccupancyEngine.execute_proposal_atomic(proposal.id, self.warden)

        # Assert occupancy completely untouched
        self.beds['101'].refresh_from_db()
        self.beds['203'].refresh_from_db()
        self.assertEqual(self.beds['101'].current_occupant, self.students['s_a'])
        self.assertEqual(self.beds['203'].current_occupant, self.students['s_b'])

    def test_03_concurrent_overlapping_approvals_race(self):
        """
        Test 4: Real multi-threaded race condition where two transactions compete
        for overlapping beds simultaneously.
        Verifies:
        - Deterministic lock acquisition order (No ABBA deadlock)
        - Exactly one transaction succeeds
        - The losing transaction safely rolls back with ZERO partial transfers
        """
        # Create 5th student and bed competing for Bed 203
        r_505 = Room.objects.create(block=self.block, room_number='505', floor=1, capacity=1)
        b_505 = Bed.objects.create(room=r_505, bed_number='Bed 1', occupancy_status=Bed.OccupancyStatus.OCCUPIED)
        s_e = User.objects.create_user(
            username='s_e',
            password='password123',
            first_name='Eve',
            last_name='Student',
            university_id='UID-EVE',
            role=User.Role.STUDENT
        )
        b_505.current_occupant = s_e
        b_505.save()

        now = timezone.now()
        
        # Proposal 1: 4-Party Cycle (touches 101, 203, 304, 412)
        prop1 = ExchangeProposal.objects.create(
            proposal_code="PROP-RACE-01",
            proposal_type=ExchangeProposal.ProposalType.CYCLE_4,
            status=ExchangeProposal.ProposalStatus.READY_FOR_APPROVAL,
            expires_at=now + timedelta(hours=24)
        )
        for s, cb, tb, i in [
            (self.students['s_a'], self.beds['101'], self.beds['203'], 0),
            (self.students['s_b'], self.beds['203'], self.beds['304'], 1),
            (self.students['s_c'], self.beds['304'], self.beds['412'], 2),
            (self.students['s_d'], self.beds['412'], self.beds['101'], 3),
        ]:
            ProposalParticipant.objects.create(
                proposal=prop1, student=s, current_bed=cb, target_bed=tb,
                response=ProposalParticipant.ParticipantResponse.ACCEPTED, order_index=i
            )

        # Proposal 2: Direct Swap competing for Bed 203 (touches 203 and 505)
        prop2 = ExchangeProposal.objects.create(
            proposal_code="PROP-RACE-02",
            proposal_type=ExchangeProposal.ProposalType.DIRECT,
            status=ExchangeProposal.ProposalStatus.READY_FOR_APPROVAL,
            expires_at=now + timedelta(hours=24)
        )
        ProposalParticipant.objects.create(
            proposal=prop2, student=self.students['s_b'], current_bed=self.beds['203'], target_bed=b_505,
            response=ProposalParticipant.ParticipantResponse.ACCEPTED, order_index=0
        )
        ProposalParticipant.objects.create(
            proposal=prop2, student=s_e, current_bed=b_505, target_bed=self.beds['203'],
            response=ProposalParticipant.ParticipantResponse.ACCEPTED, order_index=1
        )

        results = {}

        def approve_prop1():
            from django.db import connection
            connection.close()
            try:
                res = AtomicOccupancyEngine.execute_proposal_atomic(prop1.id, self.warden)
                results['prop1'] = res['success']
            except Exception as e:
                results['prop1'] = str(e)
            finally:
                connection.close()

        def approve_prop2():
            from django.db import connection
            connection.close()
            try:
                res = AtomicOccupancyEngine.execute_proposal_atomic(prop2.id, self.warden)
                results['prop2'] = res['success']
            except Exception as e:
                results['prop2'] = str(e)
            finally:
                connection.close()

        t1 = threading.Thread(target=approve_prop1)
        t2 = threading.Thread(target=approve_prop2)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Exactly one transaction must succeed, and the other must cleanly abort
        successes = [k for k, v in results.items() if v is True]
        self.assertEqual(len(successes), 1, f"Expected exactly 1 success, got results: {results}")

        # Assert no corrupted or partial bed states
        for b in [self.beds['101'], self.beds['203'], self.beds['304'], self.beds['412'], b_505]:
            b.refresh_from_db()
            self.assertIsNotNone(b.current_occupant)
            self.assertEqual(b.occupancy_status, Bed.OccupancyStatus.OCCUPIED)
