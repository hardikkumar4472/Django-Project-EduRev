from django.db import models
from django.conf import settings

class Hostel(models.Model):
    class GenderType(models.TextChoices):
        MALE = 'MALE', 'Boys Hostel'
        FEMALE = 'FEMALE', 'Girls Hostel'
        COED = 'COED', 'Co-Ed Residence'

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    gender_type = models.CharField(max_length=10, choices=GenderType.choices, default=GenderType.MALE)
    is_active = models.BooleanField(default=True)
    warden = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='managed_hostels'
    )

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def total_capacity(self):
        return Bed.objects.filter(room__block__hostel=self).count()

    @property
    def occupied_beds_count(self):
        return Bed.objects.filter(room__block__hostel=self, occupancy_status='OCCUPIED').count()

    @property
    def vacant_beds_count(self):
        return Bed.objects.filter(room__block__hostel=self, occupancy_status='VACANT').count()


class Block(models.Model):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name='blocks')
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=10)

    class Meta:
        unique_together = ('hostel', 'code')

    def __str__(self):
        return f"{self.hostel.code} - Block {self.name}"


class Room(models.Model):
    class RoomType(models.TextChoices):
        SINGLE = 'SINGLE', '1-Seater (Single)'
        DOUBLE = 'DOUBLE', '2-Seater (Double Sharing)'
        TRIPLE = 'TRIPLE', '3-Seater (Triple Sharing)'
        FOUR_SHARING = 'FOUR_SHARING', '4-Seater (Quad Sharing)'
        SEVEN_SEATER = 'SEVEN_SEATER', '7-Seater (Dormitory)'
        EIGHT_SEATER = 'EIGHT_SEATER', '8-Seater (Dormitory)'

    block = models.ForeignKey(Block, on_delete=models.CASCADE, related_name='rooms')
    room_number = models.CharField(max_length=20)
    floor = models.IntegerField(default=1)
    room_type = models.CharField(max_length=20, choices=RoomType.choices, default=RoomType.DOUBLE)
    capacity = models.PositiveIntegerField(default=2)
    has_attached_bath = models.BooleanField(default=False)
    has_ac = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('block', 'room_number')
        ordering = ['block', 'floor', 'room_number']

    def __str__(self):
        return f"{self.block.hostel.code}-{self.block.code}-{self.room_number}"

    @property
    def full_name(self):
        return f"{self.block.hostel.name} [{self.block.name}] Room {self.room_number}"


class Bed(models.Model):
    class OccupancyStatus(models.TextChoices):
        VACANT = 'VACANT', 'Vacant'
        OCCUPIED = 'OCCUPIED', 'Occupied'
        LOCKED_FOR_TRANSFER = 'LOCKED_FOR_TRANSFER', 'Locked for Transfer'
        MAINTENANCE = 'MAINTENANCE', 'Under Maintenance'

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='beds')
    bed_number = models.CharField(max_length=20)
    current_occupant = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='allocated_bed'
    )
    occupancy_status = models.CharField(
        max_length=25,
        choices=OccupancyStatus.choices,
        default=OccupancyStatus.VACANT,
        db_index=True
    )

    class Meta:
        unique_together = ('room', 'bed_number')
        ordering = ['room', 'bed_number']

    def __str__(self):
        occupant_str = self.current_occupant.get_full_name() if self.current_occupant else "Vacant"
        return f"{self.room.full_name} ({self.bed_number}) -> {occupant_str}"
