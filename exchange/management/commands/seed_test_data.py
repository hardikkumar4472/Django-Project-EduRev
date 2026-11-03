import random
import uuid
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
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
    help = "Generates and seeds rich requests and proposals (pending, partially accepted, ready for warden approval, completed) strictly segregated by gender."

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear previously generated test proposals and requests (keeps core seeded users and system accounts)',
        )
        parser.add_argument(
            '--clear-expired',
            action='store_true',
            help='Clear only expired proposals (expires_at < now or status in EXPIRED/DECLINED) and their stale requests',
        )

    def handle(self, *args, **options):
        self.stdout.write("=================================================================")
        self.stdout.write("[START] Seeding Non-Expired Test Requests & Proposals (Strict Gender Enforced)")
        self.stdout.write("=================================================================")

        now = timezone.now()

        # -------------------------------------------------------------
        # CLEARING LOGIC
        # -------------------------------------------------------------
        if options.get('clear') or options.get('clear_expired'):
            self.stdout.write("Cleaning up expired/stale proposals and requests...")
            
            # Find expired or stale proposals
            if options.get('clear'):
                props_to_delete = ExchangeProposal.objects.filter(
                    Q(proposal_code__startswith="PROP-TEST-") |
                    Q(proposal_code__startswith="PROP-2026-") |
                    Q(proposal_code__startswith="PROP-WARDEN-") |
                    Q(status__in=[
                        ExchangeProposal.ProposalStatus.EXPIRED,
                        ExchangeProposal.ProposalStatus.DECLINED,
                        ExchangeProposal.ProposalStatus.PENDING_ACCEPTANCE,
                        ExchangeProposal.ProposalStatus.PARTIALLY_ACCEPTED,
                        ExchangeProposal.ProposalStatus.READY_FOR_APPROVAL,
                    ]) |
                    Q(expires_at__lt=now)
                ).exclude(status=ExchangeProposal.ProposalStatus.COMPLETED)
            else:
                props_to_delete = ExchangeProposal.objects.filter(
                    Q(status__in=[ExchangeProposal.ProposalStatus.EXPIRED, ExchangeProposal.ProposalStatus.DECLINED]) |
                    Q(expires_at__lt=now)
                ).exclude(status=ExchangeProposal.ProposalStatus.COMPLETED)

            prop_ids = list(props_to_delete.values_list('id', flat=True))
            self.stdout.write(f"  Found {len(prop_ids)} expired/stale proposals to delete.")

            # Reset or delete linked requests
            req_ids = list(ProposalParticipant.objects.filter(proposal_id__in=prop_ids).values_list('request_id', flat=True))
            req_ids = [r for r in req_ids if r]
            if req_ids:
                ExchangeRequest.objects.filter(id__in=req_ids).delete()
                self.stdout.write(f"  Removed {len(req_ids)} requests tied to expired proposals.")

            # Also remove explicitly expired or withdrawn requests
            stale_reqs = ExchangeRequest.objects.filter(
                Q(status__in=[ExchangeRequest.RequestStatus.EXPIRED, ExchangeRequest.RequestStatus.WITHDRAWN]) |
                (Q(expires_at__isnull=False) & Q(expires_at__lt=now))
            )
            stale_req_count = stale_reqs.count()
            stale_reqs.delete()
            if stale_req_count:
                self.stdout.write(f"  Removed {stale_req_count} explicitly expired/withdrawn requests.")

            # Delete the proposals
            props_to_delete.delete()
            self.stdout.write("  Proposal cleanup complete.")

        # Administrative / Staff users
        admin_user = User.objects.filter(role=User.Role.ADMIN).first()
        chief_warden = User.objects.filter(role=User.Role.CHIEF_WARDEN).first() or admin_user
        warden_bh1 = User.objects.filter(username__in=['warden_bh1', 'wardenbh1']).first()
        warden_bh2 = User.objects.filter(username__in=['warden_bh2', 'wardenbh2']).first()
        warden_gh1 = User.objects.filter(username__in=['warden_gh1', 'wardengh1']).first()
        warden_gh2 = User.objects.filter(username__in=['warden_gh2', 'wardengh2']).first()

        all_hostels = list(Hostel.objects.filter(is_active=True))
        if not all_hostels:
            self.stderr.write("No active hostels found in database. Run 'setup_hostels' first.")
            return

        bh_hostels = [h for h in all_hostels if h.gender_type == 'MALE']
        gh_hostels = [h for h in all_hostels if h.gender_type == 'FEMALE']

        # Helper to create or fetch a student allocated strictly to their gender-matching hostel
        def ensure_test_student(username, email, fn, ln, uid, gender, hostel, room_num, bed_idx=0):
            # Strict gender residency assertion
            if gender == User.Gender.MALE and hostel.gender_type != 'MALE':
                raise ValueError(f"CRITICAL: Attempted to assign Male student {username} to {hostel.name} ({hostel.gender_type})")
            if gender == User.Gender.FEMALE and hostel.gender_type != 'FEMALE':
                raise ValueError(f"CRITICAL: Attempted to assign Female student {username} to {hostel.name} ({hostel.gender_type})")

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

            # Ensure bed allocation adheres strictly to gender
            current_allocated_bed = getattr(stu, 'allocated_bed', None)
            if current_allocated_bed:
                # If current bed is in wrong gender hostel, deallocate it
                if current_allocated_bed.room.block.hostel.gender_type != ('MALE' if gender == User.Gender.MALE else 'FEMALE'):
                    current_allocated_bed.current_occupant = None
                    current_allocated_bed.occupancy_status = Bed.OccupancyStatus.VACANT
                    current_allocated_bed.save()
                    current_allocated_bed = None

            if not current_allocated_bed:
                # Find a bed in the target room or another vacant bed in that gender hostel
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
        # 1. SEED ACTIVE PROPOSALS (EXPIRY SET TO 14 DAYS IN FUTURE)
        # -------------------------------------------------------------------------
        self.stdout.write("1. Creating Non-Expired Proposals across all operational statuses...")
        proposal_expiry = now + timedelta(days=14)

        # -------------------------------------------------------------------------
        # A) BOYS PROPOSALS (BH-1 to BH-10 ONLY)
        # -------------------------------------------------------------------------
        
        # 1. BOYS: PENDING_ACCEPTANCE (2-Party Direct Swap BH-1 <-> BH-2)
        b_pend_1 = ensure_test_student('test_b_pend_1', 'b_pend_1@edurev.edu', 'Kabir', 'Mehra', '21BCE3001', User.Gender.MALE, bh_hostels[0], '204', 0)
        b_pend_2 = ensure_test_student('test_b_pend_2', 'b_pend_2@edurev.edu', 'Farhan', 'Qureshi', '21BCE3002', User.Gender.MALE, bh_hostels[1], '204', 0)

        req_bp_1, _ = ExchangeRequest.objects.get_or_create(
            requester=b_pend_1,
            defaults={'current_bed': b_pend_1.allocated_bed, 'preferred_hostel': bh_hostels[1], 'preferred_room_type': Room.RoomType.FOUR_SHARING, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "Closer to mechanical workshop"}
        )
        req_bp_2, _ = ExchangeRequest.objects.get_or_create(
            requester=b_pend_2,
            defaults={'current_bed': b_pend_2.allocated_bed, 'preferred_hostel': bh_hostels[0], 'preferred_room_type': Room.RoomType.FOUR_SHARING, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "Closer to central library"}
        )

        p_b_pending = ExchangeProposal.objects.create(
            proposal_code="PROP-TEST-PENDING-BH-01",
            proposal_type=ExchangeProposal.ProposalType.DIRECT,
            status=ExchangeProposal.ProposalStatus.PENDING_ACCEPTANCE,
            compatibility_score=95.0,
            expires_at=proposal_expiry
        )
        ProposalParticipant.objects.create(proposal=p_b_pending, student=b_pend_1, request=req_bp_1, current_bed=b_pend_1.allocated_bed, target_bed=b_pend_2.allocated_bed, response=ProposalParticipant.ParticipantResponse.PENDING, order_index=0)
        ProposalParticipant.objects.create(proposal=p_b_pending, student=b_pend_2, request=req_bp_2, current_bed=b_pend_2.allocated_bed, target_bed=b_pend_1.allocated_bed, response=ProposalParticipant.ParticipantResponse.PENDING, order_index=1)
        ProposalMessage.objects.create(proposal=p_b_pending, sender=b_pend_1, message="Hi Farhan! Just sent over the proposal. Let me know if you are good to accept!")
        self.stdout.write(f"  [+] Created BOYS PENDING_ACCEPTANCE: {p_b_pending.proposal_code}")

        # 2. BOYS: PARTIALLY_ACCEPTED (3-Party Cycle BH-3 -> BH-4 -> BH-5 -> BH-3)
        b_part_1 = ensure_test_student('test_b_part_1', 'b_part_1@edurev.edu', 'Rishi', 'Kapoor', '21BCE3011', User.Gender.MALE, bh_hostels[2], '205', 0)
        b_part_2 = ensure_test_student('test_b_part_2', 'b_part_2@edurev.edu', 'Abhimanyu', 'Das', '21BCE3012', User.Gender.MALE, bh_hostels[3], '205', 0)
        b_part_3 = ensure_test_student('test_b_part_3', 'b_part_3@edurev.edu', 'Samar', 'Anand', '21BCE3013', User.Gender.MALE, bh_hostels[4], '205', 0)

        req_bpart_1, _ = ExchangeRequest.objects.get_or_create(requester=b_part_1, defaults={'current_bed': b_part_1.allocated_bed, 'preferred_hostel': bh_hostels[3], 'preferred_room_type': Room.RoomType.SEVEN_SEATER, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "Boys 3-party cycle leg 1"})
        req_bpart_2, _ = ExchangeRequest.objects.get_or_create(requester=b_part_2, defaults={'current_bed': b_part_2.allocated_bed, 'preferred_hostel': bh_hostels[4], 'preferred_room_type': Room.RoomType.SEVEN_SEATER, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "Boys 3-party cycle leg 2"})
        req_bpart_3, _ = ExchangeRequest.objects.get_or_create(requester=b_part_3, defaults={'current_bed': b_part_3.allocated_bed, 'preferred_hostel': bh_hostels[2], 'preferred_room_type': Room.RoomType.SEVEN_SEATER, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "Boys 3-party cycle leg 3"})

        p_b_part = ExchangeProposal.objects.create(
            proposal_code="PROP-TEST-PARTIAL-BH-03",
            proposal_type=ExchangeProposal.ProposalType.CYCLE_3,
            status=ExchangeProposal.ProposalStatus.PARTIALLY_ACCEPTED,
            compatibility_score=92.0,
            expires_at=proposal_expiry
        )
        ProposalParticipant.objects.create(proposal=p_b_part, student=b_part_1, request=req_bpart_1, current_bed=b_part_1.allocated_bed, target_bed=b_part_2.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now - timedelta(hours=5), order_index=0)
        ProposalParticipant.objects.create(proposal=p_b_part, student=b_part_2, request=req_bpart_2, current_bed=b_part_2.allocated_bed, target_bed=b_part_3.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now - timedelta(hours=2), order_index=1)
        ProposalParticipant.objects.create(proposal=p_b_part, student=b_part_3, request=req_bpart_3, current_bed=b_part_3.allocated_bed, target_bed=b_part_1.allocated_bed, response=ProposalParticipant.ParticipantResponse.PENDING, order_index=2)
        ProposalMessage.objects.create(proposal=p_b_part, sender=b_part_1, message="I have accepted! Looking forward to moving to BH-4.")
        ProposalMessage.objects.create(proposal=p_b_part, sender=b_part_2, message="Accepted as well. Waiting on Samar!")
        self.stdout.write(f"  [+] Created BOYS PARTIALLY_ACCEPTED: {p_b_part.proposal_code}")

        # 3. BOYS: READY_FOR_APPROVAL (Same Hostel BH-1 Internal)
        b_ready_1 = ensure_test_student('test_b_ready_1', 'b_ready_1@edurev.edu', 'Vivaan', 'Shah', '21BCE3021', User.Gender.MALE, bh_hostels[0], '206', 0)
        b_ready_2 = ensure_test_student('test_b_ready_2', 'b_ready_2@edurev.edu', 'Shaurya', 'Bansal', '21BCE3022', User.Gender.MALE, bh_hostels[0], '306', 0)

        req_br_1, _ = ExchangeRequest.objects.get_or_create(requester=b_ready_1, defaults={'current_bed': b_ready_1.allocated_bed, 'preferred_hostel': bh_hostels[0], 'preferred_floor': 3, 'preferred_room_type': Room.RoomType.EIGHT_SEATER, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "BH-1 higher floor request"})
        req_br_2, _ = ExchangeRequest.objects.get_or_create(requester=b_ready_2, defaults={'current_bed': b_ready_2.allocated_bed, 'preferred_hostel': bh_hostels[0], 'preferred_floor': 2, 'preferred_room_type': Room.RoomType.EIGHT_SEATER, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "BH-1 lower floor request"})

        p_b_ready_single = ExchangeProposal.objects.create(
            proposal_code="PROP-TEST-READY-SINGLE-BH-07",
            proposal_type=ExchangeProposal.ProposalType.DIRECT,
            status=ExchangeProposal.ProposalStatus.READY_FOR_APPROVAL,
            compatibility_score=99.0,
            expires_at=proposal_expiry
        )
        ProposalParticipant.objects.create(proposal=p_b_ready_single, student=b_ready_1, request=req_br_1, current_bed=b_ready_1.allocated_bed, target_bed=b_ready_2.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now - timedelta(hours=1), order_index=0)
        ProposalParticipant.objects.create(proposal=p_b_ready_single, student=b_ready_2, request=req_br_2, current_bed=b_ready_2.allocated_bed, target_bed=b_ready_1.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now - timedelta(hours=1), order_index=1)
        self.stdout.write(f"  [+] Created BOYS READY_FOR_APPROVAL (Same Hostel): {p_b_ready_single.proposal_code}")

        # 4. BOYS: READY_FOR_APPROVAL (Cross-Hostel BH-1 & BH-2 with 1 Consent)
        b_cross_1 = ensure_test_student('test_b_cross_1', 'b_cross_1@edurev.edu', 'Nitin', 'Verma', '21BCE3031', User.Gender.MALE, bh_hostels[0], '202', 0)
        b_cross_2 = ensure_test_student('test_b_cross_2', 'b_cross_2@edurev.edu', 'Suresh', 'Raina', '21BCE3032', User.Gender.MALE, bh_hostels[1], '202', 0)

        req_bc_1, _ = ExchangeRequest.objects.get_or_create(requester=b_cross_1, defaults={'current_bed': b_cross_1.allocated_bed, 'preferred_hostel': bh_hostels[1], 'preferred_room_type': Room.RoomType.DOUBLE, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "BH-1 to BH-2 cross-hostel swap"})
        req_bc_2, _ = ExchangeRequest.objects.get_or_create(requester=b_cross_2, defaults={'current_bed': b_cross_2.allocated_bed, 'preferred_hostel': bh_hostels[0], 'preferred_room_type': Room.RoomType.DOUBLE, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "BH-2 to BH-1 cross-hostel swap"})

        p_b_ready_cross = ExchangeProposal.objects.create(
            proposal_code="PROP-TEST-READY-CROSS-BH-09",
            proposal_type=ExchangeProposal.ProposalType.DIRECT,
            status=ExchangeProposal.ProposalStatus.READY_FOR_APPROVAL,
            compatibility_score=97.0,
            expires_at=proposal_expiry
        )
        ProposalParticipant.objects.create(proposal=p_b_ready_cross, student=b_cross_1, request=req_bc_1, current_bed=b_cross_1.allocated_bed, target_bed=b_cross_2.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now - timedelta(hours=3), order_index=0)
        ProposalParticipant.objects.create(proposal=p_b_ready_cross, student=b_cross_2, request=req_bc_2, current_bed=b_cross_2.allocated_bed, target_bed=b_cross_1.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now - timedelta(hours=2), order_index=1)
        if warden_bh1:
            Approval.objects.create(proposal=p_b_ready_cross, approver=warden_bh1, decision=Approval.Decision.APPROVED, remarks="Consent approved by Warden BH-1. Awaiting Warden BH-2 / Chief Warden.")
        self.stdout.write(f"  [+] Created BOYS READY_FOR_APPROVAL (Cross-Hostel): {p_b_ready_cross.proposal_code}")

        # 5. BOYS: 4-PARTY CYCLE PENDING (BH-6 -> BH-7 -> BH-8 -> BH-9 -> BH-6)
        b_q_1 = ensure_test_student('test_b_q_1', 'b_q_1@edurev.edu', 'Zakir', 'Khan', '21BCE3041', User.Gender.MALE, bh_hostels[5], '104', 0)
        b_q_2 = ensure_test_student('test_b_q_2', 'b_q_2@edurev.edu', 'Biswa', 'Kalyan', '21BCE3042', User.Gender.MALE, bh_hostels[6], '104', 0)
        b_q_3 = ensure_test_student('test_b_q_3', 'b_q_3@edurev.edu', 'Kanan', 'Gill', '21BCE3043', User.Gender.MALE, bh_hostels[7], '104', 0)
        b_q_4 = ensure_test_student('test_b_q_4', 'b_q_4@edurev.edu', 'Kenny', 'Sebastian', '21BCE3044', User.Gender.MALE, bh_hostels[8], '104', 0)

        req_bq_1, _ = ExchangeRequest.objects.get_or_create(requester=b_q_1, defaults={'current_bed': b_q_1.allocated_bed, 'preferred_hostel': bh_hostels[6], 'preferred_room_type': Room.RoomType.FOUR_SHARING, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "Quad leg 1"})
        req_bq_2, _ = ExchangeRequest.objects.get_or_create(requester=b_q_2, defaults={'current_bed': b_q_2.allocated_bed, 'preferred_hostel': bh_hostels[7], 'preferred_room_type': Room.RoomType.FOUR_SHARING, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "Quad leg 2"})
        req_bq_3, _ = ExchangeRequest.objects.get_or_create(requester=b_q_3, defaults={'current_bed': b_q_3.allocated_bed, 'preferred_hostel': bh_hostels[8], 'preferred_room_type': Room.RoomType.FOUR_SHARING, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "Quad leg 3"})
        req_bq_4, _ = ExchangeRequest.objects.get_or_create(requester=b_q_4, defaults={'current_bed': b_q_4.allocated_bed, 'preferred_hostel': bh_hostels[5], 'preferred_room_type': Room.RoomType.FOUR_SHARING, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "Quad leg 4"})

        p_b_cycle4 = ExchangeProposal.objects.create(
            proposal_code="PROP-TEST-CYCLE4-BH-05",
            proposal_type=ExchangeProposal.ProposalType.CYCLE_4,
            status=ExchangeProposal.ProposalStatus.PENDING_ACCEPTANCE,
            compatibility_score=89.5,
            expires_at=proposal_expiry
        )
        ProposalParticipant.objects.create(proposal=p_b_cycle4, student=b_q_1, request=req_bq_1, current_bed=b_q_1.allocated_bed, target_bed=b_q_2.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now, order_index=0)
        ProposalParticipant.objects.create(proposal=p_b_cycle4, student=b_q_2, request=req_bq_2, current_bed=b_q_2.allocated_bed, target_bed=b_q_3.allocated_bed, response=ProposalParticipant.ParticipantResponse.PENDING, order_index=1)
        ProposalParticipant.objects.create(proposal=p_b_cycle4, student=b_q_3, request=req_bq_3, current_bed=b_q_3.allocated_bed, target_bed=b_q_4.allocated_bed, response=ProposalParticipant.ParticipantResponse.PENDING, order_index=2)
        ProposalParticipant.objects.create(proposal=p_b_cycle4, student=b_q_4, request=req_bq_4, current_bed=b_q_4.allocated_bed, target_bed=b_q_1.allocated_bed, response=ProposalParticipant.ParticipantResponse.PENDING, order_index=3)
        self.stdout.write(f"  [+] Created BOYS 4-PARTY CYCLE: {p_b_cycle4.proposal_code}")


        # -------------------------------------------------------------------------
        # B) GIRLS PROPOSALS (GH-1 to GH-10 ONLY)
        # -------------------------------------------------------------------------

        # 6. GIRLS: PENDING_ACCEPTANCE (2-Party Direct Swap GH-1 <-> GH-2)
        g_pend_1 = ensure_test_student('test_g_pend_1', 'g_pend_1@edurev.edu', 'Ananya', 'Sharma', '21BCE4011', User.Gender.FEMALE, gh_hostels[0], '204', 0)
        g_pend_2 = ensure_test_student('test_g_pend_2', 'g_pend_2@edurev.edu', 'Rhea', 'Sen', '21BCE4012', User.Gender.FEMALE, gh_hostels[1], '204', 0)

        req_gp_1, _ = ExchangeRequest.objects.get_or_create(
            requester=g_pend_1,
            defaults={'current_bed': g_pend_1.allocated_bed, 'preferred_hostel': gh_hostels[1], 'preferred_room_type': Room.RoomType.FOUR_SHARING, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "Girls exchange to GH-2"}
        )
        req_gp_2, _ = ExchangeRequest.objects.get_or_create(
            requester=g_pend_2,
            defaults={'current_bed': g_pend_2.allocated_bed, 'preferred_hostel': gh_hostels[0], 'preferred_room_type': Room.RoomType.FOUR_SHARING, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "Girls exchange to GH-1"}
        )

        p_g_pending = ExchangeProposal.objects.create(
            proposal_code="PROP-TEST-PENDING-GH-02",
            proposal_type=ExchangeProposal.ProposalType.DIRECT,
            status=ExchangeProposal.ProposalStatus.PENDING_ACCEPTANCE,
            compatibility_score=96.0,
            expires_at=proposal_expiry
        )
        ProposalParticipant.objects.create(proposal=p_g_pending, student=g_pend_1, request=req_gp_1, current_bed=g_pend_1.allocated_bed, target_bed=g_pend_2.allocated_bed, response=ProposalParticipant.ParticipantResponse.PENDING, order_index=0)
        ProposalParticipant.objects.create(proposal=p_g_pending, student=g_pend_2, request=req_gp_2, current_bed=g_pend_2.allocated_bed, target_bed=g_pend_1.allocated_bed, response=ProposalParticipant.ParticipantResponse.PENDING, order_index=1)
        ProposalMessage.objects.create(proposal=p_g_pending, sender=g_pend_1, message="Hi Rhea! Sent proposal for room exchange, please check and accept!")
        self.stdout.write(f"  [+] Created GIRLS PENDING_ACCEPTANCE: {p_g_pending.proposal_code}")

        # 7. GIRLS: PARTIALLY_ACCEPTED (3-Party Cycle GH-3 -> GH-4 -> GH-5 -> GH-3)
        g_part_1 = ensure_test_student('test_g_part_1', 'g_part_1@edurev.edu', 'Tanvi', 'Shah', '21BCE4021', User.Gender.FEMALE, gh_hostels[2], '205', 0)
        g_part_2 = ensure_test_student('test_g_part_2', 'g_part_2@edurev.edu', 'Priya', 'Iyer', '21BCE4022', User.Gender.FEMALE, gh_hostels[3], '205', 0)
        g_part_3 = ensure_test_student('test_g_part_3', 'g_part_3@edurev.edu', 'Shreya', 'Mehta', '21BCE4023', User.Gender.FEMALE, gh_hostels[4], '205', 0)

        req_gpart_1, _ = ExchangeRequest.objects.get_or_create(requester=g_part_1, defaults={'current_bed': g_part_1.allocated_bed, 'preferred_hostel': gh_hostels[3], 'preferred_room_type': Room.RoomType.SEVEN_SEATER, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "Girls cycle leg 1"})
        req_gpart_2, _ = ExchangeRequest.objects.get_or_create(requester=g_part_2, defaults={'current_bed': g_part_2.allocated_bed, 'preferred_hostel': gh_hostels[4], 'preferred_room_type': Room.RoomType.SEVEN_SEATER, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "Girls cycle leg 2"})
        req_gpart_3, _ = ExchangeRequest.objects.get_or_create(requester=g_part_3, defaults={'current_bed': g_part_3.allocated_bed, 'preferred_hostel': gh_hostels[2], 'preferred_room_type': Room.RoomType.SEVEN_SEATER, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "Girls cycle leg 3"})

        p_g_part = ExchangeProposal.objects.create(
            proposal_code="PROP-TEST-PARTIAL-GH-04",
            proposal_type=ExchangeProposal.ProposalType.CYCLE_3,
            status=ExchangeProposal.ProposalStatus.PARTIALLY_ACCEPTED,
            compatibility_score=94.5,
            expires_at=proposal_expiry
        )
        ProposalParticipant.objects.create(proposal=p_g_part, student=g_part_1, request=req_gpart_1, current_bed=g_part_1.allocated_bed, target_bed=g_part_2.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now - timedelta(hours=4), order_index=0)
        ProposalParticipant.objects.create(proposal=p_g_part, student=g_part_2, request=req_gpart_2, current_bed=g_part_2.allocated_bed, target_bed=g_part_3.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now - timedelta(hours=1), order_index=1)
        ProposalParticipant.objects.create(proposal=p_g_part, student=g_part_3, request=req_gpart_3, current_bed=g_part_3.allocated_bed, target_bed=g_part_1.allocated_bed, response=ProposalParticipant.ParticipantResponse.PENDING, order_index=2)
        ProposalMessage.objects.create(proposal=p_g_part, sender=g_part_1, message="Accepted! Tanvi ready to move.")
        self.stdout.write(f"  [+] Created GIRLS PARTIALLY_ACCEPTED: {p_g_part.proposal_code}")

        # 8. GIRLS: READY_FOR_APPROVAL (Same Hostel GH-1 Internal)
        g_ready_1 = ensure_test_student('test_g_ready_1', 'g_ready_1@edurev.edu', 'Sneha', 'Rao', '21BCE4031', User.Gender.FEMALE, gh_hostels[0], '206', 0)
        g_ready_2 = ensure_test_student('test_g_ready_2', 'g_ready_2@edurev.edu', 'Pooja', 'Hegde', '21BCE4032', User.Gender.FEMALE, gh_hostels[0], '306', 0)

        req_gr_1, _ = ExchangeRequest.objects.get_or_create(requester=g_ready_1, defaults={'current_bed': g_ready_1.allocated_bed, 'preferred_hostel': gh_hostels[0], 'preferred_floor': 3, 'preferred_room_type': Room.RoomType.EIGHT_SEATER, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "GH-1 floor change"})
        req_gr_2, _ = ExchangeRequest.objects.get_or_create(requester=g_ready_2, defaults={'current_bed': g_ready_2.allocated_bed, 'preferred_hostel': gh_hostels[0], 'preferred_floor': 2, 'preferred_room_type': Room.RoomType.EIGHT_SEATER, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "GH-1 floor change"})

        p_g_ready_single = ExchangeProposal.objects.create(
            proposal_code="PROP-TEST-READY-SINGLE-GH-08",
            proposal_type=ExchangeProposal.ProposalType.DIRECT,
            status=ExchangeProposal.ProposalStatus.READY_FOR_APPROVAL,
            compatibility_score=98.5,
            expires_at=proposal_expiry
        )
        ProposalParticipant.objects.create(proposal=p_g_ready_single, student=g_ready_1, request=req_gr_1, current_bed=g_ready_1.allocated_bed, target_bed=g_ready_2.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now - timedelta(hours=2), order_index=0)
        ProposalParticipant.objects.create(proposal=p_g_ready_single, student=g_ready_2, request=req_gr_2, current_bed=g_ready_2.allocated_bed, target_bed=g_ready_1.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now - timedelta(hours=1), order_index=1)
        self.stdout.write(f"  [+] Created GIRLS READY_FOR_APPROVAL (Same Hostel): {p_g_ready_single.proposal_code}")

        # 9. GIRLS: READY_FOR_APPROVAL (Cross-Hostel GH-1 & GH-2 with 1 Consent)
        g_cross_1 = ensure_test_student('test_g_cross_1', 'g_cross_1@edurev.edu', 'Ishita', 'Dutta', '21BCE4001', User.Gender.FEMALE, gh_hostels[0], '203', 0)
        g_cross_2 = ensure_test_student('test_g_cross_2', 'g_cross_2@edurev.edu', 'Dia', 'Mirza', '21BCE4002', User.Gender.FEMALE, gh_hostels[1], '203', 0)

        req_gc_1, _ = ExchangeRequest.objects.get_or_create(requester=g_cross_1, defaults={'current_bed': g_cross_1.allocated_bed, 'preferred_hostel': gh_hostels[1], 'preferred_room_type': Room.RoomType.TRIPLE, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "Girls exchange GH-1 to GH-2"})
        req_gc_2, _ = ExchangeRequest.objects.get_or_create(requester=g_cross_2, defaults={'current_bed': g_cross_2.allocated_bed, 'preferred_hostel': gh_hostels[0], 'preferred_room_type': Room.RoomType.TRIPLE, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "Girls exchange GH-2 to GH-1"})

        p_g_ready_cross = ExchangeProposal.objects.create(
            proposal_code="PROP-TEST-READY-CROSS-GH-10",
            proposal_type=ExchangeProposal.ProposalType.DIRECT,
            status=ExchangeProposal.ProposalStatus.READY_FOR_APPROVAL,
            compatibility_score=97.5,
            expires_at=proposal_expiry
        )
        ProposalParticipant.objects.create(proposal=p_g_ready_cross, student=g_cross_1, request=req_gc_1, current_bed=g_cross_1.allocated_bed, target_bed=g_cross_2.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now - timedelta(hours=3), order_index=0)
        ProposalParticipant.objects.create(proposal=p_g_ready_cross, student=g_cross_2, request=req_gc_2, current_bed=g_cross_2.allocated_bed, target_bed=g_cross_1.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now - timedelta(hours=2), order_index=1)
        if warden_gh1:
            Approval.objects.create(proposal=p_g_ready_cross, approver=warden_gh1, decision=Approval.Decision.APPROVED, remarks="Consent approved by Warden GH-1. Academic zero-dues verified.")
        self.stdout.write(f"  [+] Created GIRLS READY_FOR_APPROVAL (Cross-Hostel): {p_g_ready_cross.proposal_code}")

        # 10. GIRLS: 4-PARTY CYCLE PARTIALLY ACCEPTED (GH-6 -> GH-7 -> GH-8 -> GH-9 -> GH-6)
        g_q_1 = ensure_test_student('test_g_q_1', 'g_q_1@edurev.edu', 'Dolly', 'Singh', '21BCE4041', User.Gender.FEMALE, gh_hostels[5], '104', 0)
        g_q_2 = ensure_test_student('test_g_q_2', 'g_q_2@edurev.edu', 'Barkha', 'Singh', '21BCE4042', User.Gender.FEMALE, gh_hostels[6], '104', 0)
        g_q_3 = ensure_test_student('test_g_q_3', 'g_q_3@edurev.edu', 'Ahsaas', 'Channa', '21BCE4043', User.Gender.FEMALE, gh_hostels[7], '104', 0)
        g_q_4 = ensure_test_student('test_g_q_4', 'g_q_4@edurev.edu', 'Mithila', 'Palkar', '21BCE4044', User.Gender.FEMALE, gh_hostels[8], '104', 0)

        req_gq_1, _ = ExchangeRequest.objects.get_or_create(requester=g_q_1, defaults={'current_bed': g_q_1.allocated_bed, 'preferred_hostel': gh_hostels[6], 'preferred_room_type': Room.RoomType.FOUR_SHARING, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "Girls Quad leg 1"})
        req_gq_2, _ = ExchangeRequest.objects.get_or_create(requester=g_q_2, defaults={'current_bed': g_q_2.allocated_bed, 'preferred_hostel': gh_hostels[7], 'preferred_room_type': Room.RoomType.FOUR_SHARING, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "Girls Quad leg 2"})
        req_gq_3, _ = ExchangeRequest.objects.get_or_create(requester=g_q_3, defaults={'current_bed': g_q_3.allocated_bed, 'preferred_hostel': gh_hostels[8], 'preferred_room_type': Room.RoomType.FOUR_SHARING, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "Girls Quad leg 3"})
        req_gq_4, _ = ExchangeRequest.objects.get_or_create(requester=g_q_4, defaults={'current_bed': g_q_4.allocated_bed, 'preferred_hostel': gh_hostels[5], 'preferred_room_type': Room.RoomType.FOUR_SHARING, 'status': ExchangeRequest.RequestStatus.PROPOSED, 'reason': "Girls Quad leg 4"})

        p_g_cycle4 = ExchangeProposal.objects.create(
            proposal_code="PROP-TEST-CYCLE4-GH-06",
            proposal_type=ExchangeProposal.ProposalType.CYCLE_4,
            status=ExchangeProposal.ProposalStatus.PARTIALLY_ACCEPTED,
            compatibility_score=91.0,
            expires_at=proposal_expiry
        )
        ProposalParticipant.objects.create(proposal=p_g_cycle4, student=g_q_1, request=req_gq_1, current_bed=g_q_1.allocated_bed, target_bed=g_q_2.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now, order_index=0)
        ProposalParticipant.objects.create(proposal=p_g_cycle4, student=g_q_2, request=req_gq_2, current_bed=g_q_2.allocated_bed, target_bed=g_q_3.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now, order_index=1)
        ProposalParticipant.objects.create(proposal=p_g_cycle4, student=g_q_3, request=req_gq_3, current_bed=g_q_3.allocated_bed, target_bed=g_q_4.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=now, order_index=2)
        ProposalParticipant.objects.create(proposal=p_g_cycle4, student=g_q_4, request=req_gq_4, current_bed=g_q_4.allocated_bed, target_bed=g_q_1.allocated_bed, response=ProposalParticipant.ParticipantResponse.PENDING, order_index=3)
        self.stdout.write(f"  [+] Created GIRLS 4-PARTY CYCLE: {p_g_cycle4.proposal_code}")

        # -------------------------------------------------------------------------
        # 2. SEED ACTIVE REQUESTS FOR DISCOVERY IN CYCLE EXPLORER
        # (Strictly same gender: Boys -> BH, Girls -> GH)
        # -------------------------------------------------------------------------
        self.stdout.write("2. Seeding Active Candidate Requests for Cycle Explorer...")

        matching_scenarios = [
            # Boys 2-Party Match in Double rooms (BH-3 <-> BH-4)
            ('swap_bh3_d', 'swap_bh3_d@edurev.edu', 'Dhruv', 'Rathee', '21TST3101', User.Gender.MALE, bh_hostels[2], '102', 0, bh_hostels[3], Room.RoomType.DOUBLE, "Exchange to BH-4 double room"),
            ('swap_bh4_d', 'swap_bh4_d@edurev.edu', 'Gaurav', 'Chaudhary', '21TST3102', User.Gender.MALE, bh_hostels[3], '102', 0, bh_hostels[2], Room.RoomType.DOUBLE, "Exchange to BH-3 double room"),

            # Boys 3-Party Cycle in Triple rooms (BH-5 -> BH-6 -> BH-7 -> BH-5)
            ('cyc_bh5_t', 'cyc_bh5_t@edurev.edu', 'Abhi', 'Niyogi', '21TST3111', User.Gender.MALE, bh_hostels[4], '103', 0, bh_hostels[5], Room.RoomType.TRIPLE, "Triple cycle step 1"),
            ('cyc_bh6_t', 'cyc_bh6_t@edurev.edu', 'Niyu', 'Bhatt', '21TST3112', User.Gender.MALE, bh_hostels[5], '103', 0, bh_hostels[6], Room.RoomType.TRIPLE, "Triple cycle step 2"),
            ('cyc_bh7_t', 'cyc_bh7_t@edurev.edu', 'Ranveer', 'Allahbadia', '21TST3113', User.Gender.MALE, bh_hostels[6], '103', 0, bh_hostels[4], Room.RoomType.TRIPLE, "Triple cycle step 3"),

            # Girls 2-Party Match in GH-3 <-> GH-4 (Single room)
            ('swap_gh3_s', 'swap_gh3_s@edurev.edu', 'Prajakta', 'Koli', '21TST4101', User.Gender.FEMALE, gh_hostels[2], '101', 0, gh_hostels[3], Room.RoomType.SINGLE, "Wants GH-4 single room"),
            ('swap_gh4_s', 'swap_gh4_s@edurev.edu', 'Kusha', 'Kapila', '21TST4102', User.Gender.FEMALE, gh_hostels[3], '101', 0, gh_hostels[2], Room.RoomType.SINGLE, "Wants GH-3 single room"),

            # Girls 3-Party Cycle in GH-5 -> GH-6 -> GH-7 -> GH-5 (Triple room)
            ('cyc_gh5_t', 'cyc_gh5_t@edurev.edu', 'Kriti', 'Verma', '21TST4111', User.Gender.FEMALE, gh_hostels[4], '103', 0, gh_hostels[5], Room.RoomType.TRIPLE, "Girls triple cycle step 1"),
            ('cyc_gh6_t', 'cyc_gh6_t@edurev.edu', 'Juhi', 'Chawla', '21TST4112', User.Gender.FEMALE, gh_hostels[5], '103', 0, gh_hostels[6], Room.RoomType.TRIPLE, "Girls triple cycle step 2"),
            ('cyc_gh7_t', 'cyc_gh7_t@edurev.edu', 'Madhuri', 'Dixit', '21TST4113', User.Gender.FEMALE, gh_hostels[6], '103', 0, gh_hostels[4], Room.RoomType.TRIPLE, "Girls triple cycle step 3"),
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
            if not created and req.status != ExchangeRequest.RequestStatus.ACTIVE:
                req.current_bed = stu.allocated_bed
                req.preferred_hostel = target_hostel
                req.preferred_room_type = pref_type
                req.status = ExchangeRequest.RequestStatus.ACTIVE
                req.save()
            seeded_req_count += 1

        self.stdout.write(f"  [+] Seeded {seeded_req_count} structured matching requests across BH & GH.")

        # -------------------------------------------------------------------------
        # 3. SEED GENERAL HIGH-VOLUME ACTIVE POOL (STRICTLY SEGREGATED)
        # -------------------------------------------------------------------------
        self.stdout.write("3. Seeding wide pool of background active requests...")
        pool_names = [
            ("Hardik", "Agarwal", User.Gender.MALE),
            ("Aakash", "Trivedi", User.Gender.MALE),
            ("Sourabh", "Jain", User.Gender.MALE),
            ("Alok", "Nath", User.Gender.MALE),
            ("Mohit", "Chauhan", User.Gender.MALE),
            ("Pratik", "Gandhi", User.Gender.MALE),
            ("Manan", "Shah", User.Gender.MALE),
            ("Harshit", "Rana", User.Gender.MALE),
            ("Tanya", "Bhardwaj", User.Gender.FEMALE),
            ("Simran", "Bhatia", User.Gender.FEMALE),
            ("Kiran", "Bedi", User.Gender.FEMALE),
            ("Sonal", "Chauhan", User.Gender.FEMALE),
            ("Vidya", "Balan", User.Gender.FEMALE),
            ("Ritu", "Karidhal", User.Gender.FEMALE),
            ("Kalpana", "Chawla", User.Gender.FEMALE),
            ("Divya", "Dutta", User.Gender.FEMALE),
        ]

        for i, (p_fn, p_ln, p_gen) in enumerate(pool_names):
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
                        "Participating in study group with floor mates"
                    ])
                }
            )

        # -------------------------------------------------------------------------
        # 4. FINAL GENDER CONSISTENCY AUDIT
        # -------------------------------------------------------------------------
        self.stdout.write("4. Running Strict Gender Integrity Audit across all records...")
        violations = 0

        # Check all beds allocated to students
        for u in User.objects.filter(role=User.Role.STUDENT, allocated_bed__isnull=False):
            hostel = u.allocated_bed.room.block.hostel
            expected_gender = 'MALE' if u.gender == User.Gender.MALE else 'FEMALE'
            if hostel.gender_type != expected_gender:
                self.stderr.write(f"  [VIOLATION] Student {u.username} ({u.gender}) in {hostel.name} ({hostel.gender_type})")
                violations += 1

        # Check all proposals
        for p in ExchangeProposal.objects.all():
            part_genders = set()
            for part in p.participants.all():
                part_genders.add(part.student.gender)
                tb_hostel = part.target_bed.room.block.hostel if part.target_bed else None
                if tb_hostel:
                    expected = 'MALE' if part.student.gender == User.Gender.MALE else 'FEMALE'
                    if tb_hostel.gender_type != expected:
                        self.stderr.write(f"  [VIOLATION] Proposal {p.proposal_code} assigns {part.student.username} ({part.student.gender}) to {tb_hostel.name} ({tb_hostel.gender_type})")
                        violations += 1
            if len(part_genders) > 1:
                self.stderr.write(f"  [VIOLATION] Proposal {p.proposal_code} has mixed genders: {part_genders}")
                violations += 1

        if violations == 0:
            self.stdout.write(self.style.SUCCESS("  [PASS] ZERO Gender Residency Policy Violations. All Male->Boys, Female->Girls!"))
        else:
            self.stderr.write(f"  [FAIL] Detected {violations} gender violations!")

        # -------------------------------------------------------------------------
        # 5. SUMMARY REPORT
        # -------------------------------------------------------------------------
        total_proposals = ExchangeProposal.objects.count()
        active_proposals = ExchangeProposal.objects.filter(expires_at__gt=now).exclude(status=ExchangeProposal.ProposalStatus.COMPLETED).count()
        total_requests = ExchangeRequest.objects.count()
        active_requests = ExchangeRequest.objects.filter(status=ExchangeRequest.RequestStatus.ACTIVE).count()

        self.stdout.write("=================================================================")
        self.stdout.write(self.style.SUCCESS("[COMPLETED] Data Generation & Seeding Successful!"))
        self.stdout.write("=================================================================")
        self.stdout.write(f"Total Proposals: {total_proposals} (Active/Non-Expired: {active_proposals})")
        self.stdout.write(f"Total Requests: {total_requests} (Active for matching: {active_requests})")
        self.stdout.write("=================================================================")
