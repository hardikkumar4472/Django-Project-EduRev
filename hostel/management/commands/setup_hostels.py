from django.core.management.base import BaseCommand
from django.db import transaction
from hostel.models import Hostel, Block, Room, Bed
from exchange.models import ExchangeRequest, ProposalParticipant, TransferRecord

class Command(BaseCommand):
    help = "Resets all existing hostels and creates 10 Boys Hostels (BH-1 to BH-10) and 10 Girls Hostels (GH-1 to GH-10) with blocks, rooms, and vacant beds."

    def handle(self, *args, **options):
        self.stdout.write("Resetting existing hostels and beds...")

        with transaction.atomic():
            # Clear any records linked to old beds/rooms
            TransferRecord.objects.all().delete()
            ProposalParticipant.objects.all().delete()
            ExchangeRequest.objects.all().delete()
            Bed.objects.all().delete()
            Room.objects.all().delete()
            Block.objects.all().delete()
            Hostel.objects.all().delete()

            # Helper function to generate blocks, rooms, and beds for a hostel
            def generate_hostel_structure(hostel, blocks=('A', 'B'), floors=3, rooms_per_floor=6):
                room_configs = {
                    1: (Room.RoomType.SINGLE, 1),
                    2: (Room.RoomType.DOUBLE, 2),
                    3: (Room.RoomType.TRIPLE, 3),
                    4: (Room.RoomType.FOUR_SHARING, 4),
                    5: (Room.RoomType.SEVEN_SEATER, 7),
                    6: (Room.RoomType.EIGHT_SEATER, 8),
                }
                for b_code in blocks:
                    block = Block.objects.create(
                        hostel=hostel,
                        name=f"Block {b_code}",
                        code=b_code
                    )
                    for floor in range(1, floors + 1):
                        for r_idx in range(1, rooms_per_floor + 1):
                            r_number = f"{floor}{r_idx:02d}"
                            r_type, cap = room_configs.get(r_idx, (Room.RoomType.DOUBLE, 2))
                            
                            room = Room.objects.create(
                                block=block,
                                room_number=r_number,
                                floor=floor,
                                room_type=r_type,
                                capacity=cap,
                                has_attached_bath=(r_idx <= 2),
                                has_ac=(floor >= 2)
                            )

                            for bed_idx in range(1, cap + 1):
                                Bed.objects.create(
                                    room=room,
                                    bed_number=f"Bed {bed_idx}",
                                    occupancy_status=Bed.OccupancyStatus.VACANT
                                )

            # 1. Create 10 Boys Hostels: BH-1 to BH-10
            for i in range(1, 11):
                h = Hostel.objects.create(
                    name=f"Boys Hostel {i}",
                    code=f"BH-{i}",
                    gender_type=Hostel.GenderType.MALE,
                    is_active=True
                )
                generate_hostel_structure(h)
                self.stdout.write(f"  + Created Boys Hostel: {h.name} ({h.code})")

            # 2. Create 10 Girls Hostels: GH-1 to GH-10
            for i in range(1, 11):
                h = Hostel.objects.create(
                    name=f"Girls Hostel {i}",
                    code=f"GH-{i}",
                    gender_type=Hostel.GenderType.FEMALE,
                    is_active=True
                )
                generate_hostel_structure(h)
                self.stdout.write(f"  + Created Girls Hostel: {h.name} ({h.code})")

        total_hostels = Hostel.objects.count()
        total_blocks = Block.objects.count()
        total_rooms = Room.objects.count()
        total_beds = Bed.objects.count()

        self.stdout.write(self.style.SUCCESS(
            f"\nSuccessfully configured 20 Hostels:\n"
            f"  • {total_hostels} Hostels (10 Boys: BH-1 to BH-10, 10 Girls: GH-1 to GH-10)\n"
            f"  • {total_blocks} Blocks\n"
            f"  • {total_rooms} Rooms\n"
            f"  • {total_beds} Vacant Beds ready for allocation and exchange."
        ))
