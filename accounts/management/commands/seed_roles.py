from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from hostel.models import Hostel, Bed

User = get_user_model()

class Command(BaseCommand):
    help = "Seeds separate warden accounts hostel-wise (10 Boys Hostels, 10 Girls Hostels) plus student, chief_warden, dsw, and admin accounts."

    def handle(self, *args, **options):
        self.stdout.write("Seeding hostel-wise warden accounts and core role users...")

        with transaction.atomic():
            # 1. Seed Core Role Accounts: student, chief_warden, admin, dsw
            core_users = [
                {
                    "username": "student",
                    "email": "student@gmail.com",
                    "password": "student@123",
                    "role": User.Role.STUDENT,
                    "university_id": "STU202601",
                    "first_name": "Aarav",
                    "last_name": "Sharma",
                    "gender": User.Gender.MALE,
                    "is_staff": False,
                    "is_superuser": False,
                },
                {
                    "username": "chief_warden",
                    "email": "chief_warden@gmail.com",
                    "password": "chief_warden@123",
                    "role": User.Role.CHIEF_WARDEN,
                    "university_id": "CWR202601",
                    "first_name": "Rajesh",
                    "last_name": "Verma",
                    "gender": User.Gender.MALE,
                    "is_staff": False,
                    "is_superuser": False,
                },
                {
                    "username": "admin",
                    "email": "admin@gmail.com",
                    "password": "admin@123",
                    "role": User.Role.ADMIN,
                    "university_id": "ADM202601",
                    "first_name": "System",
                    "last_name": "Administrator",
                    "gender": User.Gender.MALE,
                    "is_staff": True,
                    "is_superuser": True,
                },
                {
                    "username": "dsw",
                    "email": "dsw@gmail.com",
                    "password": "dsw@123",
                    "role": User.Role.DSW,
                    "university_id": "DSW202601",
                    "first_name": "Ananya",
                    "last_name": "Iyer",
                    "gender": User.Gender.FEMALE,
                    "is_staff": False,
                    "is_superuser": False,
                },
            ]

            for conf in core_users:
                user = User.objects.filter(username=conf["username"]).first() or User.objects.filter(email=conf["email"]).first()
                if user:
                    user.username = conf["username"]
                    user.email = conf["email"]
                    user.role = conf["role"]
                    user.university_id = conf["university_id"]
                    user.first_name = conf["first_name"]
                    user.last_name = conf["last_name"]
                    user.gender = conf["gender"]
                    user.is_staff = conf["is_staff"]
                    user.is_superuser = conf["is_superuser"]
                    user.set_password(conf["password"])
                    user.save()
                    action = "Updated"
                else:
                    user = User.objects.create(
                        username=conf["username"],
                        email=conf["email"],
                        role=conf["role"],
                        university_id=conf["university_id"],
                        first_name=conf["first_name"],
                        last_name=conf["last_name"],
                        gender=conf["gender"],
                        is_staff=conf["is_staff"],
                        is_superuser=conf["is_superuser"],
                    )
                    user.set_password(conf["password"])
                    user.save()
                    action = "Created"

                self.stdout.write(f"  [+] {action} User: {user.username} ({user.email}) -> Role: {user.role}")

                # Allocate student to a vacant bed in BH-1
                if user.is_student and not hasattr(user, 'allocated_bed'):
                    vacant_bed = Bed.objects.filter(
                        room__block__hostel__code="BH-1",
                        occupancy_status=Bed.OccupancyStatus.VACANT
                    ).first()
                    if vacant_bed:
                        vacant_bed.current_occupant = user
                        vacant_bed.occupancy_status = Bed.OccupancyStatus.OCCUPIED
                        vacant_bed.save()
                        self.stdout.write(f"      -> Allocated to {vacant_bed.room.full_name} ({vacant_bed.bed_number})")

            # 2. Seed 10 Boys Hostel Wardens: BH-1 to BH-10
            self.stdout.write("\nSeeding 10 Boys Hostel Wardens (wardenbh1 to wardenbh10)...")
            for i in range(1, 11):
                code = f"BH-{i}"
                email = f"wardenbh{i}@gmail.com"
                password = f"wardenbh{i}@123"
                username = f"warden_bh{i}"
                uni_id = f"WRD_BH_{i:02d}"

                user = User.objects.filter(username=username).first() or User.objects.filter(email=email).first()
                if user:
                    user.username = username
                    user.email = email
                    user.role = User.Role.WARDEN
                    user.university_id = uni_id
                    user.first_name = f"Warden BH-{i}"
                    user.last_name = "In-Charge"
                    user.gender = User.Gender.MALE
                    user.set_password(password)
                    user.save()
                    action = "Updated"
                else:
                    user = User.objects.create(
                        username=username,
                        email=email,
                        role=User.Role.WARDEN,
                        university_id=uni_id,
                        first_name=f"Warden BH-{i}",
                        last_name="In-Charge",
                        gender=User.Gender.MALE,
                    )
                    user.set_password(password)
                    user.save()
                    action = "Created"

                # Assign this warden to Boys Hostel i
                hostel = Hostel.objects.filter(code=code).first()
                if hostel:
                    hostel.warden = user
                    hostel.save()
                    self.stdout.write(f"  [+] {action} {username} | {email} | Password: {password} -> Assigned to {hostel.name} ({hostel.code})")

            # 3. Seed 10 Girls Hostel Wardens: GH-1 to GH-10
            self.stdout.write("\nSeeding 10 Girls Hostel Wardens (wardengh1 to wardengh10)...")
            for i in range(1, 11):
                code = f"GH-{i}"
                email = f"wardengh{i}@gmail.com"
                password = f"wardengh{i}@123"
                username = f"warden_gh{i}"
                uni_id = f"WRD_GH_{i:02d}"

                user = User.objects.filter(username=username).first() or User.objects.filter(email=email).first()
                if user:
                    user.username = username
                    user.email = email
                    user.role = User.Role.WARDEN
                    user.university_id = uni_id
                    user.first_name = f"Warden GH-{i}"
                    user.last_name = "In-Charge"
                    user.gender = User.Gender.FEMALE
                    user.set_password(password)
                    user.save()
                    action = "Updated"
                else:
                    user = User.objects.create(
                        username=username,
                        email=email,
                        role=User.Role.WARDEN,
                        university_id=uni_id,
                        first_name=f"Warden GH-{i}",
                        last_name="In-Charge",
                        gender=User.Gender.FEMALE,
                    )
                    user.set_password(password)
                    user.save()
                    action = "Created"

                # Assign this warden to Girls Hostel i
                hostel = Hostel.objects.filter(code=code).first()
                if hostel:
                    hostel.warden = user
                    hostel.save()
                    self.stdout.write(f"  [+] {action} {username} | {email} | Password: {password} -> Assigned to {hostel.name} ({hostel.code})")

        self.stdout.write(self.style.SUCCESS(
            "\nSuccessfully seeded all 20 hostel wardens (10 Boys, 10 Girls) and core roles!"
        ))
