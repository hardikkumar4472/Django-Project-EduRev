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
    TransferRecord
)

User = get_user_model()

class Command(BaseCommand):
    help = "Seeds comprehensive realistic student cohort and multi-capacity exchange cycles across hostels"

    def handle(self, *args, **options):
        self.stdout.write("Initializing bulk student cohort and exchange network...")

        # 1. Clean existing proposals and requests to avoid deadlocks/conflicts
        ProposalParticipant.objects.all().delete()
        ExchangeProposal.objects.all().delete()
        ExchangeRequest.objects.all().delete()

        # Clean old demo student accounts (preserving core accounts: student, wardens, admin, dsw)
        core_usernames = {
            'student', 'admin', 'dsw', 'chief_warden', 'warden',
            'wardenbh1', 'wardenbh2', 'wardenbh3', 'wardenbh4', 'wardenbh5',
            'wardenbh6', 'wardenbh7', 'wardenbh8', 'wardenbh9', 'wardenbh10',
            'wardengh1', 'wardengh2', 'wardengh3', 'wardengh4', 'wardengh5',
            'wardengh6', 'wardengh7', 'wardengh8', 'wardengh9', 'wardengh10',
        }
        old_students = User.objects.filter(role=User.Role.STUDENT).exclude(username__in=core_usernames)
        for s in old_students:
            if hasattr(s, 'allocated_bed') and s.allocated_bed:
                bed = s.allocated_bed
                bed.current_occupant = None
                bed.occupancy_status = Bed.OccupancyStatus.VACANT
                bed.save()
            s.delete()

        # 2. Re-verify primary 'student' account in BH-1 Block A Room 101 Bed 1
        main_student = User.objects.filter(username='student').first()
        if not main_student:
            main_student = User.objects.create_user(
                username='student',
                email='student@gmail.com',
                first_name='Aarav',
                last_name='Sharma',
                university_id='21BCE1001',
                role=User.Role.STUDENT,
                gender=User.Gender.MALE
            )
            main_student.set_password('student@123')
        main_student.has_fee_clearance = True
        main_student.has_disciplinary_hold = False
        main_student.save()

        # Ensure main student has their bed allocated in BH-1 Room 101
        bh1 = Hostel.objects.filter(code='BH-1').first()
        bh2 = Hostel.objects.filter(code='BH-2').first()
        bh3 = Hostel.objects.filter(code='BH-3').first()
        bh4 = Hostel.objects.filter(code='BH-4').first()
        gh1 = Hostel.objects.filter(code='GH-1').first()
        gh2 = Hostel.objects.filter(code='GH-2').first()
        gh3 = Hostel.objects.filter(code='GH-3').first()

        room_bh1_101 = Room.objects.filter(block__hostel=bh1, room_number='101').first()
        if room_bh1_101:
            bed = room_bh1_101.beds.first()
            if bed:
                # Clear if occupied by someone else
                if bed.current_occupant and bed.current_occupant != main_student:
                    bed.current_occupant = None
                bed.current_occupant = main_student
                bed.occupancy_status = Bed.OccupancyStatus.OCCUPIED
                bed.save()

        # Main student active request: seeking BH-2 Single Room
        ExchangeRequest.objects.create(
            requester=main_student,
            current_bed=main_student.allocated_bed,
            preferred_hostel=bh2,
            preferred_room_type='SINGLE',
            reason="Looking to swap to BH-2 closer to engineering lecture halls.",
            status=ExchangeRequest.RequestStatus.ACTIVE
        )
        self.stdout.write("[OK] Verified primary student (Aarav Sharma) in BH-1 Room 101 with active request.")

        # Helper to create and allocate a student
        def create_resident(username, email, fname, lname, uid, gender, hostel, room_num, bed_num_idx=0):
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=fname,
                last_name=lname,
                university_id=uid,
                role=User.Role.STUDENT,
                gender=gender
            )
            user.set_password('student@123')
            user.has_fee_clearance = True
            user.has_disciplinary_hold = False
            user.save()

            room = Room.objects.filter(block__hostel=hostel, room_number=room_num).first()
            if room:
                beds = list(room.beds.filter(occupancy_status=Bed.OccupancyStatus.VACANT))
                if beds and bed_num_idx < len(beds):
                    bed_obj = beds[bed_num_idx]
                    bed_obj.current_occupant = user
                    bed_obj.occupancy_status = Bed.OccupancyStatus.OCCUPIED
                    bed_obj.save()
            return user

        # ---------------------------------------------------------------------
        # 3. Boys Hostel Cycles & Direct Swaps
        # ---------------------------------------------------------------------
        # (A) Single Seater Match for main_student:
        # student_bh2 in BH-2 Room 101 (Single) -> wants BH-1
        s_bh2 = create_resident('student_bh2', 'student_bh2@gmail.com', 'Rohan', 'Verma', '21BCE1002', User.Gender.MALE, bh2, '101')
        ExchangeRequest.objects.create(
            requester=s_bh2,
            current_bed=s_bh2.allocated_bed,
            preferred_hostel=bh1,
            preferred_room_type='SINGLE',
            reason="Requesting transfer to BH-1 to join robotics project lab.",
            status=ExchangeRequest.RequestStatus.ACTIVE
        )

        # student_bh3 in BH-3 Room 101 (Single) -> wants BH-2 (creates 3-party loop: BH-1 -> BH-2 -> BH-3 -> BH-1)
        s_bh3 = create_resident('student_bh3', 'student_bh3@gmail.com', 'Siddharth', 'Mehta', '21BCE1003', User.Gender.MALE, bh3, '101')
        ExchangeRequest.objects.create(
            requester=s_bh3,
            current_bed=s_bh3.allocated_bed,
            preferred_hostel=bh1,
            preferred_room_type='SINGLE',
            reason="Departmental study group coordination in BH-1.",
            status=ExchangeRequest.RequestStatus.ACTIVE
        )

        # (B) 2-Seater (Double) Direct Pair:
        # boy_double_1 in BH-1 Room 102 <-> boy_double_2 in BH-2 Room 102
        bd1 = create_resident('boy_double_1', 'boy_double_1@gmail.com', 'Kunal', 'Kapoor', '21BCE1010', User.Gender.MALE, bh1, '102', 0)
        bd2 = create_resident('boy_double_2', 'boy_double_2@gmail.com', 'Vikram', 'Patel', '21BCE1011', User.Gender.MALE, bh2, '102', 0)
        ExchangeRequest.objects.create(
            requester=bd1,
            current_bed=bd1.allocated_bed,
            preferred_hostel=bh2,
            preferred_room_type='DOUBLE',
            reason="Seeking double room accommodation in BH-2.",
            status=ExchangeRequest.RequestStatus.ACTIVE
        )
        ExchangeRequest.objects.create(
            requester=bd2,
            current_bed=bd2.allocated_bed,
            preferred_hostel=bh1,
            preferred_room_type='DOUBLE',
            reason="Seeking double room accommodation in BH-1.",
            status=ExchangeRequest.RequestStatus.ACTIVE
        )

        # (C) 3-Seater (Triple) 3-Party Cycle:
        # bt1 (BH-1) -> wants BH-2 | bt2 (BH-2) -> wants BH-3 | bt3 (BH-3) -> wants BH-1
        bt1 = create_resident('boy_triple_1', 'boy_triple_1@gmail.com', 'Aditya', 'Gupta', '21BCE1020', User.Gender.MALE, bh1, '103', 0)
        bt2 = create_resident('boy_triple_2', 'boy_triple_2@gmail.com', 'Naveen', 'Chopra', '21BCE1021', User.Gender.MALE, bh2, '103', 0)
        bt3 = create_resident('boy_triple_3', 'boy_triple_3@gmail.com', 'Varun', 'Saxena', '21BCE1022', User.Gender.MALE, bh3, '103', 0)
        ExchangeRequest.objects.create(requester=bt1, current_bed=bt1.allocated_bed, preferred_hostel=bh2, preferred_room_type='TRIPLE', reason="Swap to BH-2 triple room", status=ExchangeRequest.RequestStatus.ACTIVE)
        ExchangeRequest.objects.create(requester=bt2, current_bed=bt2.allocated_bed, preferred_hostel=bh3, preferred_room_type='TRIPLE', reason="Swap to BH-3 triple room", status=ExchangeRequest.RequestStatus.ACTIVE)
        ExchangeRequest.objects.create(requester=bt3, current_bed=bt3.allocated_bed, preferred_hostel=bh1, preferred_room_type='TRIPLE', reason="Swap to BH-1 triple room", status=ExchangeRequest.RequestStatus.ACTIVE)

        # (D) 4-Seater (Quad) 4-Party Cycle:
        bq1 = create_resident('boy_quad_1', 'boy_quad_1@gmail.com', 'Arjun', 'Reddy', '21BCE1030', User.Gender.MALE, bh1, '104', 0)
        bq2 = create_resident('boy_quad_2', 'boy_quad_2@gmail.com', 'Manish', 'Iyer', '21BCE1031', User.Gender.MALE, bh2, '104', 0)
        bq3 = create_resident('boy_quad_3', 'boy_quad_3@gmail.com', 'Rahul', 'Singh', '21BCE1032', User.Gender.MALE, bh3, '104', 0)
        bq4 = create_resident('boy_quad_4', 'boy_quad_4@gmail.com', 'Deepak', 'Mishra', '21BCE1033', User.Gender.MALE, bh4, '104', 0)
        ExchangeRequest.objects.create(requester=bq1, current_bed=bq1.allocated_bed, preferred_hostel=bh2, preferred_room_type='FOUR_SHARING', reason="Quad swap leg 1", status=ExchangeRequest.RequestStatus.ACTIVE)
        ExchangeRequest.objects.create(requester=bq2, current_bed=bq2.allocated_bed, preferred_hostel=bh3, preferred_room_type='FOUR_SHARING', reason="Quad swap leg 2", status=ExchangeRequest.RequestStatus.ACTIVE)
        ExchangeRequest.objects.create(requester=bq3, current_bed=bq3.allocated_bed, preferred_hostel=bh4, preferred_room_type='FOUR_SHARING', reason="Quad swap leg 3", status=ExchangeRequest.RequestStatus.ACTIVE)
        ExchangeRequest.objects.create(requester=bq4, current_bed=bq4.allocated_bed, preferred_hostel=bh1, preferred_room_type='FOUR_SHARING', reason="Quad swap leg 4", status=ExchangeRequest.RequestStatus.ACTIVE)

        # (E) 7-Seater and 8-Seater Dormitory Swaps:
        bd7_1 = create_resident('boy_dorm7_1', 'boy_dorm7_1@gmail.com', 'Amit', 'Kumar', '21BCE1040', User.Gender.MALE, bh1, '105', 0)
        bd7_2 = create_resident('boy_dorm7_2', 'boy_dorm7_2@gmail.com', 'Gaurav', 'Joshi', '21BCE1041', User.Gender.MALE, bh2, '105', 0)
        ExchangeRequest.objects.create(requester=bd7_1, current_bed=bd7_1.allocated_bed, preferred_hostel=bh2, preferred_room_type='SEVEN_SEATER', reason="7-seater dorm swap", status=ExchangeRequest.RequestStatus.ACTIVE)
        ExchangeRequest.objects.create(requester=bd7_2, current_bed=bd7_2.allocated_bed, preferred_hostel=bh1, preferred_room_type='SEVEN_SEATER', reason="7-seater dorm swap", status=ExchangeRequest.RequestStatus.ACTIVE)

        bd8_1 = create_resident('boy_dorm8_1', 'boy_dorm8_1@gmail.com', 'Tanmay', 'Bhatia', '21BCE1050', User.Gender.MALE, bh1, '106', 0)
        bd8_2 = create_resident('boy_dorm8_2', 'boy_dorm8_2@gmail.com', 'Harsh', 'Vardhan', '21BCE1051', User.Gender.MALE, bh2, '106', 0)
        ExchangeRequest.objects.create(requester=bd8_1, current_bed=bd8_1.allocated_bed, preferred_hostel=bh2, preferred_room_type='EIGHT_SEATER', reason="8-seater dorm swap", status=ExchangeRequest.RequestStatus.ACTIVE)
        ExchangeRequest.objects.create(requester=bd8_2, current_bed=bd8_2.allocated_bed, preferred_hostel=bh1, preferred_room_type='EIGHT_SEATER', reason="8-seater dorm swap", status=ExchangeRequest.RequestStatus.ACTIVE)

        # ---------------------------------------------------------------------
        # 4. Girls Hostel Cycles & Direct Swaps
        # ---------------------------------------------------------------------
        # (A) Single Seater Direct Pair:
        gs1 = create_resident('girl_single_1', 'girl_single_1@gmail.com', 'Ananya', 'Sharma', '21BCE2001', User.Gender.FEMALE, gh1, '101', 0)
        gs2 = create_resident('girl_single_2', 'girl_single_2@gmail.com', 'Pooja', 'Singh', '21BCE2002', User.Gender.FEMALE, gh2, '101', 0)
        ExchangeRequest.objects.create(requester=gs1, current_bed=gs1.allocated_bed, preferred_hostel=gh2, preferred_room_type='SINGLE', reason="GH Single swap", status=ExchangeRequest.RequestStatus.ACTIVE)
        ExchangeRequest.objects.create(requester=gs2, current_bed=gs2.allocated_bed, preferred_hostel=gh1, preferred_room_type='SINGLE', reason="GH Single swap", status=ExchangeRequest.RequestStatus.ACTIVE)

        # (B) 2-Seater (Double) 3-Party Cycle:
        gd1 = create_resident('girl_double_1', 'girl_double_1@gmail.com', 'Rhea', 'Nair', '21BCE2010', User.Gender.FEMALE, gh1, '102', 0)
        gd2 = create_resident('girl_double_2', 'girl_double_2@gmail.com', 'Sneha', 'Roy', '21BCE2011', User.Gender.FEMALE, gh2, '102', 0)
        gd3 = create_resident('girl_double_3', 'girl_double_3@gmail.com', 'Priya', 'Menon', '21BCE2012', User.Gender.FEMALE, gh3, '102', 0)
        ExchangeRequest.objects.create(requester=gd1, current_bed=gd1.allocated_bed, preferred_hostel=gh2, preferred_room_type='DOUBLE', reason="GH Double cycle 1", status=ExchangeRequest.RequestStatus.ACTIVE)
        ExchangeRequest.objects.create(requester=gd2, current_bed=gd2.allocated_bed, preferred_hostel=gh3, preferred_room_type='DOUBLE', reason="GH Double cycle 2", status=ExchangeRequest.RequestStatus.ACTIVE)
        ExchangeRequest.objects.create(requester=gd3, current_bed=gd3.allocated_bed, preferred_hostel=gh1, preferred_room_type='DOUBLE', reason="GH Double cycle 3", status=ExchangeRequest.RequestStatus.ACTIVE)

        # (C) 4-Seater Quad Direct Pair:
        gq1 = create_resident('girl_quad_1', 'girl_quad_1@gmail.com', 'Isha', 'Deshmukh', '21BCE2020', User.Gender.FEMALE, gh1, '104', 0)
        gq2 = create_resident('girl_quad_2', 'girl_quad_2@gmail.com', 'Tanvi', 'Kulkarni', '21BCE2021', User.Gender.FEMALE, gh2, '104', 0)
        ExchangeRequest.objects.create(requester=gq1, current_bed=gq1.allocated_bed, preferred_hostel=gh2, preferred_room_type='FOUR_SHARING', reason="GH Quad swap", status=ExchangeRequest.RequestStatus.ACTIVE)
        ExchangeRequest.objects.create(requester=gq2, current_bed=gq2.allocated_bed, preferred_hostel=gh1, preferred_room_type='FOUR_SHARING', reason="GH Quad swap", status=ExchangeRequest.RequestStatus.ACTIVE)

        # ---------------------------------------------------------------------
        # 5. Seed Pre-Approved Proposal for Instant Warden Testing
        # ---------------------------------------------------------------------
        w_stu_a = create_resident('warden_demo_a', 'warden_demo_a@gmail.com', 'Nitin', 'Verma', '21BCE1090', User.Gender.MALE, bh1, '201', 0)
        w_stu_b = create_resident('warden_demo_b', 'warden_demo_b@gmail.com', 'Suresh', 'Raina', '21BCE1091', User.Gender.MALE, bh2, '201', 0)

        r_wa = ExchangeRequest.objects.create(
            requester=w_stu_a,
            current_bed=w_stu_a.allocated_bed,
            preferred_hostel=bh2,
            preferred_room_type='SINGLE',
            status=ExchangeRequest.RequestStatus.PROPOSED
        )
        r_wb = ExchangeRequest.objects.create(
            requester=w_stu_b,
            current_bed=w_stu_b.allocated_bed,
            preferred_hostel=bh1,
            preferred_room_type='SINGLE',
            status=ExchangeRequest.RequestStatus.PROPOSED
        )

        demo_prop = ExchangeProposal.objects.create(
            proposal_code="PROP-WARDEN-DEMO",
            proposal_type=ExchangeProposal.ProposalType.DIRECT,
            status=ExchangeProposal.ProposalStatus.READY_FOR_APPROVAL,
            compatibility_score=98.5,
            expires_at=timezone.now() + timedelta(hours=48)
        )
        ProposalParticipant.objects.create(
            proposal=demo_prop,
            student=w_stu_a,
            request=r_wa,
            current_bed=w_stu_a.allocated_bed,
            target_bed=w_stu_b.allocated_bed,
            response=ProposalParticipant.ParticipantResponse.ACCEPTED,
            responded_at=timezone.now(),
            order_index=0
        )
        ProposalParticipant.objects.create(
            proposal=demo_prop,
            student=w_stu_b,
            request=r_wb,
            current_bed=w_stu_b.allocated_bed,
            target_bed=w_stu_a.allocated_bed,
            response=ProposalParticipant.ParticipantResponse.ACCEPTED,
            responded_at=timezone.now(),
            order_index=1
        )
        self.stdout.write("[OK] Seeded READY_FOR_APPROVAL proposal PROP-WARDEN-DEMO for Warden dashboard testing.")

        # ---------------------------------------------------------------------
        # 6. Seed 30 Additional Realistic Campus Residents for Authenticity
        # ---------------------------------------------------------------------
        names = [
            ("Dev", "Sharma", "M"), ("Pranav", "Nair", "M"), ("Yash", "Chopra", "M"),
            ("Kartik", "Mishra", "M"), ("Saurabh", "Bose", "M"), ("Akash", "Trivedi", "M"),
            ("Abhishek", "Rathore", "M"), ("Rishi", "Pandey", "M"), ("Mayank", "Singhal", "M"),
            ("Tarun", "Sen", "M"), ("Divya", "Pillai", "F"), ("Shweta", "Bhardwaj", "F"),
            ("Meenakshi", "Sundaram", "F"), ("Kritika", "Sethi", "F"), ("Simran", "Kaur", "F"),
            ("Deepika", "Rao", "F"), ("Sangeeta", "Gowda", "F"), ("Preeti", "Chatterjee", "F"),
            ("Radhika", "Bansal", "F"), ("Nidhi", "Agarwal", "F")
        ]

        active_hostels = list(Hostel.objects.filter(is_active=True))
        uid_counter = 3000
        for i, (fn, ln, g) in enumerate(names):
            uname = f"resident_{fn.lower()}_{i+1}"
            email = f"{uname}@gmail.com"
            gender = User.Gender.MALE if g == "M" else User.Gender.FEMALE
            target_hostel = [h for h in active_hostels if (h.gender_type == 'MALE' if g == 'M' else h.gender_type == 'FEMALE')][i % 4]
            # Pick room 102, 103, or 104
            room_choice = ['102', '103', '104', '105', '106'][i % 5]
            uid_counter += 1
            create_resident(uname, email, fn, ln, f"21BCE{uid_counter}", gender, target_hostel, room_choice, 1)

        total_students = User.objects.filter(role=User.Role.STUDENT).count()
        total_requests = ExchangeRequest.objects.filter(status=ExchangeRequest.RequestStatus.ACTIVE).count()
        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {total_students} total students across hostels!"))
        self.stdout.write(self.style.SUCCESS(f"Active Exchange Requests: {total_requests} (Covering 1-Seater, 2-Seater, 3-Seater, 4-Seater, 7-Seater & 8-Seater)"))
        self.stdout.write(self.style.SUCCESS("All student passwords are: student@123"))
