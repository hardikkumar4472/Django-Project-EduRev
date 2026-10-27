import random
import uuid
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from hostel.models import Hostel, Room, Bed
from exchange.models import (
    ExchangeRequest,
    ExchangeProposal,
    ProposalParticipant,
    Approval,
    TransferRecord,
    AuditEntry,
    ProposalMessage,
    StudentLifestyle,
    Notification
)

User = get_user_model()

class Command(BaseCommand):
    help = "Generates and seeds rich requests, proposals (all statuses: pending, partially accepted, ready for warden approval, approved, declined, expired, completed), messages, notifications, and transfer records for testing."

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear previously generated test proposals and requests (keeps core seeded users and system accounts)',
        )

    def handle(self, *args, **options):
        self.stdout.write("=================================================================")
        self.stdout.write("[START] Generating and Seeding Test Requests, Proposals & Scenarios")
        self.stdout.write("=================================================================")

        now = timezone.now()

        # Administrative / Staff users
        admin_user = User.objects.filter(role=User.Role.ADMIN).first()
        chief_warden = User.objects.filter(role=User.Role.CHIEF_WARDEN).first() or admin_user
        warden_bh1 = User.objects.filter(username__in=['warden_bh1', 'wardenbh1']).first()
        warden_bh2 = User.objects.filter(username__in=['warden_bh2', 'wardenbh2']).first()
        warden_bh3 = User.objects.filter(username__in=['warden_bh3', 'wardenbh3']).first()
        warden_gh1 = User.objects.filter(username__in=['warden_gh1', 'wardengh1']).first()
        warden_gh2 = User.objects.filter(username__in=['warden_gh2', 'wardengh2']).first()

        all_hostels = list(Hostel.objects.filter(is_active=True))
        if not all_hostels:
            self.stderr.write("No active hostels found in database. Run 'setup_hostels' first.")
            return

        bh_hostels = [h for h in all_hostels if h.gender_type == 'MALE']
        gh_hostels = [h for h in all_hostels if h.gender_type == 'FEMALE']

        # Helper to create or fetch a student allocated to a bed
        def ensure_test_student(username, email, fn, ln, uid, gender, hostel, room_num, bed_idx=0):
            stu = User.objects.filter(username=username).first() or User.objects.filter(university_id=uid).first()
            if not stu:
                stu = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=fn,
                    last_name=ln,
                    university_id=uid,
                    role=User.Role.STUDENT,
                    gender=gender
                )
                stu.set_password('student@123')
            else:
                stu.username = username
                stu.email = email
                stu.first_name = fn
                stu.last_name = ln
                stu.gender = gender
                stu.role = User.Role.STUDENT
            
            stu.has_fee_clearance = True
            stu.has_disciplinary_hold = False
            stu.save()

            # Ensure bed allocation
            if not getattr(stu, 'allocated_bed', None):
                # Find a vacant bed in the specified hostel room or any vacant bed in that hostel
                room = Room.objects.filter(block__hostel=hostel, room_number=room_num).first()
                bed = None
                if room:
                    bed = room.beds.filter(occupancy_status=Bed.OccupancyStatus.VACANT).first()
                if not bed:
                    bed = Bed.objects.filter(room__block__hostel=hostel, occupancy_status=Bed.OccupancyStatus.VACANT).first()
                if bed:
                    bed.current_occupant = stu
                    bed.occupancy_status = Bed.OccupancyStatus.OCCUPIED
                    bed.save()

            # Lifestyle
            StudentLifestyle.objects.get_or_create(
                student=stu,
                defaults={
                    'sleep_schedule': random.choice(StudentLifestyle.SleepSchedule.values),
                    'study_habit': random.choice(StudentLifestyle.StudyHabit.values),
                    'ac_preference': random.choice(StudentLifestyle.ACPreference.values),
                    'cleanliness': random.choice(StudentLifestyle.Cleanliness.values),
                    'hobbies': random.choice(["Coding, Robotics, Chess", "Gaming, Anime, Gym", "Music, Photography, Reading"])
                }
            )
            return stu

        # -------------------------------------------------------------------------
        # 1. SEED DIVERSE PROPOSALS ACROSS DIFFERENT WORKFLOW STATES
        # -------------------------------------------------------------------------
        self.stdout.write("1. Creating Proposals in all operational statuses...")

        # A) PENDING_ACCEPTANCE: Fresh 2-Party Direct Swap awaiting response
        s_pend_a = ensure_test_student('test_pend_a', 'test_pend_a@edurev.edu', 'Kabir', 'Mehra', '21BCE3001', User.Gender.MALE, bh_hostels[0], '204', 0)
        s_pend_b = ensure_test_student('test_pend_b', 'test_pend_b@edurev.edu', 'Farhan', 'Qureshi', '21BCE3002', User.Gender.MALE, bh_hostels[1], '204', 0)

        req_p_a, _ = ExchangeRequest.objects.get_or_create(
            requester=s_pend_a,
            defaults={
                'current_bed': s_pend_a.allocated_bed,
                'preferred_hostel': bh_hostels[1],
                'preferred_room_type': Room.RoomType.FOUR_SHARING,
                'status': ExchangeRequest.RequestStatus.PROPOSED,
                'reason': "Closer to mechanical engineering workshop"
            }
        )
        req_p_b, _ = ExchangeRequest.objects.get_or_create(
            requester=s_pend_b,
            defaults={
                'current_bed': s_pend_b.allocated_bed,
                'preferred_hostel': bh_hostels[0],
                'preferred_room_type': Room.RoomType.FOUR_SHARING,
                'status': ExchangeRequest.RequestStatus.PROPOSED,
                'reason': "Closer to university library"
            }
        )

        p_pending, created = ExchangeProposal.objects.get_or_create(
            proposal_code="PROP-TEST-PENDING-01",
            defaults={
                'proposal_type': ExchangeProposal.ProposalType.DIRECT,
                'status': ExchangeProposal.ProposalStatus.PENDING_ACCEPTANCE,
                'compatibility_score': 95.0,
                'expires_at': now + timedelta(hours=44)
            }
        )
        if created:
            ProposalParticipant.objects.create(
                proposal=p_pending, student=s_pend_a, request=req_p_a,
                current_bed=s_pend_a.allocated_bed, target_bed=s_pend_b.allocated_bed,
                response=ProposalParticipant.ParticipantResponse.PENDING, order_index=0
            )
            ProposalParticipant.objects.create(
                proposal=p_pending, student=s_pend_b, request=req_p_b,
                current_bed=s_pend_b.allocated_bed, target_bed=s_pend_a.allocated_bed,
                response=ProposalParticipant.ParticipantResponse.PENDING, order_index=1
            )
            ProposalMessage.objects.create(
                proposal=p_pending,
                sender=s_pend_a,
                message="Hi Farhan! Just sent over the proposal. Let me know if you are good to accept!"
            )
            Notification.objects.create(
                recipient=s_pend_b,
                title="New Exchange Proposal Received",
                message=f"You received an exchange proposal from {s_pend_a.get_full_name()} ({p_pending.proposal_code}).",
                notification_type=Notification.NotificationType.PROPOSAL_RECEIVED,
                link=f"/proposals/{p_pending.id}/"
            )
        self.stdout.write(f"  [+] Created PENDING_ACCEPTANCE Proposal: {p_pending.proposal_code}")

        # B) PARTIALLY_ACCEPTED: 3-Party Cycle with 2 accepted, 1 pending
        s_part_1 = ensure_test_student('test_part_1', 'test_part_1@edurev.edu', 'Rishi', 'Kapoor', '21BCE3011', User.Gender.MALE, bh_hostels[2], '205', 0)
        s_part_2 = ensure_test_student('test_part_2', 'test_part_2@edurev.edu', 'Abhimanyu', 'Das', '21BCE3012', User.Gender.MALE, bh_hostels[3], '205', 0)
        s_part_3 = ensure_test_student('test_part_3', 'test_part_3@edurev.edu', 'Samar', 'Anand', '21BCE3013', User.Gender.MALE, bh_hostels[4], '205', 0)

        req_part_1, _ = ExchangeRequest.objects.get_or_create(requester=s_part_1, defaults={'current_bed': s_part_1.allocated_bed, 'preferred_hostel': bh_hostels[3], 'preferred_room_type': Room.RoomType.SEVEN_SEATER, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "3-party cycle leg 1"})
        req_part_2, _ = ExchangeRequest.objects.get_or_create(requester=s_part_2, defaults={'current_bed': s_part_2.allocated_bed, 'preferred_hostel': bh_hostels[4], 'preferred_room_type': Room.RoomType.SEVEN_SEATER, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "3-party cycle leg 2"})
        req_part_3, _ = ExchangeRequest.objects.get_or_create(requester=s_part_3, defaults={'current_bed': s_part_3.allocated_bed, 'preferred_hostel': bh_hostels[2], 'preferred_room_type': Room.RoomType.SEVEN_SEATER, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "3-party cycle leg 3"})

        p_partially, created = ExchangeProposal.objects.get_or_create(
            proposal_code="PROP-TEST-PARTIAL-02",
            defaults={
                'proposal_type': ExchangeProposal.ProposalType.CYCLE_3,
                'status': ExchangeProposal.ProposalStatus.PARTIALLY_ACCEPTED,
                'compatibility_score': 91.5,
                'expires_at': now + timedelta(hours=30)
            }
        )
        if created:
            ProposalParticipant.objects.create(proposal=p_partially, student=s_part_1, request=req_part_1, current_bed=s_part_1.allocated_bed, target_bed=s_part_2.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now - timedelta(hours=5), order_index=0)
            ProposalParticipant.objects.create(proposal=p_partially, student=s_part_2, request=req_part_2, current_bed=s_part_2.allocated_bed, target_bed=s_part_3.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now - timedelta(hours=2), order_index=1)
            ProposalParticipant.objects.create(proposal=p_partially, student=s_part_3, request=req_part_3, current_bed=s_part_3.allocated_bed, target_bed=s_part_1.allocated_bed, response=ProposalParticipant.ParticipantResponse.PENDING, order_index=2)
            ProposalMessage.objects.create(proposal=p_partially, sender=s_part_1, message="I have accepted! Looking forward to the move.")
            ProposalMessage.objects.create(proposal=p_partially, sender=s_part_2, message="Accepted as well. Waiting on Samar!")
        self.stdout.write(f"  [+] Created PARTIALLY_ACCEPTED Proposal: {p_partially.proposal_code}")

        # C) READY_FOR_APPROVAL: All Accepted Direct Swap (Single Hostel BH-1 Internal)
        # Allows testing Warden of BH-1 or Chief Warden single-click direct execution!
        s_ready_a = ensure_test_student('test_ready_a', 'test_ready_a@edurev.edu', 'Vivaan', 'Shah', '21BCE3021', User.Gender.MALE, bh_hostels[0], '206', 0)
        s_ready_b = ensure_test_student('test_ready_b', 'test_ready_b@edurev.edu', 'Shaurya', 'Bansal', '21BCE3022', User.Gender.MALE, bh_hostels[0], '306', 0)

        req_ready_a, _ = ExchangeRequest.objects.get_or_create(requester=s_ready_a, defaults={'current_bed': s_ready_a.allocated_bed, 'preferred_hostel': bh_hostels[0], 'preferred_floor': 3, 'preferred_room_type': Room.RoomType.EIGHT_SEATER, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "Same hostel, requesting higher floor 3"})
        req_ready_b, _ = ExchangeRequest.objects.get_or_create(requester=s_ready_b, defaults={'current_bed': s_ready_b.allocated_bed, 'preferred_hostel': bh_hostels[0], 'preferred_floor': 2, 'preferred_room_type': Room.RoomType.EIGHT_SEATER, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "Same hostel, requesting lower floor 2"})

        p_ready_single, created = ExchangeProposal.objects.get_or_create(
            proposal_code="PROP-TEST-READY-SINGLE-03",
            defaults={
                'proposal_type': ExchangeProposal.ProposalType.DIRECT,
                'status': ExchangeProposal.ProposalStatus.READY_FOR_APPROVAL,
                'compatibility_score': 99.0,
                'expires_at': now + timedelta(hours=48)
            }
        )
        if created:
            ProposalParticipant.objects.create(proposal=p_ready_single, student=s_ready_a, request=req_ready_a, current_bed=s_ready_a.allocated_bed, target_bed=s_ready_b.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now - timedelta(hours=1), order_index=0)
            ProposalParticipant.objects.create(proposal=p_ready_single, student=s_ready_b, request=req_ready_b, current_bed=s_ready_b.allocated_bed, target_bed=s_ready_a.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now - timedelta(hours=1), order_index=1)
            ProposalMessage.objects.create(proposal=p_ready_single, sender=s_ready_a, message="Both of us have accepted! Warden approval is pending.")
        self.stdout.write(f"  [+] Created READY_FOR_APPROVAL (Same Hostel) Proposal: {p_ready_single.proposal_code}")

        # D) READY_FOR_APPROVAL (Girls Hostels GH-1 & GH-2 Multi-Hop Cycle with 1 Warden Signed Off)
        # Perfect for testing cross-hostel consent workflow!
        g_ready_1 = ensure_test_student('test_g_ready_1', 'test_g_ready_1@edurev.edu', 'Ishita', 'Dutta', '21BCE4001', User.Gender.FEMALE, gh_hostels[0], '203', 0)
        g_ready_2 = ensure_test_student('test_g_ready_2', 'test_g_ready_2@edurev.edu', 'Dia', 'Mirza', '21BCE4002', User.Gender.FEMALE, gh_hostels[1], '203', 0)

        req_g_1, _ = ExchangeRequest.objects.get_or_create(requester=g_ready_1, defaults={'current_bed': g_ready_1.allocated_bed, 'preferred_hostel': gh_hostels[1], 'preferred_room_type': Room.RoomType.TRIPLE, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "Girls inter-hostel exchange to GH-2"})
        req_g_2, _ = ExchangeRequest.objects.get_or_create(requester=g_ready_2, defaults={'current_bed': g_ready_2.allocated_bed, 'preferred_hostel': gh_hostels[0], 'preferred_room_type': Room.RoomType.TRIPLE, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "Girls inter-hostel exchange to GH-1"})

        p_ready_cross, created = ExchangeProposal.objects.get_or_create(
            proposal_code="PROP-TEST-READY-CROSS-04",
            defaults={
                'proposal_type': ExchangeProposal.ProposalType.DIRECT,
                'status': ExchangeProposal.ProposalStatus.READY_FOR_APPROVAL,
                'compatibility_score': 97.5,
                'expires_at': now + timedelta(hours=40)
            }
        )
        if created:
            ProposalParticipant.objects.create(proposal=p_ready_cross, student=g_ready_1, request=req_g_1, current_bed=g_ready_1.allocated_bed, target_bed=g_ready_2.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now - timedelta(hours=3), order_index=0)
            ProposalParticipant.objects.create(proposal=p_ready_cross, student=g_ready_2, request=req_g_2, current_bed=g_ready_2.allocated_bed, target_bed=g_ready_1.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now - timedelta(hours=2), order_index=1)
            # Warden GH-1 already granted consent! Waiting for Warden GH-2:
            if warden_gh1:
                Approval.objects.create(
                    proposal=p_ready_cross,
                    approver=warden_gh1,
                    decision=Approval.Decision.APPROVED,
                    remarks="Consent granted by Warden GH-1. Academic zero-dues cleared."
                )
        self.stdout.write(f"  [+] Created READY_FOR_APPROVAL (Cross-Hostel GH-1 & GH-2 with 1 consent) Proposal: {p_ready_cross.proposal_code}")

        # E) DECLINED Proposal for history & rejection analytics
        s_dec_a = ensure_test_student('test_dec_a', 'test_dec_a@edurev.edu', 'Harsh', 'Vardhan', '21BCE3031', User.Gender.MALE, bh_hostels[1], '205', 0)
        s_dec_b = ensure_test_student('test_dec_b', 'test_dec_b@edurev.edu', 'Prateek', 'Khurana', '21BCE3032', User.Gender.MALE, bh_hostels[2], '205', 0)

        p_declined, created = ExchangeProposal.objects.get_or_create(
            proposal_code="PROP-TEST-DECLINED-05",
            defaults={
                'proposal_type': ExchangeProposal.ProposalType.DIRECT,
                'status': ExchangeProposal.ProposalStatus.DECLINED,
                'compatibility_score': 82.0,
                'expires_at': now - timedelta(days=2)
            }
        )
        if created:
            ProposalParticipant.objects.create(proposal=p_declined, student=s_dec_a, current_bed=s_dec_a.allocated_bed, target_bed=s_dec_b.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now - timedelta(days=3), order_index=0)
            ProposalParticipant.objects.create(proposal=p_declined, student=s_dec_b, current_bed=s_dec_b.allocated_bed, target_bed=s_dec_a.allocated_bed, response=ProposalParticipant.ParticipantResponse.DECLINED, responded_at=now - timedelta(days=2), order_index=1)
            ProposalMessage.objects.create(proposal=p_declined, sender=s_dec_b, message="Sorry Harsh, I found an alternate room partner in my block.")
        self.stdout.write(f"  [+] Created DECLINED Proposal: {p_declined.proposal_code}")

        # F) EXPIRED Proposal
        s_exp_a = ensure_test_student('test_exp_a', 'test_exp_a@edurev.edu', 'Nakul', 'Garg', '21BCE3041', User.Gender.MALE, bh_hostels[3], '206', 0)
        s_exp_b = ensure_test_student('test_exp_b', 'test_exp_b@edurev.edu', 'Sahil', 'Taneja', '21BCE3042', User.Gender.MALE, bh_hostels[4], '206', 0)

        p_expired, created = ExchangeProposal.objects.get_or_create(
            proposal_code="PROP-TEST-EXPIRED-06",
            defaults={
                'proposal_type': ExchangeProposal.ProposalType.DIRECT,
                'status': ExchangeProposal.ProposalStatus.EXPIRED,
                'compatibility_score': 85.0,
                'expires_at': now - timedelta(days=1)
            }
        )
        if created:
            ProposalParticipant.objects.create(proposal=p_expired, student=s_exp_a, current_bed=s_exp_a.allocated_bed, target_bed=s_exp_b.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now - timedelta(days=3), order_index=0)
            ProposalParticipant.objects.create(proposal=p_expired, student=s_exp_b, current_bed=s_exp_b.allocated_bed, target_bed=s_exp_a.allocated_bed, response=ProposalParticipant.ParticipantResponse.PENDING, order_index=1)
        self.stdout.write(f"  [+] Created EXPIRED Proposal: {p_expired.proposal_code}")

        # G) COMPLETED Proposals with TransferRecords (For QR passes and Transfer History)
        s_comp_1 = ensure_test_student('test_comp_1', 'test_comp_1@edurev.edu', 'Karan', 'Johar', '21BCE3051', User.Gender.MALE, bh_hostels[5], '101', 0)
        s_comp_2 = ensure_test_student('test_comp_2', 'test_comp_2@edurev.edu', 'Varun', 'Dhawan', '21BCE3052', User.Gender.MALE, bh_hostels[6], '101', 0)

        p_completed, created = ExchangeProposal.objects.get_or_create(
            proposal_code="PROP-TEST-COMPLETED-07",
            defaults={
                'proposal_type': ExchangeProposal.ProposalType.DIRECT,
                'status': ExchangeProposal.ProposalStatus.COMPLETED,
                'compatibility_score': 100.0,
                'expires_at': now - timedelta(days=4),
                'completed_at': now - timedelta(days=4)
            }
        )
        if created:
            ProposalParticipant.objects.create(proposal=p_completed, student=s_comp_1, current_bed=s_comp_1.allocated_bed, target_bed=s_comp_2.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now - timedelta(days=5), order_index=0)
            ProposalParticipant.objects.create(proposal=p_completed, student=s_comp_2, current_bed=s_comp_2.allocated_bed, target_bed=s_comp_1.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now - timedelta(days=5), order_index=1)
            Approval.objects.create(proposal=p_completed, approver=chief_warden, decision=Approval.Decision.APPROVED, remarks="Official transfer verified and authorized.")
            TransferRecord.objects.get_or_create(
                transfer_code="TRF-TEST-2026-001",
                defaults={
                    'proposal': p_completed,
                    'student': s_comp_1,
                    'previous_bed': s_comp_1.allocated_bed,
                    'new_bed': s_comp_2.allocated_bed,
                    'approved_by': chief_warden,
                    'verification_token': uuid.uuid4()
                }
            )
            TransferRecord.objects.get_or_create(
                transfer_code="TRF-TEST-2026-002",
                defaults={
                    'proposal': p_completed,
                    'student': s_comp_2,
                    'previous_bed': s_comp_2.allocated_bed,
                    'new_bed': s_comp_1.allocated_bed,
                    'approved_by': chief_warden,
                    'verification_token': uuid.uuid4()
                }
            )
        self.stdout.write(f"  [+] Created COMPLETED Proposal with Transfer Records: {p_completed.proposal_code}")

        # -------------------------------------------------------------------------
        # 2. SEED ACTIVE REQUESTS ACROSS VARIOUS ROOM TYPES & HOSTELS
        # (Creates plenty of candidate matches for the Cycle Explorer)
        # -------------------------------------------------------------------------
        self.stdout.write("2. Generating Active Requests for Cycle Match Explorer...")
        
        # Create pairwise and cyclic matching students across BH and GH
        matching_scenarios = [
            # 2-Party Match in Double rooms (BH-3 <-> BH-4)
            ('swap_bh3_d', 'swap_bh3_d@edurev.edu', 'Dhruv', 'Rathee', '21TST3101', User.Gender.MALE, bh_hostels[2], '102', 0, bh_hostels[3], Room.RoomType.DOUBLE, "Exchange to BH-4 double room"),
            ('swap_bh4_d', 'swap_bh4_d@edurev.edu', 'Gaurav', 'Chaudhary', '21TST3102', User.Gender.MALE, bh_hostels[3], '102', 0, bh_hostels[2], Room.RoomType.DOUBLE, "Exchange to BH-3 double room"),

            # 3-Party Cycle in Triple rooms (BH-5 -> BH-6 -> BH-7 -> BH-5)
            ('cyc_bh5_t', 'cyc_bh5_t@edurev.edu', 'Abhi', 'Niyogi', '21TST3111', User.Gender.MALE, bh_hostels[4], '103', 0, bh_hostels[5], Room.RoomType.TRIPLE, "Triple cycle step 1"),
            ('cyc_bh6_t', 'cyc_bh6_t@edurev.edu', 'Niyu', 'Bhatt', '21TST3112', User.Gender.MALE, bh_hostels[5], '103', 0, bh_hostels[6], Room.RoomType.TRIPLE, "Triple cycle step 2"),
            ('cyc_bh7_t', 'cyc_bh7_t@edurev.edu', 'Ranveer', 'Allahbadia', '21TST3113', User.Gender.MALE, bh_hostels[6], '103', 0, bh_hostels[4], Room.RoomType.TRIPLE, "Triple cycle step 3"),

            # 4-Party Cycle in 4-Sharing Quad (BH-7 -> BH-8 -> BH-9 -> BH-10 -> BH-7)
            ('cyc_bh7_q', 'cyc_bh7_q@edurev.edu', 'Zakir', 'Khan', '21TST3121', User.Gender.MALE, bh_hostels[6], '104', 0, bh_hostels[7], Room.RoomType.FOUR_SHARING, "Quad cycle step 1"),
            ('cyc_bh8_q', 'cyc_bh8_q@edurev.edu', 'Biswa', 'Kalyan', '21TST3122', User.Gender.MALE, bh_hostels[7], '104', 0, bh_hostels[8], Room.RoomType.FOUR_SHARING, "Quad cycle step 2"),
            ('cyc_bh9_q', 'cyc_bh9_q@edurev.edu', 'Kanan', 'Gill', '21TST3123', User.Gender.MALE, bh_hostels[8], '104', 0, bh_hostels[9], Room.RoomType.FOUR_SHARING, "Quad cycle step 3"),
            ('cyc_bh10_q', 'cyc_bh10_q@edurev.edu', 'Kenny', 'Sebastian', '21TST3124', User.Gender.MALE, bh_hostels[9], '104', 0, bh_hostels[6], Room.RoomType.FOUR_SHARING, "Quad cycle step 4"),

            # Girls 2-Party Match in GH-3 <-> GH-4 (Single room)
            ('swap_gh3_s', 'swap_gh3_s@edurev.edu', 'Prajakta', 'Koli', '21TST4101', User.Gender.FEMALE, gh_hostels[2], '101', 0, gh_hostels[3], Room.RoomType.SINGLE, "Wants GH-4 single room"),
            ('swap_gh4_s', 'swap_gh4_s@edurev.edu', 'Kusha', 'Kapila', '21TST4102', User.Gender.FEMALE, gh_hostels[3], '101', 0, gh_hostels[2], Room.RoomType.SINGLE, "Wants GH-3 single room"),

            # Girls 3-Party Cycle in GH-5 -> GH-6 -> GH-7 -> GH-5 (Triple room)
            ('cyc_gh5_t', 'cyc_gh5_t@edurev.edu', 'Dolly', 'Singh', '21TST4111', User.Gender.FEMALE, gh_hostels[4], '103', 0, gh_hostels[5], Room.RoomType.TRIPLE, "Girls triple cycle step 1"),
            ('cyc_gh6_t', 'cyc_gh6_t@edurev.edu', 'Barkha', 'Singh', '21TST4112', User.Gender.FEMALE, gh_hostels[5], '103', 0, gh_hostels[6], Room.RoomType.TRIPLE, "Girls triple cycle step 2"),
            ('cyc_gh7_t', 'cyc_gh7_t@edurev.edu', 'Ahsaas', 'Channa', '21TST4113', User.Gender.FEMALE, gh_hostels[6], '103', 0, gh_hostels[4], Room.RoomType.TRIPLE, "Girls triple cycle step 3"),
        ]

        seeded_req_count = 0
        for uname, uemail, ufn, uln, uuid_str, ugen, uhostel, uroom, ubed_idx, target_hostel, pref_type, reason_str in matching_scenarios:
            stu = ensure_test_student(uname, uemail, ufn, uln, uuid_str, ugen, uhostel, uroom, ubed_idx)
            req, created = ExchangeRequest.objects.get_or_create(
                requester=stu,
                defaults={
                    'current_bed': stu.allocated_bed,
                    'preferred_hostel': target_hostel,
                    'preferred_room_type': pref_type,
                    'status': ExchangeRequest.RequestStatus.ACTIVE,
                    'reason': reason_str
                }
            )
            if created or req.status != ExchangeRequest.RequestStatus.ACTIVE:
                req.current_bed = stu.allocated_bed
                req.preferred_hostel = target_hostel
                req.preferred_room_type = pref_type
                req.status = ExchangeRequest.RequestStatus.ACTIVE
                req.save()
            seeded_req_count += 1

        self.stdout.write(f"  [+] Seeded {seeded_req_count} structured matching requests across BH & GH.")

        # -------------------------------------------------------------------------
        # 3. SEED GENERAL HIGH-VOLUME ACTIVE POOL FOR FILTERING & CHARTS
        # -------------------------------------------------------------------------
        self.stdout.write("3. Seeding wide pool of background active requests for statistics & filters...")
        pool_names = [
            ("Hardik", "Agarwal"), ("Aakash", "Trivedi"), ("Sourabh", "Jain"), ("Alok", "Nath"),
            ("Mohit", "Chauhan"), ("Tanya", "Bhardwaj"), ("Simran", "Bhatia"), ("Kiran", "Bedi"),
            ("Sonal", "Chauhan"), ("Vidya", "Balan"), ("Ritu", "Karidhal"), ("Kalpana", "Chawla"),
            ("Jayesh", "Bhatt"), ("Manan", "Shah"), ("Pratik", "Gandhi"), ("Harshit", "Rana")
        ]

        for i, (p_fn, p_ln) in enumerate(pool_names):
            p_gen = User.Gender.MALE if i < 8 else User.Gender.FEMALE
            p_hostel_pool = bh_hostels if p_gen == User.Gender.MALE else gh_hostels
            p_curr_h = p_hostel_pool[i % len(p_hostel_pool)]
            p_tgt_h = p_hostel_pool[(i + 1) % len(p_hostel_pool)]
            
            p_room_num = f"{random.choice([1, 2, 3])}{random.choice([1, 2, 3, 4, 5, 6]):02d}"
            p_uname = f"test_pool_{i+1:02d}"
            p_stu = ensure_test_student(
                p_uname, f"{p_uname}@edurev.edu", p_fn, p_ln, f"21BCE5{i+100:03d}", p_gen, p_curr_h, p_room_num, 0
            )

            ExchangeRequest.objects.get_or_create(
                requester=p_stu,
                defaults={
                    'current_bed': p_stu.allocated_bed,
                    'preferred_hostel': p_tgt_h,
                    'preferred_room_type': p_stu.allocated_bed.room.room_type if p_stu.allocated_bed else Room.RoomType.DOUBLE,
                    'preferred_floor': random.choice([1, 2, 3]),
                    'status': ExchangeRequest.RequestStatus.ACTIVE,
                    'reason': random.choice([
                        "Prefers room nearer to department seminar hall",
                        "Seeking room on same floor as peer mentor",
                        "Desires morning sunlight and better ventilation",
                        "Participating in cross-hostel hackathon team"
                    ])
                }
            )

        # -------------------------------------------------------------------------
        # 4. SUMMARY REPORT
        # -------------------------------------------------------------------------
        total_users = User.objects.count()
        total_students = User.objects.filter(role=User.Role.STUDENT).count()
        total_requests = ExchangeRequest.objects.count()
        total_proposals = ExchangeProposal.objects.count()
        total_transfers = TransferRecord.objects.count()
        total_approvals = Approval.objects.count()

        proposals_by_status = {s[0]: ExchangeProposal.objects.filter(status=s[0]).count() for s in ExchangeProposal.ProposalStatus.choices}
        requests_by_status = {r[0]: ExchangeRequest.objects.filter(status=r[0]).count() for r in ExchangeRequest.RequestStatus.choices}

        self.stdout.write("=================================================================")
        self.stdout.write(self.style.SUCCESS("[COMPLETED] Test Data Generation & Seeding Successful!"))
        self.stdout.write("=================================================================")
        self.stdout.write(f"Total Users: {total_users} (Students: {total_students})")
        self.stdout.write(f"Total Exchange Requests: {total_requests}")
        self.stdout.write(f"  - Requests breakdown: {requests_by_status}")
        self.stdout.write(f"Total Exchange Proposals: {total_proposals}")
        self.stdout.write(f"  - Proposals breakdown: {proposals_by_status}")
        self.stdout.write(f"Total Completed Transfers: {total_transfers}")
        self.stdout.write(f"Total Approval Sign-offs: {total_approvals}")
        self.stdout.write("=================================================================")
        self.stdout.write("Key Test Personas & Proposals ready to test:")
        self.stdout.write("1. 'student' / 'student@123' -> Aarav Sharma (Active search in BH-1)")
        self.stdout.write("2. 'warden_bh1' / 'wardenbh1@123' -> Can view single & cross-hostel approval queue")
        self.stdout.write("3. 'chief_warden' / 'chief_warden@123' -> Can execute proposals")
        self.stdout.write("4. 'PROP-TEST-PENDING-01' -> Test student acceptance & chat")
        self.stdout.write("5. 'PROP-TEST-PARTIAL-02' -> Test 3-party voting progress")
        self.stdout.write("6. 'PROP-TEST-READY-SINGLE-03' -> Test same-hostel instant Warden execution")
        self.stdout.write("7. 'PROP-TEST-READY-CROSS-04' -> Test cross-hostel dual Warden consent")
        self.stdout.write("8. 'TRF-TEST-2026-001' & 'TRF-2026-618921' -> Test QR Verification Scanner")
        self.stdout.write("=================================================================")
