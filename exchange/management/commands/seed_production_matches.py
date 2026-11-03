import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from hostel.models import Hostel, Room, Bed
from exchange.models import ExchangeRequest, StudentLifestyle

User = get_user_model()

class Command(BaseCommand):
    help = "Seeds a high-density, production-grade network of student exchange requests creating dozens of 2-party, 3-party, 4-party, and 5-party matching cycles strictly segregated by gender."

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-requests',
            action='store_true',
            help='Clear existing ACTIVE requests before seeding fresh production pool',
        )

    def handle(self, *args, **options):
        self.stdout.write("=================================================================")
        self.stdout.write("[START] Seeding Production Campus Matches & Active Requests")
        self.stdout.write("=================================================================")

        now = timezone.now()

        all_hostels = list(Hostel.objects.filter(is_active=True).order_by('code'))
        bh_hostels = {h.code: h for h in all_hostels if h.gender_type == 'MALE'}
        gh_hostels = {h.code: h for h in all_hostels if h.gender_type == 'FEMALE'}

        if not bh_hostels or not gh_hostels:
            self.stderr.write("Active hostels not found. Run 'setup_hostels' first.")
            return

        if options.get('clear_requests'):
            deleted = ExchangeRequest.objects.filter(status=ExchangeRequest.RequestStatus.ACTIVE).delete()
            self.stdout.write(f"Cleared {deleted[0]} existing active requests.")

        def allocate_student_to_room(uname, uemail, ufn, uln, uid, ugen, hostel_code, room_type, floor=None):
            hostel = bh_hostels[hostel_code] if ugen == User.Gender.MALE else gh_hostels[hostel_code]
            
            # Fetch or create student
            stu = User.objects.filter(username=uname).first() or User.objects.filter(university_id=uid).first()
            if not stu:
                stu = User.objects.create_user(
                    username=uname,
                    email=uemail,
                    first_name=ufn,
                    last_name=uln,
                    university_id=uid,
                    role=User.Role.STUDENT,
                    gender=ugen
                )
                stu.set_password('student@123')
            else:
                stu.username = uname
                stu.first_name = ufn
                stu.last_name = uln
                stu.gender = ugen
                stu.role = User.Role.STUDENT
            
            stu.has_fee_clearance = True
            stu.has_disciplinary_hold = False
            stu.save()

            # Allocate bed strictly matching room_type and gender hostel
            current_bed = getattr(stu, 'allocated_bed', None)
            needs_bed = False

            if not current_bed:
                needs_bed = True
            elif current_bed.room.block.hostel.id != hostel.id or current_bed.room.room_type != room_type:
                # Free old bed
                current_bed.current_occupant = None
                current_bed.occupancy_status = Bed.OccupancyStatus.VACANT
                current_bed.save()
                needs_bed = True

            if needs_bed:
                rooms_qs = Room.objects.filter(block__hostel=hostel, room_type=room_type, is_active=True)
                if floor:
                    floor_rooms = rooms_qs.filter(floor=floor)
                    if floor_rooms.exists():
                        rooms_qs = floor_rooms
                
                # Find room with a vacant bed
                bed = None
                for rm in rooms_qs:
                    b = rm.beds.filter(occupancy_status=Bed.OccupancyStatus.VACANT).first()
                    if b:
                        bed = b
                        break
                
                # Fallback to any vacant bed of this room type
                if not bed:
                    bed = Bed.objects.filter(
                        room__block__hostel=hostel,
                        room__room_type=room_type,
                        occupancy_status=Bed.OccupancyStatus.VACANT
                    ).first()

                if bed:
                    bed.current_occupant = stu
                    bed.occupancy_status = Bed.OccupancyStatus.OCCUPIED
                    bed.save()
                else:
                    self.stderr.write(f"Warning: No vacant bed in {hostel.code} for room type {room_type}")

            # Lifestyle
            StudentLifestyle.objects.get_or_create(
                student=stu,
                defaults={
                    'sleep_schedule': random.choice(StudentLifestyle.SleepSchedule.values),
                    'study_habit': random.choice(StudentLifestyle.StudyHabit.values),
                    'ac_preference': random.choice(StudentLifestyle.ACPreference.values),
                    'cleanliness': random.choice(StudentLifestyle.Cleanliness.values),
                    'hobbies': random.choice([
                        "Competitive Programming, Hackathons, Chess",
                        "Robotics, IoT Hardware, Gaming",
                        "Machine Learning Research, Open Source",
                        "Music Production, Digital Art, Reading",
                        "Cricket, Football, Fitness Gym",
                        "Civil Services Prep, Debating, Model UN"
                    ])
                }
            )
            return stu

        def create_match_request(stu, target_hostel_code, target_room_type, reason_text, target_floor=None):
            target_h = bh_hostels[target_hostel_code] if stu.gender == User.Gender.MALE else gh_hostels[target_hostel_code]
            
            req = ExchangeRequest.objects.filter(requester=stu).first()
            if not req:
                req = ExchangeRequest.objects.create(
                    requester=stu,
                    current_bed=stu.allocated_bed,
                    preferred_hostel=target_h,
                    preferred_room_type=target_room_type,
                    preferred_floor=target_floor,
                    status=ExchangeRequest.RequestStatus.ACTIVE,
                    reason=reason_text
                )
            else:
                req.current_bed = stu.allocated_bed
                req.preferred_hostel = target_h
                req.preferred_room_type = target_room_type
                req.preferred_floor = target_floor
                req.status = ExchangeRequest.RequestStatus.ACTIVE
                req.reason = reason_text
                req.save()
            return req

        seeded_cycles_count = 0

        # =========================================================================
        # 1. BOYS MATCHING NETWORKS (BH-1 to BH-10 ONLY)
        # =========================================================================
        self.stdout.write("1. Seeding Boys Matching Networks across BH-1 to BH-10...")

        boys_scenarios = [
            # Direct Swaps (2-Party)
            ('DIRECT_2', Room.RoomType.SINGLE, [
                ('b_swap_01', 'b01@campus.edu', 'Aarav', 'Nair', '22BCE1101', 'BH-1', 'BH-2', 'Closer to Central Computing Facility'),
                ('b_swap_02', 'b02@campus.edu', 'Rohan', 'Iyer', '22BCE1102', 'BH-2', 'BH-1', 'Wants room in Tagore Block near student mess'),
            ]),
            ('DIRECT_2', Room.RoomType.DOUBLE, [
                ('b_swap_03', 'b03@campus.edu', 'Ishaan', 'Kapoor', '22BCE1103', 'BH-2', 'BH-3', 'Moving to BH-3 to join college robotics team cluster'),
                ('b_swap_04', 'b04@campus.edu', 'Aniket', 'Deshmukh', '22BCE1104', 'BH-3', 'BH-2', 'Prefers BH-2 proximity to tennis courts'),
            ]),
            ('DIRECT_2', Room.RoomType.TRIPLE, [
                ('b_swap_05', 'b05@campus.edu', 'Aditya', 'Pandey', '22BCE1105', 'BH-3', 'BH-4', 'Wants East-facing room with morning natural light'),
                ('b_swap_06', 'b06@campus.edu', 'Devansh', 'Mishra', '22BCE1106', 'BH-4', 'BH-3', 'Relocating closer to mechanical workshop block'),
            ]),
            ('DIRECT_2', Room.RoomType.FOUR_SHARING, [
                ('b_swap_07', 'b07@campus.edu', 'Siddharth', 'Joshi', '22BCE1107', 'BH-4', 'BH-5', 'Room exchange with classmate for shared study materials'),
                ('b_swap_08', 'b08@campus.edu', 'Yash', 'Kulkarni', '22BCE1108', 'BH-5', 'BH-4', 'Prefers BH-4 hostel gym and badminton courts'),
            ]),
            ('DIRECT_2', Room.RoomType.DOUBLE, [
                ('b_swap_09', 'b09@campus.edu', 'Parth', 'Bhatia', '22BCE1109', 'BH-5', 'BH-6', 'Closer to Electrical Sciences laboratory'),
                ('b_swap_10', 'b10@campus.edu', 'Mayank', 'Saxena', '22BCE1110', 'BH-6', 'BH-5', 'Roommate graduated, seeking quieter wing in BH-5'),
            ]),
            ('DIRECT_2', Room.RoomType.SINGLE, [
                ('b_swap_11', 'b11@campus.edu', 'Aryan', 'Singhania', '22BCE1111', 'BH-7', 'BH-8', 'Relocating to quieter senior block for GATE exam prep'),
                ('b_swap_12', 'b12@campus.edu', 'Varun', 'Somani', '22BCE1112', 'BH-8', 'BH-7', 'Wants single room closer to Main Gate & Cafeteria'),
            ]),
            ('DIRECT_2', Room.RoomType.TRIPLE, [
                ('b_swap_13', 'b13@campus.edu', 'Rohit', 'Chopra', '22BCE1113', 'BH-9', 'BH-10', 'Moving to BH-10 alongside departmental research team'),
                ('b_swap_14', 'b14@campus.edu', 'Kunal', 'Bakshi', '22BCE1114', 'BH-10', 'BH-9', 'Prefers BH-9 proximity to incubation centre'),
            ]),

            # 3-Party Triangular Cycles (A -> B -> C -> A)
            ('CYCLE_3', Room.RoomType.SINGLE, [
                ('b_tri_01', 'btri01@campus.edu', 'Sameer', 'Reddy', '22BCE1201', 'BH-1', 'BH-2', 'Triangular hop 1: Moving BH-1 to BH-2'),
                ('b_tri_02', 'btri02@campus.edu', 'Tejas', 'Patil', '22BCE1202', 'BH-2', 'BH-3', 'Triangular hop 2: Moving BH-2 to BH-3'),
                ('b_tri_03', 'btri03@campus.edu', 'Chirag', 'Modi', '22BCE1203', 'BH-3', 'BH-1', 'Triangular hop 3: Moving BH-3 to BH-1'),
            ]),
            ('CYCLE_3', Room.RoomType.DOUBLE, [
                ('b_tri_04', 'btri04@campus.edu', 'Harshit', 'Goyal', '22BCE1204', 'BH-4', 'BH-5', 'Cycle leg 1: BH-4 double room to BH-5'),
                ('b_tri_05', 'btri05@campus.edu', 'Shivam', 'Tripathi', '22BCE1205', 'BH-5', 'BH-6', 'Cycle leg 2: BH-5 double room to BH-6'),
                ('b_tri_06', 'btri06@campus.edu', 'Pranav', 'Bansal', '22BCE1206', 'BH-6', 'BH-4', 'Cycle leg 3: BH-6 double room to BH-4'),
            ]),
            ('CYCLE_3', Room.RoomType.TRIPLE, [
                ('b_tri_07', 'btri07@campus.edu', 'Naveen', 'Kumar', '22BCE1207', 'BH-7', 'BH-8', 'Rotation step 1 in Triple Sharing room'),
                ('b_tri_08', 'btri08@campus.edu', 'Akash', 'Shukla', '22BCE1208', 'BH-8', 'BH-9', 'Rotation step 2 in Triple Sharing room'),
                ('b_tri_09', 'btri09@campus.edu', 'Deepak', 'Srivastava', '22BCE1209', 'BH-9', 'BH-7', 'Rotation step 3 in Triple Sharing room'),
            ]),
            ('CYCLE_3', Room.RoomType.FOUR_SHARING, [
                ('b_tri_10', 'btri10@campus.edu', 'Abhishek', 'Yadav', '22BCE1210', 'BH-8', 'BH-9', 'Quad cycle step 1'),
                ('b_tri_11', 'btri11@campus.edu', 'Gaurav', 'Tiwari', '22BCE1211', 'BH-9', 'BH-10', 'Quad cycle step 2'),
                ('b_tri_12', 'btri12@campus.edu', 'Nitin', 'Dubey', '22BCE1212', 'BH-10', 'BH-8', 'Quad cycle step 3'),
            ]),

            # 4-Party Rotations (A -> B -> C -> D -> A)
            ('CYCLE_4', Room.RoomType.DOUBLE, [
                ('b_quad_01', 'bquad01@campus.edu', 'Rahul', 'Khanna', '22BCE1301', 'BH-1', 'BH-3', '4-Party rotation leg 1: BH-1 to BH-3'),
                ('b_quad_02', 'bquad02@campus.edu', 'Vivek', 'Oberoi', '22BCE1302', 'BH-3', 'BH-5', '4-Party rotation leg 2: BH-3 to BH-5'),
                ('b_quad_03', 'bquad03@campus.edu', 'Karthik', 'Aryan', '22BCE1303', 'BH-5', 'BH-7', '4-Party rotation leg 3: BH-5 to BH-7'),
                ('b_quad_04', 'bquad04@campus.edu', 'Sanjay', 'Dutt', '22BCE1304', 'BH-7', 'BH-1', '4-Party rotation leg 4: BH-7 to BH-1'),
            ]),
            ('CYCLE_4', Room.RoomType.TRIPLE, [
                ('b_quad_05', 'bquad05@campus.edu', 'Ayushmann', 'Khurrana', '22BCE1305', 'BH-2', 'BH-4', '4-Party rotation step 1'),
                ('b_quad_06', 'bquad06@campus.edu', 'Rajkummar', 'Rao', '22BCE1306', 'BH-4', 'BH-6', '4-Party rotation step 2'),
                ('b_quad_07', 'bquad07@campus.edu', 'Vicky', 'Kaushal', '22BCE1307', 'BH-6', 'BH-8', '4-Party rotation step 3'),
                ('b_quad_08', 'bquad08@campus.edu', 'Sid', 'Malhotra', '22BCE1308', 'BH-8', 'BH-2', '4-Party rotation step 4'),
            ]),

            # 5-Party Multi-Hop Rotation (A -> B -> C -> D -> E -> A)
            ('CYCLE_5', Room.RoomType.DOUBLE, [
                ('b_pent_01', 'bpent01@campus.edu', 'Amitabh', 'Bacchan', '22BCE1401', 'BH-1', 'BH-2', '5-Party signature loop leg 1'),
                ('b_pent_02', 'bpent02@campus.edu', 'Shahrukh', 'Khan', '22BCE1402', 'BH-2', 'BH-3', '5-Party signature loop leg 2'),
                ('b_pent_03', 'bpent03@campus.edu', 'Aamir', 'Khan', '22BCE1403', 'BH-3', 'BH-4', '5-Party signature loop leg 3'),
                ('b_pent_04', 'bpent04@campus.edu', 'Salman', 'Khan', '22BCE1404', 'BH-4', 'BH-5', '5-Party signature loop leg 4'),
                ('b_pent_05', 'bpent05@campus.edu', 'Saif', 'Ali', '22BCE1405', 'BH-5', 'BH-1', '5-Party signature loop leg 5'),
            ]),
        ]

        for cycle_type, room_type, participants in boys_scenarios:
            for p_tuple in participants:
                uname, uemail, ufn, uln, uid, curr_h, tgt_h, reason = p_tuple
                stu = allocate_student_to_room(uname, uemail, ufn, uln, uid, User.Gender.MALE, curr_h, room_type)
                create_match_request(stu, tgt_h, room_type, reason)
            seeded_cycles_count += 1

        self.stdout.write(f"  [+] Seeded {len(boys_scenarios)} Boys cyclic match configurations.")


        # =========================================================================
        # 2. GIRLS MATCHING NETWORKS (GH-1 to GH-10 ONLY)
        # =========================================================================
        self.stdout.write("2. Seeding Girls Matching Networks across GH-1 to GH-10...")

        girls_scenarios = [
            # Direct Swaps (2-Party)
            ('DIRECT_2', Room.RoomType.SINGLE, [
                ('g_swap_01', 'g01@campus.edu', 'Ananya', 'Panday', '22BCE2101', 'GH-1', 'GH-2', 'Closer to Biotechnology lab complex'),
                ('g_swap_02', 'g02@campus.edu', 'Riya', 'Sen', '22BCE2102', 'GH-2', 'GH-1', 'Prefers Sarojini block near auditorium'),
            ]),
            ('DIRECT_2', Room.RoomType.DOUBLE, [
                ('g_swap_03', 'g03@campus.edu', 'Shreya', 'Ghoshal', '22BCE2103', 'GH-2', 'GH-3', 'Joining batch project partner in GH-3'),
                ('g_swap_04', 'g04@campus.edu', 'Sneha', 'Khanwalkar', '22BCE2104', 'GH-3', 'GH-2', 'Wants room in GH-2 near music studio'),
            ]),
            ('DIRECT_2', Room.RoomType.TRIPLE, [
                ('g_swap_05', 'g05@campus.edu', 'Tanvi', 'Azmi', '22BCE2105', 'GH-3', 'GH-4', 'Desires quieter study wing for UPSC prep'),
                ('g_swap_06', 'g06@campus.edu', 'Kavya', 'Maranna', '22BCE2106', 'GH-4', 'GH-3', 'Closer to indoor badminton complex'),
            ]),
            ('DIRECT_2', Room.RoomType.FOUR_SHARING, [
                ('g_swap_07', 'g07@campus.edu', 'Neha', 'Kakkar', '22BCE2107', 'GH-4', 'GH-5', 'Quad room mutual swap with department friend'),
                ('g_swap_08', 'g08@campus.edu', 'Pooja', 'Bhatt', '22BCE2108', 'GH-5', 'GH-4', 'Prefers GH-4 courtyard garden view'),
            ]),
            ('DIRECT_2', Room.RoomType.DOUBLE, [
                ('g_swap_09', 'g09@campus.edu', 'Aditi', 'Rao', '22BCE2109', 'GH-5', 'GH-6', 'Closer to Electronics design laboratory'),
                ('g_swap_10', 'g10@campus.edu', 'Divya', 'Bharti', '22BCE2110', 'GH-6', 'GH-5', 'Prefers higher floor with morning ventilation'),
            ]),
            ('DIRECT_2', Room.RoomType.SINGLE, [
                ('g_swap_11', 'g11@campus.edu', 'Meera', 'Deosthale', '22BCE2111', 'GH-7', 'GH-8', 'Relocating to GH-8 for quiet thesis work'),
                ('g_swap_12', 'g12@campus.edu', 'Sanya', 'Malhotra', '22BCE2112', 'GH-8', 'GH-7', 'Wants single room closer to Main Cafeteria'),
            ]),
            ('DIRECT_2', Room.RoomType.TRIPLE, [
                ('g_swap_13', 'g13@campus.edu', 'Simran', 'Kaur', '22BCE2113', 'GH-9', 'GH-10', 'Moving to GH-10 with research team mates'),
                ('g_swap_14', 'g14@campus.edu', 'Anoushka', 'Shankar', '22BCE2114', 'GH-10', 'GH-9', 'Prefers GH-9 ground floor access'),
            ]),

            # 3-Party Triangular Cycles (A -> B -> C -> A)
            ('CYCLE_3', Room.RoomType.SINGLE, [
                ('g_tri_01', 'gtri01@campus.edu', 'Trisha', 'Krishnan', '22BCE2201', 'GH-1', 'GH-2', 'Triangular cycle leg 1: GH-1 to GH-2'),
                ('g_tri_02', 'gtri02@campus.edu', 'Avani', 'Lekhara', '22BCE2202', 'GH-2', 'GH-3', 'Triangular cycle leg 2: GH-2 to GH-3'),
                ('g_tri_03', 'gtri03@campus.edu', 'Riddhi', 'Dogra', '22BCE2203', 'GH-3', 'GH-1', 'Triangular cycle leg 3: GH-3 to GH-1'),
            ]),
            ('CYCLE_3', Room.RoomType.DOUBLE, [
                ('g_tri_04', 'gtri04@campus.edu', 'Disha', 'Patani', '22BCE2204', 'GH-4', 'GH-5', 'Cycle leg 1: GH-4 double room to GH-5'),
                ('g_tri_05', 'gtri05@campus.edu', 'Tara', 'Sutaria', '22BCE2205', 'GH-5', 'GH-6', 'Cycle leg 2: GH-5 double room to GH-6'),
                ('g_tri_06', 'gtri06@campus.edu', 'Janhvi', 'Kapoor', '22BCE2206', 'GH-6', 'GH-4', 'Cycle leg 3: GH-6 double room to GH-4'),
            ]),
            ('CYCLE_3', Room.RoomType.TRIPLE, [
                ('g_tri_07', 'gtri07@campus.edu', 'Sara', 'Ali', '22BCE2207', 'GH-7', 'GH-8', 'Rotation step 1 in Triple Sharing room'),
                ('g_tri_08', 'gtri08@campus.edu', 'Alia', 'Bhatt', '22BCE2208', 'GH-8', 'GH-9', 'Rotation step 2 in Triple Sharing room'),
                ('g_tri_09', 'gtri09@campus.edu', 'Shraddha', 'Kapoor', '22BCE2209', 'GH-9', 'GH-7', 'Rotation step 3 in Triple Sharing room'),
            ]),
            ('CYCLE_3', Room.RoomType.FOUR_SHARING, [
                ('g_tri_10', 'gtri10@campus.edu', 'Deepika', 'Padukone', '22BCE2210', 'GH-8', 'GH-9', 'Quad cycle step 1 in GH-8'),
                ('g_tri_11', 'gtri11@campus.edu', 'Katrina', 'Kaif', '22BCE2211', 'GH-9', 'GH-10', 'Quad cycle step 2 in GH-9'),
                ('g_tri_12', 'gtri12@campus.edu', 'Priyanka', 'Chopra', '22BCE2212', 'GH-10', 'GH-8', 'Quad cycle step 3 in GH-10'),
            ]),

            # 4-Party Rotations (A -> B -> C -> D -> A)
            ('CYCLE_4', Room.RoomType.DOUBLE, [
                ('g_quad_01', 'gquad01@campus.edu', 'Kareena', 'Kapoor', '22BCE2301', 'GH-1', 'GH-3', '4-Party rotation leg 1: GH-1 to GH-3'),
                ('g_quad_02', 'gquad02@campus.edu', 'Karisma', 'Kapoor', '22BCE2302', 'GH-3', 'GH-5', '4-Party rotation leg 2: GH-3 to GH-5'),
                ('g_quad_03', 'gquad03@campus.edu', 'Sonam', 'Kapoor', '22BCE2303', 'GH-5', 'GH-7', '4-Party rotation leg 3: GH-5 to GH-7'),
                ('g_quad_04', 'gquad04@campus.edu', 'Rhea', 'Kapoor', '22BCE2304', 'GH-7', 'GH-1', '4-Party rotation leg 4: GH-7 to GH-1'),
            ]),
            ('CYCLE_4', Room.RoomType.TRIPLE, [
                ('g_quad_05', 'gquad05@campus.edu', 'Tabu', 'Hashmi', '22BCE2305', 'GH-2', 'GH-4', '4-Party rotation step 1 in GH'),
                ('g_quad_06', 'gquad06@campus.edu', 'Kajol', 'Devgn', '22BCE2306', 'GH-4', 'GH-6', '4-Party rotation step 2 in GH'),
                ('g_quad_07', 'gquad07@campus.edu', 'Rani', 'Mukerji', '22BCE2307', 'GH-6', 'GH-8', '4-Party rotation step 3 in GH'),
                ('g_quad_08', 'gquad08@campus.edu', 'Preity', 'Zinta', '22BCE2308', 'GH-8', 'GH-2', '4-Party rotation step 4 in GH'),
            ]),

            # 5-Party Multi-Hop Rotation (A -> B -> C -> D -> E -> A)
            ('CYCLE_5', Room.RoomType.DOUBLE, [
                ('g_pent_01', 'gpent01@campus.edu', 'Madhuri', 'Nene', '22BCE2401', 'GH-1', 'GH-2', '5-Party girls rotation leg 1'),
                ('g_pent_02', 'gpent02@campus.edu', 'Juhi', 'Mehta', '22BCE2402', 'GH-2', 'GH-3', '5-Party girls rotation leg 2'),
                ('g_pent_03', 'gpent03@campus.edu', 'Raveena', 'Tandon', '22BCE2403', 'GH-3', 'GH-4', '5-Party girls rotation leg 3'),
                ('g_pent_04', 'gpent04@campus.edu', 'Shilpa', 'Shetty', '22BCE2404', 'GH-4', 'GH-5', '5-Party girls rotation leg 4'),
                ('g_pent_05', 'gpent05@campus.edu', 'Sushmita', 'Sen', '22BCE2405', 'GH-5', 'GH-1', '5-Party girls rotation leg 5'),
            ]),
        ]

        for cycle_type, room_type, participants in girls_scenarios:
            for p_tuple in participants:
                uname, uemail, ufn, uln, uid, curr_h, tgt_h, reason = p_tuple
                stu = allocate_student_to_room(uname, uemail, ufn, uln, uid, User.Gender.FEMALE, curr_h, room_type)
                create_match_request(stu, tgt_h, room_type, reason)
            seeded_cycles_count += 1

        self.stdout.write(f"  [+] Seeded {len(girls_scenarios)} Girls cyclic match configurations.")


        # =========================================================================
        # 3. BACKGROUND PRODUCTION POOL (50 Diverse Requests across all 20 Hostels)
        # =========================================================================
        self.stdout.write("3. Seeding wide background pool of realistic student requests...")

        first_names_m = ["Raghav", "Dhruv", "Omkar", "Harsh", "Akshat", "Vansh", "Chinmay", "Samarth", "Naman", "Shreyas",
                         "Tejveer", "Arnav", "Dev", "Jay", "Manish", "Sanket", "Anurag", "Utkarsh", "Piyush", "Girish"]
        last_names_m = ["Bhardwaj", "Aggarwal", "Chawla", "Bhatnagar", "Sood", "Dhar", "Vora", "Merchant", "Parekh", "Chitnis"]

        first_names_f = ["Anvi", "Ishani", "Saanvi", "Nandini", "Myra", "Suhani", "Kashvi", "Navya", "Prisha", "Aarna",
                         "Ira", "Vanya", "Aditi", "Bhavna", "Charu", "Garima", "Geetika", "Harini", "Jaya", "Kalyani"]
        last_names_f = ["Garg", "Sengupta", "Banerjee", "Bose", "Mukherjee", "Dutta", "Goswami", "Chatterjee", "Roy", "Mitra"]

        reasons_pool = [
            "Requesting ground floor room for medical and mobility accommodation",
            "Seeking room closer to departmental high-performance computing cluster",
            "Desires morning sunlight and quiet wing for competitive civil service exams",
            "Mutual exchange to room near academic batch peer group",
            "Prefers room near university indoor sports complex & gymnasium",
            "Relocation closer to campus library for night study access",
            "Seeking quieter room away from courtyard construction noise",
            "Department lab shifted to North Campus science block"
        ]

        # Seed 25 background boys
        for i in range(25):
            fn = first_names_m[i % len(first_names_m)]
            ln = last_names_m[i % len(last_names_m)]
            uname = f"b_pool_{i+1:02d}"
            uid = f"22BCE9{i+100:03d}"
            curr_code = f"BH-{(i % 10) + 1}"
            tgt_code = f"BH-{((i + 3) % 10) + 1}"
            rtype = random.choice([Room.RoomType.DOUBLE, Room.RoomType.TRIPLE, Room.RoomType.FOUR_SHARING])
            floor = random.choice([1, 2, 3])
            
            stu = allocate_student_to_room(uname, f"{uname}@campus.edu", fn, ln, uid, User.Gender.MALE, curr_code, rtype, floor)
            create_match_request(stu, tgt_code, rtype, random.choice(reasons_pool), floor)

        # Seed 25 background girls
        for i in range(25):
            fn = first_names_f[i % len(first_names_f)]
            ln = last_names_f[i % len(last_names_f)]
            uname = f"g_pool_{i+1:02d}"
            uid = f"22BCE8{i+100:03d}"
            curr_code = f"GH-{(i % 10) + 1}"
            tgt_code = f"GH-{((i + 3) % 10) + 1}"
            rtype = random.choice([Room.RoomType.DOUBLE, Room.RoomType.TRIPLE, Room.RoomType.FOUR_SHARING])
            floor = random.choice([1, 2, 3])
            
            stu = allocate_student_to_room(uname, f"{uname}@campus.edu", fn, ln, uid, User.Gender.FEMALE, curr_code, rtype, floor)
            create_match_request(stu, tgt_code, rtype, random.choice(reasons_pool), floor)

        # =========================================================================
        # 4. GENDER INTEGRITY AUDIT
        # =========================================================================
        self.stdout.write("4. Verifying strict gender integrity across all seeded requests...")
        violations = 0
        for r in ExchangeRequest.objects.all():
            u = r.requester
            # Check current bed
            if r.current_bed:
                h_type = r.current_bed.room.block.hostel.gender_type
                expected = 'MALE' if u.gender == User.Gender.MALE else 'FEMALE'
                if h_type != expected:
                    self.stderr.write(f"Violation in current_bed: {u.username} ({u.gender}) in {r.current_bed}")
                    violations += 1
            # Check preferred hostel
            if r.preferred_hostel:
                ph_type = r.preferred_hostel.gender_type
                expected = 'MALE' if u.gender == User.Gender.MALE else 'FEMALE'
                if ph_type != expected:
                    self.stderr.write(f"Violation in preferred_hostel: {u.username} ({u.gender}) prefers {r.preferred_hostel.name}")
                    violations += 1

        if violations == 0:
            self.stdout.write(self.style.SUCCESS("  [PASS] ZERO Gender Policy Violations! Strict Boys->BH, Girls->GH verified."))
        else:
            self.stderr.write(f"  [FAIL] Found {violations} gender policy violations.")

        # =========================================================================
        # 5. SUMMARY
        # =========================================================================
        total_students = User.objects.filter(role=User.Role.STUDENT).count()
        total_requests = ExchangeRequest.objects.count()
        active_requests = ExchangeRequest.objects.filter(status=ExchangeRequest.RequestStatus.ACTIVE).count()

        from exchange.services.matching_service import MatchingService
        discovered = MatchingService.find_cycles()

        self.stdout.write("=================================================================")
        self.stdout.write(self.style.SUCCESS("[COMPLETED] Production Campus Matches Successfully Seeded!"))
        self.stdout.write("=================================================================")
        self.stdout.write(f"Total Student Accounts: {total_students}")
        self.stdout.write(f"Total Exchange Requests: {total_requests} (Active: {active_requests})")
        self.stdout.write(f"Discovered Graph Rotation Cycles: {len(discovered)}")
        
        cycle_types = {}
        for c in discovered:
            t = c['type_display']
            cycle_types[t] = cycle_types.get(t, 0) + 1
        for t, cnt in cycle_types.items():
            self.stdout.write(f"  - {t}: {cnt}")
        self.stdout.write("=================================================================")

