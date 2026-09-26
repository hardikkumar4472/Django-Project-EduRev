from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from hostel.models import Hostel, Room, Bed
from exchange.models import ExchangeRequest

User = get_user_model()

class Command(BaseCommand):
    help = "Seeds matching partner students across BH-2, BH-3, and BH-4 to demonstrate direct and cyclic swaps"

    def handle(self, *args, **options):
        self.stdout.write("Seeding sample matching students...")

        bh1 = Hostel.objects.filter(code='BH-1').first()
        bh2 = Hostel.objects.filter(code='BH-2').first()
        bh3 = Hostel.objects.filter(code='BH-3').first()

        if not (bh1 and bh2 and bh3):
            self.stderr.write("Hostels BH-1, BH-2, or BH-3 not found. Run setup_hostels first.")
            return

        # -------------------------------------------------------------
        # 1. Seed student_bh2 (in BH-2 Room 101 [Single], wants BH-1)
        # -------------------------------------------------------------
        u2, created = User.objects.get_or_create(
            username='student_bh2',
            defaults={
                'email': 'student_bh2@gmail.com',
                'first_name': 'Rohan',
                'last_name': 'Verma',
                'university_id': 'STU-BH2-01',
                'role': User.Role.STUDENT,
                'gender': User.Gender.MALE,
                'has_fee_clearance': True,
                'has_disciplinary_hold': False,
            }
        )
        u2.set_password('student@123')
        u2.has_fee_clearance = True
        u2.has_disciplinary_hold = False
        u2.save()

        room_bh2_101 = Room.objects.filter(block__hostel=bh2, room_number='101').first()
        if room_bh2_101:
            bed2 = room_bh2_101.beds.first()
            if bed2:
                bed2.current_occupant = u2
                bed2.occupancy_status = Bed.OccupancyStatus.OCCUPIED
                bed2.save()

        # Create or update exchange request for student_bh2
        req2 = ExchangeRequest.objects.filter(requester=u2, status=ExchangeRequest.RequestStatus.ACTIVE).first()
        if not req2:
            ExchangeRequest.objects.create(
                requester=u2,
                current_bed=u2.allocated_bed,
                preferred_hostel=bh1,
                preferred_room_type='SINGLE',
                reason="Requesting transfer closer to academic block in BH-1.",
                status=ExchangeRequest.RequestStatus.ACTIVE
            )
        else:
            req2.preferred_hostel = bh1
            req2.preferred_room_type = 'SINGLE'
            req2.save()

        self.stdout.write(self.style.SUCCESS("[OK] Seeded student_bh2 in BH-2 (wants BH-1)"))

        # -------------------------------------------------------------
        # 2. Seed student_bh3 (in BH-3 Room 101 [Single], wants BH-2 or BH-1)
        # -------------------------------------------------------------
        u3, created = User.objects.get_or_create(
            username='student_bh3',
            defaults={
                'email': 'student_bh3@gmail.com',
                'first_name': 'Siddharth',
                'last_name': 'Mehta',
                'university_id': 'STU-BH3-01',
                'role': User.Role.STUDENT,
                'gender': User.Gender.MALE,
                'has_fee_clearance': True,
                'has_disciplinary_hold': False,
            }
        )
        u3.set_password('student@123')
        u3.has_fee_clearance = True
        u3.has_disciplinary_hold = False
        u3.save()

        room_bh3_101 = Room.objects.filter(block__hostel=bh3, room_number='101').first()
        if room_bh3_101:
            bed3 = room_bh3_101.beds.first()
            if bed3:
                bed3.current_occupant = u3
                bed3.occupancy_status = Bed.OccupancyStatus.OCCUPIED
                bed3.save()

        req3 = ExchangeRequest.objects.filter(requester=u3, status=ExchangeRequest.RequestStatus.ACTIVE).first()
        if not req3:
            ExchangeRequest.objects.create(
                requester=u3,
                current_bed=u3.allocated_bed,
                preferred_hostel=bh1,
                preferred_room_type='SINGLE',
                reason="Departmental study group coordination.",
                status=ExchangeRequest.RequestStatus.ACTIVE
            )
        else:
            req3.preferred_hostel = bh1
            req3.preferred_room_type = 'SINGLE'
            req3.save()

        self.stdout.write(self.style.SUCCESS("[OK] Seeded student_bh3 in BH-3 (wants BH-1)"))

        # -------------------------------------------------------------
        # 3. Seed student_2s_a & student_2s_b (2-Seater Sample Swap)
        # -------------------------------------------------------------
        u_2s_a, _ = User.objects.get_or_create(
            username='student_2s_a',
            defaults={
                'email': 'student_2sa@gmail.com',
                'first_name': 'Kunal',
                'last_name': 'Kapoor',
                'university_id': 'STU-2SA-01',
                'role': User.Role.STUDENT,
                'gender': User.Gender.MALE,
                'has_fee_clearance': True,
                'has_disciplinary_hold': False,
            }
        )
        u_2s_a.set_password('student@123')
        u_2s_a.has_fee_clearance = True
        u_2s_a.has_disciplinary_hold = False
        u_2s_a.save()

        room_bh1_102 = Room.objects.filter(block__hostel=bh1, room_number='102').first()
        if room_bh1_102:
            bed_2sa = room_bh1_102.beds.first()
            if bed_2sa:
                bed_2sa.current_occupant = u_2s_a
                bed_2sa.occupancy_status = Bed.OccupancyStatus.OCCUPIED
                bed_2sa.save()

        if not ExchangeRequest.objects.filter(requester=u_2s_a, status=ExchangeRequest.RequestStatus.ACTIVE).exists():
            ExchangeRequest.objects.create(
                requester=u_2s_a,
                current_bed=u_2s_a.allocated_bed,
                preferred_hostel=bh2,
                preferred_room_type='DOUBLE',
                reason="Looking for double room in BH-2.",
                status=ExchangeRequest.RequestStatus.ACTIVE
            )

        u_2s_b, _ = User.objects.get_or_create(
            username='student_2s_b',
            defaults={
                'email': 'student_2sb@gmail.com',
                'first_name': 'Vikram',
                'last_name': 'Patel',
                'university_id': 'STU-2SB-01',
                'role': User.Role.STUDENT,
                'gender': User.Gender.MALE,
                'has_fee_clearance': True,
                'has_disciplinary_hold': False,
            }
        )
        u_2s_b.set_password('student@123')
        u_2s_b.has_fee_clearance = True
        u_2s_b.has_disciplinary_hold = False
        u_2s_b.save()

        room_bh2_102 = Room.objects.filter(block__hostel=bh2, room_number='102').first()
        if room_bh2_102:
            bed_2sb = room_bh2_102.beds.first()
            if bed_2sb:
                bed_2sb.current_occupant = u_2s_b
                bed_2sb.occupancy_status = Bed.OccupancyStatus.OCCUPIED
                bed_2sb.save()

        if not ExchangeRequest.objects.filter(requester=u_2s_b, status=ExchangeRequest.RequestStatus.ACTIVE).exists():
            ExchangeRequest.objects.create(
                requester=u_2s_b,
                current_bed=u_2s_b.allocated_bed,
                preferred_hostel=bh1,
                preferred_room_type='DOUBLE',
                reason="Looking for double room in BH-1.",
                status=ExchangeRequest.RequestStatus.ACTIVE
            )

        self.stdout.write(self.style.SUCCESS("[OK] Seeded 2-seater sample pair (student_2s_a <-> student_2s_b)"))
        self.stdout.write(self.style.SUCCESS("All matching students seeded successfully! Refresh /matches/ to explore cycles."))
