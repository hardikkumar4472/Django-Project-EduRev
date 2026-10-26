import uuid
import random
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
    StudentLifestyle
)

User = get_user_model()

class Command(BaseCommand):
    help = "Seeds comprehensive, high-volume production-like realistic data: users, requests, cycles, proposals, chats, transfer letters, and audit logs."

    def handle(self, *args, **options):
        self.stdout.write("=========================================================")
        self.stdout.write("[START] Seeding High-Volume Production-Grade Simulation Data...")
        self.stdout.write("=========================================================")

        # Clean existing runtime data (preserving system staff accounts)
        TransferRecord.objects.all().delete()
        ProposalParticipant.objects.all().delete()
        ProposalMessage.objects.all().delete()
        Approval.objects.all().delete()
        ExchangeProposal.objects.all().delete()
        ExchangeRequest.objects.all().delete()
        AuditEntry.objects.all().delete()

        core_usernames = {
            'student', 'admin', 'dsw', 'chief_warden', 'warden',
            'wardenbh1', 'wardenbh2', 'wardenbh3', 'wardenbh4', 'wardenbh5',
            'wardenbh6', 'wardenbh7', 'wardenbh8', 'wardenbh9', 'wardenbh10',
            'wardengh1', 'wardengh2', 'wardengh3', 'wardengh4', 'wardengh5',
            'wardengh6', 'wardengh7', 'wardengh8', 'wardengh9', 'wardengh10',
        }

        # Clear existing transient student accounts
        transient_students = User.objects.filter(role=User.Role.STUDENT).exclude(username__in=core_usernames)
        for s in transient_students:
            if hasattr(s, 'allocated_bed') and s.allocated_bed:
                bed = s.allocated_bed
                bed.current_occupant = None
                bed.occupancy_status = Bed.OccupancyStatus.VACANT
                bed.save()
            s.delete()

        # Retrieve administrative actors
        admin_user = User.objects.filter(username='admin').first()
        chief_warden = User.objects.filter(role=User.Role.CHIEF_WARDEN).first()
        warden_bh1 = User.objects.filter(username='wardenbh1').first()
        warden_bh2 = User.objects.filter(username='wardenbh2').first()
        dsw_user = User.objects.filter(role=User.Role.DSW).first()

        hostels = list(Hostel.objects.filter(is_active=True))
        bh1 = Hostel.objects.filter(code='BH-1').first()
        bh2 = Hostel.objects.filter(code='BH-2').first()
        bh3 = Hostel.objects.filter(code='BH-3').first()
        bh4 = Hostel.objects.filter(code='BH-4').first()
        gh1 = Hostel.objects.filter(code='GH-1').first()
        gh2 = Hostel.objects.filter(code='GH-2').first()
        gh3 = Hostel.objects.filter(code='GH-3').first()

        # -------------------------------------------------------------
        # 1. Main Student Setup ('student' -> Aarav Sharma)
        # -------------------------------------------------------------
        main_student = User.objects.filter(username='student').first()
        if not main_student:
            main_student = User.objects.create_user(
                username='student',
                email='aarav.sharma@edurev.edu',
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

        # Allocate bed in BH-1 Room 101 Bed 1
        room_bh1_101 = Room.objects.filter(block__hostel=bh1, room_number='101').first()
        if room_bh1_101:
            bed_101 = room_bh1_101.beds.first()
            if bed_101:
                bed_101.current_occupant = main_student
                bed_101.occupancy_status = Bed.OccupancyStatus.OCCUPIED
                bed_101.save()

        # Lifestyle profile for Aarav
        StudentLifestyle.objects.update_or_create(
            student=main_student,
            defaults={
                'sleep_schedule': StudentLifestyle.SleepSchedule.EARLY_BIRD,
                'study_habit': StudentLifestyle.StudyHabit.PIN_DROP,
                'ac_preference': StudentLifestyle.ACPreference.MODERATE,
                'cleanliness': StudentLifestyle.Cleanliness.VERY_STRICT,
                'hobbies': 'Competitive Coding, Chess, Morning Jogging'
            }
        )

        # Active request for Aarav: wants BH-2
        req_aarav = ExchangeRequest.objects.create(
            requester=main_student,
            current_bed=main_student.allocated_bed,
            preferred_hostel=bh2,
            preferred_room_type='SINGLE',
            reason="Looking for accommodation in BH-2 close to academic computer science labs.",
            status=ExchangeRequest.RequestStatus.ACTIVE
        )

        # -------------------------------------------------------------
        # 2. Student Creation Helper
        # -------------------------------------------------------------
        def create_student(username, email, fn, ln, uid, gender, hostel, room_num, bed_idx=0, sleep=None, study=None, clean=None):
            user = User.objects.create_user(
                username=username,
                email=email,
                first_name=fn,
                last_name=ln,
                university_id=uid,
                role=User.Role.STUDENT,
                gender=gender
            )
            user.set_password('student@123')
            user.has_fee_clearance = True
            user.has_disciplinary_hold = False
            user.save()

            # Bed allocation
            room = Room.objects.filter(block__hostel=hostel, room_number=room_num).first()
            if room:
                beds = list(room.beds.all())
                if beds and bed_idx < len(beds):
                    bed = beds[bed_idx]
                    bed.current_occupant = user
                    bed.occupancy_status = Bed.OccupancyStatus.OCCUPIED
                    bed.save()

            # Lifestyle Profile
            StudentLifestyle.objects.create(
                student=user,
                sleep_schedule=sleep or random.choice(StudentLifestyle.SleepSchedule.values),
                study_habit=study or random.choice(StudentLifestyle.StudyHabit.values),
                ac_preference=random.choice(StudentLifestyle.ACPreference.values),
                cleanliness=clean or random.choice(StudentLifestyle.Cleanliness.values),
                hobbies=random.choice([
                    "Gym, Football, AI Research",
                    "Guitar, Night Gaming, Web Dev",
                    "Badminton, Reading, Data Structures",
                    "Photography, Swimming, Blogging",
                    "UI/UX Design, Anime, Podcasting"
                ])
            )
            return user

        # -------------------------------------------------------------
        # 3. Direct Match with Aarav: student_bh2 (in BH-2 -> wants BH-1)
        # -------------------------------------------------------------
        s_bh2 = create_student(
            'student_bh2', 'rohan.verma@edurev.edu', 'Rohan', 'Verma', '21BCE1002',
            User.Gender.MALE, bh2, '101', 0,
            sleep=StudentLifestyle.SleepSchedule.EARLY_BIRD,
            study=StudentLifestyle.StudyHabit.PIN_DROP,
            clean=StudentLifestyle.Cleanliness.VERY_STRICT
        )
        ExchangeRequest.objects.create(
            requester=s_bh2,
            current_bed=s_bh2.allocated_bed,
            preferred_hostel=bh1,
            preferred_room_type='SINGLE',
            reason="Wanting to move to BH-1 to join the University Robotics team.",
            status=ExchangeRequest.RequestStatus.ACTIVE
        )

        # 3-Party Circular loop: student_bh3 (BH-3 -> wants BH-1) & s_bh2 (BH-2 -> wants BH-3)
        s_bh3 = create_student(
            'student_bh3', 'siddharth.m@edurev.edu', 'Siddharth', 'Mehta', '21BCE1003',
            User.Gender.MALE, bh3, '101', 0
        )
        ExchangeRequest.objects.create(
            requester=s_bh3,
            current_bed=s_bh3.allocated_bed,
            preferred_hostel=bh1,
            preferred_room_type='SINGLE',
            reason="Core course curriculum cohort relocated to BH-1.",
            status=ExchangeRequest.RequestStatus.ACTIVE
        )

        # -------------------------------------------------------------
        # 4. Multi-Capacity Cycles (2-Seater, 3-Seater, 4-Seater, Dorms)
        # -------------------------------------------------------------
        # Double Room (2-Seater) Direct Match
        bd1 = create_student('kunal_k', 'kunal@edurev.edu', 'Kunal', 'Kapoor', '21BCE1011', User.Gender.MALE, bh1, '102', 0)
        bd2 = create_student('vikram_p', 'vikram@edurev.edu', 'Vikram', 'Patel', '21BCE1012', User.Gender.MALE, bh2, '102', 0)
        ExchangeRequest.objects.create(requester=bd1, current_bed=bd1.allocated_bed, preferred_hostel=bh2, preferred_room_type='DOUBLE', reason="Closer to sport complex in BH-2", status=ExchangeRequest.RequestStatus.ACTIVE)
        ExchangeRequest.objects.create(requester=bd2, current_bed=bd2.allocated_bed, preferred_hostel=bh1, preferred_room_type='DOUBLE', reason="Study group in BH-1", status=ExchangeRequest.RequestStatus.ACTIVE)

        # Triple Room (3-Seater) 3-Party Cycle
        bt1 = create_student('aditya_g', 'aditya@edurev.edu', 'Aditya', 'Gupta', '21BCE1021', User.Gender.MALE, bh1, '103', 0)
        bt2 = create_student('naveen_c', 'naveen@edurev.edu', 'Naveen', 'Chopra', '21BCE1022', User.Gender.MALE, bh2, '103', 0)
        bt3 = create_student('varun_s', 'varun@edurev.edu', 'Varun', 'Saxena', '21BCE1023', User.Gender.MALE, bh3, '103', 0)
        ExchangeRequest.objects.create(requester=bt1, current_bed=bt1.allocated_bed, preferred_hostel=bh2, preferred_room_type='TRIPLE', reason="Triple cycle leg 1", status=ExchangeRequest.RequestStatus.ACTIVE)
        ExchangeRequest.objects.create(requester=bt2, current_bed=bt2.allocated_bed, preferred_hostel=bh3, preferred_room_type='TRIPLE', reason="Triple cycle leg 2", status=ExchangeRequest.RequestStatus.ACTIVE)
        ExchangeRequest.objects.create(requester=bt3, current_bed=bt3.allocated_bed, preferred_hostel=bh1, preferred_room_type='TRIPLE', reason="Triple cycle leg 3", status=ExchangeRequest.RequestStatus.ACTIVE)

        # 4-Seater Quad 4-Party Cycle
        bq1 = create_student('arjun_r', 'arjun@edurev.edu', 'Arjun', 'Reddy', '21BCE1031', User.Gender.MALE, bh1, '104', 0)
        bq2 = create_student('manish_i', 'manish@edurev.edu', 'Manish', 'Iyer', '21BCE1032', User.Gender.MALE, bh2, '104', 0)
        bq3 = create_student('rahul_s', 'rahul@edurev.edu', 'Rahul', 'Singh', '21BCE1033', User.Gender.MALE, bh3, '104', 0)
        bq4 = create_student('deepak_m', 'deepak@edurev.edu', 'Deepak', 'Mishra', '21BCE1034', User.Gender.MALE, bh4, '104', 0)
        ExchangeRequest.objects.create(requester=bq1, current_bed=bq1.allocated_bed, preferred_hostel=bh2, preferred_room_type='FOUR_SHARING', reason="Quad cycle leg 1", status=ExchangeRequest.RequestStatus.ACTIVE)
        ExchangeRequest.objects.create(requester=bq2, current_bed=bq2.allocated_bed, preferred_hostel=bh3, preferred_room_type='FOUR_SHARING', reason="Quad cycle leg 2", status=ExchangeRequest.RequestStatus.ACTIVE)
        ExchangeRequest.objects.create(requester=bq3, current_bed=bq3.allocated_bed, preferred_hostel=bh4, preferred_room_type='FOUR_SHARING', reason="Quad cycle leg 3", status=ExchangeRequest.RequestStatus.ACTIVE)
        ExchangeRequest.objects.create(requester=bq4, current_bed=bq4.allocated_bed, preferred_hostel=bh1, preferred_room_type='FOUR_SHARING', reason="Quad cycle leg 4", status=ExchangeRequest.RequestStatus.ACTIVE)

        # -------------------------------------------------------------
        # 5. Girls Hostel Cohort & Rotations
        # -------------------------------------------------------------
        gs1 = create_student('ananya_s', 'ananya@edurev.edu', 'Ananya', 'Sharma', '21BCE2001', User.Gender.FEMALE, gh1, '101', 0)
        gs2 = create_student('pooja_s', 'pooja@edurev.edu', 'Pooja', 'Singh', '21BCE2002', User.Gender.FEMALE, gh2, '101', 0)
        ExchangeRequest.objects.create(requester=gs1, current_bed=gs1.allocated_bed, preferred_hostel=gh2, preferred_room_type='SINGLE', reason="Girls Single swap", status=ExchangeRequest.RequestStatus.ACTIVE)
        ExchangeRequest.objects.create(requester=gs2, current_bed=gs2.allocated_bed, preferred_hostel=gh1, preferred_room_type='SINGLE', reason="Girls Single swap", status=ExchangeRequest.RequestStatus.ACTIVE)

        gd1 = create_student('rhea_n', 'rhea@edurev.edu', 'Rhea', 'Nair', '21BCE2011', User.Gender.FEMALE, gh1, '102', 0)
        gd2 = create_student('sneha_r', 'sneha@edurev.edu', 'Sneha', 'Roy', '21BCE2012', User.Gender.FEMALE, gh2, '102', 0)
        gd3 = create_student('priya_m', 'priya@edurev.edu', 'Priya', 'Menon', '21BCE2013', User.Gender.FEMALE, gh3, '102', 0)
        ExchangeRequest.objects.create(requester=gd1, current_bed=gd1.allocated_bed, preferred_hostel=gh2, preferred_room_type='DOUBLE', reason="Girls Double cycle 1", status=ExchangeRequest.RequestStatus.ACTIVE)
        ExchangeRequest.objects.create(requester=gd2, current_bed=gd2.allocated_bed, preferred_hostel=gh3, preferred_room_type='DOUBLE', reason="Girls Double cycle 2", status=ExchangeRequest.RequestStatus.ACTIVE)
        ExchangeRequest.objects.create(requester=gd3, current_bed=gd3.allocated_bed, preferred_hostel=gh1, preferred_room_type='DOUBLE', reason="Girls Double cycle 3", status=ExchangeRequest.RequestStatus.ACTIVE)

        # -------------------------------------------------------------
        # 6. Active Live Proposal with Messages (PROP-2026-DEMO)
        # -------------------------------------------------------------
        p_stu1 = create_student('ayush_t', 'ayush@edurev.edu', 'Ayush', 'Tiwari', '21BCE1055', User.Gender.MALE, bh1, '201', 0)
        p_stu2 = create_student('chirag_j', 'chirag@edurev.edu', 'Chirag', 'Jain', '21BCE1056', User.Gender.MALE, bh2, '201', 0)

        r_p1 = ExchangeRequest.objects.create(requester=p_stu1, current_bed=p_stu1.allocated_bed, preferred_hostel=bh2, preferred_room_type='SINGLE', status=ExchangeRequest.RequestStatus.PROPOSED)
        r_p2 = ExchangeRequest.objects.create(requester=p_stu2, current_bed=p_stu2.allocated_bed, preferred_hostel=bh1, preferred_room_type='SINGLE', status=ExchangeRequest.RequestStatus.PROPOSED)

        active_prop = ExchangeProposal.objects.create(
            proposal_code="PROP-2026-ACTIVE-99",
            proposal_type=ExchangeProposal.ProposalType.DIRECT,
            status=ExchangeProposal.ProposalStatus.PARTIALLY_ACCEPTED,
            compatibility_score=96.4,
            expires_at=timezone.now() + timedelta(hours=36)
        )
        ProposalParticipant.objects.create(
            proposal=active_prop,
            student=p_stu1,
            request=r_p1,
            current_bed=p_stu1.allocated_bed,
            target_bed=p_stu2.allocated_bed,
            response=ProposalParticipant.ParticipantResponse.ACCEPTED,
            responded_at=timezone.now() - timedelta(hours=2),
            order_index=0
        )
        ProposalParticipant.objects.create(
            proposal=active_prop,
            student=p_stu2,
            request=r_p2,
            current_bed=p_stu2.allocated_bed,
            target_bed=p_stu1.allocated_bed,
            response=ProposalParticipant.ParticipantResponse.PENDING,
            order_index=1
        )

        # Seed in-proposal discussion messages
        ProposalMessage.objects.create(
            proposal=active_prop,
            sender=p_stu1,
            message="Hi Chirag! I'm planning to move my luggage on Saturday morning around 10 AM. Does that work for you?"
        )
        ProposalMessage.objects.create(
            proposal=active_prop,
            sender=p_stu2,
            message="Hey Ayush! Perfect, I've already packed most of my desk items. We can both go to the Caretaker desk together on Saturday!"
        )

        # -------------------------------------------------------------
        # 7. Ready for Warden Approval (Cross-Hostel BH-1 & BH-2)
        # -------------------------------------------------------------
        w_stu_a = create_student('nitin_v', 'nitin@edurev.edu', 'Nitin', 'Verma', '21BCE1070', User.Gender.MALE, bh1, '202', 0)
        w_stu_b = create_student('suresh_r', 'suresh@edurev.edu', 'Suresh', 'Raina', '21BCE1071', User.Gender.MALE, bh2, '202', 0)

        r_wa = ExchangeRequest.objects.create(requester=w_stu_a, current_bed=w_stu_a.allocated_bed, preferred_hostel=bh2, preferred_room_type='SINGLE', status=ExchangeRequest.RequestStatus.PROPOSED)
        r_wb = ExchangeRequest.objects.create(requester=w_stu_b, current_bed=w_stu_b.allocated_bed, preferred_hostel=bh1, preferred_room_type='SINGLE', status=ExchangeRequest.RequestStatus.PROPOSED)

        warden_prop = ExchangeProposal.objects.create(
            proposal_code="PROP-WARDEN-REVIEW-88",
            proposal_type=ExchangeProposal.ProposalType.DIRECT,
            status=ExchangeProposal.ProposalStatus.READY_FOR_APPROVAL,
            compatibility_score=98.0,
            expires_at=timezone.now() + timedelta(hours=48)
        )
        ProposalParticipant.objects.create(proposal=warden_prop, student=w_stu_a, request=r_wa, current_bed=w_stu_a.allocated_bed, target_bed=w_stu_b.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=timezone.now(), order_index=0)
        ProposalParticipant.objects.create(proposal=warden_prop, student=w_stu_b, request=r_wb, current_bed=w_stu_b.allocated_bed, target_bed=w_stu_a.allocated_bed, response=ProposalParticipant.ParticipantResponse.ACCEPTED, responded_at=timezone.now(), order_index=1)

        # -------------------------------------------------------------
        # 8. Completed Official Transfer Pass (For QR Caretaker Desk)
        # -------------------------------------------------------------
        comp_stu = create_student('tushar_m', 'tushar@edurev.edu', 'Tushar', 'Malhotra', '21BCE1085', User.Gender.MALE, bh1, '203', 0)
        dest_room = Room.objects.filter(block__hostel=bh2, room_number='203').first()
        dest_bed = dest_room.beds.first() if dest_room else comp_stu.allocated_bed

        comp_prop = ExchangeProposal.objects.create(
            proposal_code="PROP-EXECUTED-101",
            proposal_type=ExchangeProposal.ProposalType.DIRECT,
            status=ExchangeProposal.ProposalStatus.COMPLETED,
            compatibility_score=99.2,
            expires_at=timezone.now() - timedelta(days=1)
        )
        Approval.objects.create(
            proposal=comp_prop,
            approver=chief_warden or admin_user,
            decision=Approval.Decision.APPROVED,
            remarks="Verified academic standing and hostel zero-dues clearance."
        )
        transfer_pass = TransferRecord.objects.create(
            transfer_code="TRF-2026-618921",
            proposal=comp_prop,
            student=comp_stu,
            previous_bed=comp_stu.allocated_bed,
            new_bed=dest_bed,
            approved_by=chief_warden or admin_user,
            verification_token=uuid.UUID('a1b2c3d4-e5f6-7890-abcd-ef1234567890')
        )

        # -------------------------------------------------------------
        # 9. Additional Cohort of 35 Active Requests for Dense Analytics
        # -------------------------------------------------------------
        first_names = [
            "Dev", "Pranav", "Yash", "Kartik", "Saurabh", "Akash", "Abhishek", "Rishi",
            "Mayank", "Tarun", "Divya", "Shweta", "Meenakshi", "Kritika", "Simran",
            "Deepika", "Sangeeta", "Preeti", "Radhika", "Nidhi", "Tanmay", "Harsh",
            "Gaurav", "Amit", "Kunal", "Rajesh", "Pankaj", "Vikas", "Sunil", "Ankit",
            "Bhavna", "Kavita", "Ritu", "Payal", "Monika"
        ]
        last_names = [
            "Sharma", "Verma", "Gupta", "Malhotra", "Mehta", "Patel", "Singh", "Joshi",
            "Chopra", "Bhatia", "Saxena", "Deshmukh", "Kulkarni", "Iyer", "Nair", "Menon"
        ]

        active_rooms = list(Room.objects.filter(is_active=True))
        all_hostels = list(Hostel.objects.filter(is_active=True))
        
        counter = 3100
        for i, fn in enumerate(first_names):
            ln = random.choice(last_names)
            gender = User.Gender.MALE if i < 20 else User.Gender.FEMALE
            u_name = f"stu_{fn.lower()}_{i+1}"
            email = f"{u_name}@edurev.edu"
            counter += 1
            
            # Select gender-appropriate hostel
            h_pool = [h for h in all_hostels if (h.gender_type == 'MALE' if gender == User.Gender.MALE else h.gender_type == 'FEMALE')]
            curr_hostel = random.choice(h_pool)
            target_hostel = random.choice([h for h in h_pool if h != curr_hostel] or h_pool)
            
            # Pick a room from that hostel
            avail_rooms = [r for r in active_rooms if r.block.hostel == curr_hostel]
            room_obj = random.choice(avail_rooms) if avail_rooms else active_rooms[0]

            stu = create_student(
                u_name, email, fn, ln, f"21BCE{counter}", gender, curr_hostel, room_obj.room_number, bed_idx=0
            )

            # Create an open exchange request
            ExchangeRequest.objects.create(
                requester=stu,
                current_bed=stu.allocated_bed or bed_101,
                preferred_hostel=target_hostel,
                preferred_room_type=random.choice(Room.RoomType.values),
                preferred_floor=random.choice([1, 2, 3, 4]),
                reason=random.choice([
                    "Seeking quieter study environment for competitive exam preparation.",
                    "Closer proximity to campus central library and sports pavilion.",
                    "Requesting relocation to be in the same wing as department lab partners.",
                    "Medical recommendation for lower floor accommodation.",
                    "Preferring modern block infrastructure and Wi-Fi access point proximity."
                ]),
                status=ExchangeRequest.RequestStatus.ACTIVE
            )

        # -------------------------------------------------------------
        # 10. Comprehensive Immutable Audit Trail Entries
        # -------------------------------------------------------------
        audit_events = [
            ("SYSTEM", "SERVER_STARTUP", "Core", "0", "Production system re-initialized with ACID compliance."),
            (admin_user.username if admin_user else "admin", "POLICY_UPDATED", "PolicyRule", "COOLING_OFF_DAYS", "Cooling off verified at 30 days."),
            ("student", "REQUEST_ACTIVATED", "ExchangeRequest", str(req_aarav.id), "Request for BH-2 submitted by Aarav Sharma."),
            ("student_bh2", "REQUEST_ACTIVATED", "ExchangeRequest", "42", "Reciprocal exchange request submitted by Rohan Verma."),
            ("SYSTEM", "CYCLE_MATCH_FOUND", "MatchingEngine", "CYC-901", "Detected 2-party reciprocal cycle between BH-1 and BH-2."),
            ("ayush_t", "PROPOSAL_ACCEPTED", "ExchangeProposal", str(active_prop.id), "Participant confirmed exchange terms."),
            ("chief_warden", "TRANSFER_EXECUTED", "TransferRecord", transfer_pass.transfer_code, "Final authorization granted by Chief Warden."),
            ("warden_bh1", "CARETAKER_KEY_VERIFIED", "KeyDesk", transfer_pass.transfer_code, "Physical keys deposited and verified at key desk.")
        ]

        now = timezone.now()
        for idx, (actor_name, action, ent_type, ent_id, detail) in enumerate(audit_events):
            actor_obj = User.objects.filter(username=actor_name).first() or admin_user
            AuditEntry.objects.create(
                actor=actor_obj,
                action=action,
                entity_type=ent_type,
                entity_id=ent_id,
                metadata={"detail": detail, "ip_address": "127.0.0.1"},
                timestamp=now - timedelta(minutes=15 * (len(audit_events) - idx))
            )

        # Summary
        total_students = User.objects.filter(role=User.Role.STUDENT).count()
        total_requests = ExchangeRequest.objects.count()
        total_proposals = ExchangeProposal.objects.count()
        total_transfers = TransferRecord.objects.count()

        self.stdout.write("=========================================================")
        self.stdout.write(self.style.SUCCESS("[OK] Data Population Complete!"))
        self.stdout.write(f"- Total Registered Students: {total_students}")
        self.stdout.write(f"- Active & Proposed Requests: {total_requests}")
        self.stdout.write(f"- Active & Review Proposals: {total_proposals}")
        self.stdout.write(f"- Completed Reallocations: {total_transfers}")
        self.stdout.write(f"- Audit Trail Logs: {AuditEntry.objects.count()} entries")
        self.stdout.write("- Primary student account: 'student' / 'student@123'")
        self.stdout.write("- Ready-to-scan QR Pass token: a1b2c3d4-e5f6-7890-abcd-ef1234567890")
        self.stdout.write("=========================================================")
