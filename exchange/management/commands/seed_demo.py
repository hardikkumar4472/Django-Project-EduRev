from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from hostel.models import Hostel, Block, Room, Bed
from exchange.models import (
    PolicyRule,
    ExchangeRequest,
    ExchangeProposal,
    ProposalParticipant,
    Approval,
    TransferRecord,
    AuditEntry
)

User = get_user_model()

class Command(BaseCommand):
    help = "Seeds comprehensive realistic university demo data for P04 Master Scenario"

    def handle(self, *args, **options):
        self.stdout.write("Seeding campus hostels, resident students, policy rules, and demo cycles...")

        # 1. Clean existing records
        AuditEntry.objects.all().delete()
        TransferRecord.objects.all().delete()
        Approval.objects.all().delete()
        ProposalParticipant.objects.all().delete()
        ExchangeProposal.objects.all().delete()
        ExchangeRequest.objects.all().delete()
        Bed.objects.all().delete()
        Room.objects.all().delete()
        Block.objects.all().delete()
        Hostel.objects.all().delete()
        User.objects.all().delete()
        PolicyRule.objects.all().delete()

        # 2. Seed System Policies
        default_policies = [
            (PolicyRule.RuleType.COOLING_OFF_DAYS, 30, True, "Days student must wait after a completed transfer before applying again"),
            (PolicyRule.RuleType.MAX_CHAIN_LENGTH, 5, True, "Maximum multi-party cycle length (2 to 5) evaluated by graph matching"),
            (PolicyRule.RuleType.PROPOSAL_VALIDITY_HOURS, 48, True, "Hours allowed for all participants to accept a proposal before automatic expiration"),
            (PolicyRule.RuleType.FEE_CLEARANCE_REQUIRED, 0, True, "Require zero hostel fee balance before allowing request submission"),
            (PolicyRule.RuleType.DISCIPLINARY_CHECK, 0, True, "Block students with active disciplinary holds from participating in room transfers"),
            (PolicyRule.RuleType.GENDER_STRICT_SEPARATION, 0, True, "Enforce strict hostel block gender residency regulations"),
        ]
        for r_type, d_int, d_bool, desc in default_policies:
            PolicyRule.objects.create(rule_type=r_type, int_value=d_int, bool_value=d_bool, description=desc)

        # 3. Create Administrative & Staff Personas
        warden_sharma = User.objects.create_user(
            username='warden_sharma',
            email='warden.sharma@university.edu',
            password='campus123',
            first_name='Dr. K.',
            last_name='Sharma',
            university_id='FAC-WAR-01',
            role=User.Role.WARDEN,
            gender=User.Gender.MALE
        )

        chief_warden = User.objects.create_user(
            username='chief_warden_verma',
            email='chief.warden@university.edu',
            password='campus123',
            first_name='Prof. R.',
            last_name='Verma',
            university_id='FAC-CHIEF-01',
            role=User.Role.CHIEF_WARDEN,
            gender=User.Gender.MALE
        )

        admin_patel = User.objects.create_superuser(
            username='admin_patel',
            email='admin@university.edu',
            password='campus123',
            first_name='S.',
            last_name='Patel',
            university_id='ADMIN-01',
            role=User.Role.ADMIN,
            gender=User.Gender.MALE
        )

        dean_rao = User.objects.create_user(
            username='dean_rao',
            email='dean.dsw@university.edu',
            password='campus123',
            first_name='Prof. M.',
            last_name='Rao',
            university_id='DSW-DEAN-01',
            role=User.Role.DSW,
            gender=User.Gender.MALE
        )

        # 4. Create 4 Campus Hostels
        tagore = Hostel.objects.create(name='Rabindranath Tagore Hall', code='TAGORE', gender_type=Hostel.GenderType.MALE, warden=warden_sharma)
        sarojini = Hostel.objects.create(name='Sarojini Naidu Residence', code='SAROJINI', gender_type=Hostel.GenderType.FEMALE, warden=warden_sharma)
        aryabhatta = Hostel.objects.create(name='Aryabhatta Tech Residence', code='ARYABHATTA', gender_type=Hostel.GenderType.MALE, warden=chief_warden)
        gargi = Hostel.objects.create(name='Gargi Postgraduate Hall', code='GARGI', gender_type=Hostel.GenderType.FEMALE, warden=chief_warden)

        hostels = [tagore, sarojini, aryabhatta, gargi]

        # 5. Create Blocks, Rooms, Beds
        blocks_data = ['A', 'B', 'C', 'D']
        room_dict = {} # key: (hostel.code, block.code, room_number) -> Room

        for h in hostels:
            for b_code in blocks_data:
                block = Block.objects.create(hostel=h, name=f"Block {b_code}", code=b_code)
                for floor in [1, 2, 3, 4]:
                    for r_num in [1, 2, 3, 4, 12]:
                        r_str = f"{floor}{r_num:02d}"
                        room = Room.objects.create(
                            block=block,
                            room_number=r_str,
                            floor=floor,
                            room_type=Room.RoomType.DOUBLE if r_num % 2 == 0 else Room.RoomType.SINGLE,
                            capacity=2 if r_num % 2 == 0 else 1,
                            has_ac=(floor >= 3),
                            has_attached_bath=(r_num == 1)
                        )
                        room_dict[(h.code, b_code, r_str)] = room
                        # Create beds
                        for bed_idx in range(1, room.capacity + 1):
                            Bed.objects.create(
                                room=room,
                                bed_number=f"Bed {bed_idx}",
                                occupancy_status=Bed.OccupancyStatus.VACANT
                            )

        # 6. Create Signature 4 Students for the Primary Demonstration Scenario
        # Student A: Room A-101 (Tagore) -> Desires B-203
        # Student B: Room B-203 (Tagore) -> Desires C-304
        # Student C: Room C-304 (Tagore) -> Desires D-412
        # Student D: Room D-412 (Tagore) -> Desires A-101
        student_configs = [
            ('student_a', 'Aarav', 'Sharma', '21BCE1001', 'TAGORE', 'A', '101', 'Bed 1', 'TAGORE', 'B', '203'),
            ('student_b', 'Bhavya', 'Patel', '21BCE1002', 'TAGORE', 'B', '203', 'Bed 1', 'TAGORE', 'C', '304'),
            ('student_c', 'Chirag', 'Verma', '21BCE1003', 'TAGORE', 'C', '304', 'Bed 1', 'TAGORE', 'D', '412'),
            ('student_d', 'Divya', 'Nair', '21BCE1004', 'TAGORE', 'D', '412', 'Bed 1', 'TAGORE', 'A', '101'),
        ]

        demo_students = []
        for uname, fname, lname, uid, h_code, b_code, r_num, b_num, t_h_code, t_b_code, t_r_num in student_configs:
            student = User.objects.create_user(
                username=uname,
                email=f"{uname}@university.edu",
                password='campus123',
                first_name=fname,
                last_name=lname,
                university_id=uid,
                role=User.Role.STUDENT,
                gender=User.Gender.MALE
            )
            
            # Allocate current bed
            curr_room = room_dict[(h_code, b_code, r_num)]
            curr_bed = curr_room.beds.first()
            curr_bed.current_occupant = student
            curr_bed.occupancy_status = Bed.OccupancyStatus.OCCUPIED
            curr_bed.save()

            # Create active exchange request
            target_room = room_dict[(t_h_code, t_b_code, t_r_num)]
            req = ExchangeRequest.objects.create(
                requester=student,
                current_bed=curr_bed,
                preferred_hostel=target_room.block.hostel,
                specific_target_room=target_room,
                status=ExchangeRequest.RequestStatus.ACTIVE,
                reason=f"Desired room rotation to {target_room.full_name}"
            )
            demo_students.append((student, curr_bed, target_room, req))

        # 7. Create 46 Additional Realistic Student Residents to make 50+ total students
        first_names = ["Aditya", "Rohan", "Siddharth", "Ananya", "Pooja", "Vikram", "Sneha", "Kunal", "Meera", "Varun",
                       "Isha", "Naveen", "Tanvi", "Arjun", "Rhea", "Rahul", "Priya", "Manish", "Shreya", "Kavita",
                       "Gaurav", "Simran", "Amit", "Neha", "Deepak"]
        last_names = ["Gupta", "Singh", "Kumar", "Iyer", "Reddy", "Banerjee", "Chopra", "Joshi", "Mishra", "Saxena"]

        vacant_beds = list(Bed.objects.filter(occupancy_status=Bed.OccupancyStatus.VACANT)[:60])
        student_count = 0
        for i, bed in enumerate(vacant_beds[:46]):
            fn = first_names[i % len(first_names)]
            ln = last_names[i % len(last_names)]
            uname = f"resident_{i+5:02d}"
            s = User.objects.create_user(
                username=uname,
                email=f"{uname}@university.edu",
                password='campus123',
                first_name=fn,
                last_name=ln,
                university_id=f"22BCS{i+105:04d}",
                role=User.Role.STUDENT,
                gender=User.Gender.FEMALE if bed.room.block.hostel.gender_type == 'FEMALE' else User.Gender.MALE
            )
            bed.current_occupant = s
            bed.occupancy_status = Bed.OccupancyStatus.OCCUPIED
            bed.save()
            student_count += 1

            # Give a few of them active requests to create other cycles
            if i % 5 == 0:
                ExchangeRequest.objects.create(
                    requester=s,
                    current_bed=bed,
                    preferred_hostel=bed.room.block.hostel,
                    preferred_floor=2,
                    status=ExchangeRequest.RequestStatus.ACTIVE,
                    reason="Requesting 2nd floor room"
                )

        # 8. Create One Completed Transfer Record for Historical & Audit Demo
        past_student = demo_students[0][0]
        past_bed_prev = room_dict[('TAGORE', 'A', '102')].beds.first()
        past_bed_curr = demo_students[0][1]
        t_code = "TRF-2026-INIT001"
        TransferRecord.objects.create(
            transfer_code=t_code,
            proposal=ExchangeProposal.objects.create(
                proposal_code="PROP-2026-HIST01",
                proposal_type=ExchangeProposal.ProposalType.DIRECT,
                status=ExchangeProposal.ProposalStatus.COMPLETED,
                expires_at=timezone.now() - timedelta(days=5),
                completed_at=timezone.now() - timedelta(days=5)
            ),
            student=past_student,
            previous_bed=past_bed_prev,
            new_bed=past_bed_curr,
            approved_by=warden_sharma,
            completed_at=timezone.now() - timedelta(days=5)
        )

        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded database:\n"
            f"  * {Hostel.objects.count()} Hostels, {Block.objects.count()} Blocks, {Room.objects.count()} Rooms, {Bed.objects.count()} Beds\n"
            f"  * {User.objects.count()} Users (50+ Students, 2 Wardens, 1 Admin, 1 DSW)\n"
            f"  * Signature 4-Party Cycle (A -> B -> C -> D -> A) ready for graph discovery and live demonstration!\n"
            f"  * Default demo password for all accounts: 'campus123'"
        ))
