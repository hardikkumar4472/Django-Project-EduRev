import random
from django.db import models
from django.conf import settings
from django.utils import timezone
from hostel.models import Hostel, Room

class RMSRequest(models.Model):
    class MessageType(models.TextChoices):
        MAINTENANCE_REQUEST = 'MAINTENANCE_REQUEST', 'Maintenance Request'
        COMPLAINT = 'COMPLAINT', 'Hostel Complaint'
        GRIEVANCE = 'GRIEVANCE', 'Urgent Grievance'
        ASSISTANCE = 'ASSISTANCE', 'Caretaker Assistance'

    class Category(models.TextChoices):
        ELECTRICAL = 'ELECTRICAL', 'Electrical & Air Conditioning'
        PLUMBING = 'PLUMBING', 'Plumbing & Sanitation'
        CARPENTRY = 'CARPENTRY', 'Furniture & Carpentry'
        INTERNET_WIFI = 'INTERNET_WIFI', 'Hostel Wi-Fi & Network'
        HOUSEKEEPING = 'HOUSEKEEPING', 'Cleaning & Washroom Hygiene'
        MESS_WATER = 'MESS_WATER', 'Drinking RO Water & Mess Food'
        SECURITY_APPLIANCE = 'SECURITY_APPLIANCE', 'Door Locks, Curfew & Security'
        OTHER = 'OTHER', 'Other Hostel Maintenance'

    class SubCategory(models.TextChoices):
        AIR_CONDITIONER = 'AIR_CONDITIONER', 'Window / Split AC Not Cooling / Remote'
        FAN_LIGHT = 'FAN_LIGHT', 'Ceiling Fan / Tube Light / Plug Socket'
        GEYSER_HOT_WATER = 'GEYSER_HOT_WATER', 'Geyser / Solar Water Heater'
        TAP_LEAKAGE_DRAIN = 'TAP_LEAKAGE_DRAIN', 'Tap Leakage / Drain Clogged / Flush'
        WATER_COOLER_RO = 'WATER_COOLER_RO', 'Floor RO Filter / Water Cooler'
        BED_ALMIRAH_CHAIR = 'BED_ALMIRAH_CHAIR', 'Bed Frame / Almirah Locker / Study Table'
        DOOR_LOCK_WINDOW = 'DOOR_LOCK_WINDOW', 'Door Latch / Lock Broken / Window Glass'
        WIFI_SPEED_DISCONNECT = 'WIFI_SPEED_DISCONNECT', 'Wi-Fi AP Drop / Login Failure'
        CLEANLINESS_WASHROOM = 'CLEANLINESS_WASHROOM', 'Room Dusting / Washroom Cleaning'
        PEST_CONTROL = 'PEST_CONTROL', 'Pest Control / Mosquito Spray'
        OTHER = 'OTHER', 'Other Hostel Issue'

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        ESCALATED_DEAN = 'ESCALATED_DEAN', 'Escalated to Dean (DSW)'
        ESCALATED_CHIEF_WARDEN = 'ESCALATED_CHIEF_WARDEN', 'Escalated to Chief Warden'
        ESCALATED_ADMIN = 'ESCALATED_ADMIN', 'Escalated to System Administrator'
        RESOLVED = 'RESOLVED', 'Resolved'
        CLOSED = 'CLOSED', 'Closed'

    class Priority(models.TextChoices):
        NORMAL = 'NORMAL', 'Normal'
        HIGH = 'HIGH', 'High (Urgent)'
        EMERGENCY = 'EMERGENCY', 'Emergency'

    # Auto-generated ticket code: mt/Sep-26/03121 style
    ticket_code = models.CharField(max_length=40, unique=True, db_index=True)

    # Student raising the request
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rms_requests'
    )

    # Hostel associated with student / query
    hostel = models.ForeignKey(
        Hostel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rms_tickets'
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rms_tickets'
    )
    room_number_str = models.CharField(max_length=50, blank=True)
    contact_phone = models.CharField(max_length=25, blank=True)

    message_type = models.CharField(
        max_length=25,
        choices=MessageType.choices,
        default=MessageType.MAINTENANCE_REQUEST
    )
    category = models.CharField(
        max_length=40,
        choices=Category.choices,
        default=Category.ELECTRICAL
    )
    sub_category = models.CharField(
        max_length=40,
        choices=SubCategory.choices,
        default=SubCategory.AIR_CONDITIONER
    )

    subject = models.CharField(max_length=200)
    description = models.TextField()

    availability_date = models.DateField(null=True, blank=True)
    time_slot = models.CharField(max_length=60, blank=True)

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL
    )

    # Assigned staff / Current handling authority
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_rms_tickets'
    )

    # Escalation info
    escalated_from_warden = models.BooleanField(default=False)
    escalation_reason = models.TextField(blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    escalated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='escalated_rms_tickets'
    )

    # Resolution & Feedback
    closing_remarks = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_rms_tickets'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    student_rating = models.IntegerField(null=True, blank=True, help_text="Rating out of 5 stars")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ticket_code} - {self.subject} ({self.get_status_display()})"

    @classmethod
    def generate_ticket_code(cls):
        now = timezone.now()
        month_str = now.strftime('%b-%y')
        random_num = random.randint(10000, 99999)
        return f"mt/{month_str}/{random_num}"

    def save(self, *args, **kwargs):
        if not self.ticket_code:
            code = self.generate_ticket_code()
            while RMSRequest.objects.filter(ticket_code=code).exists():
                code = self.generate_ticket_code()
            self.ticket_code = code
        super().save(*args, **kwargs)


class RMSComment(models.Model):
    ticket = models.ForeignKey(RMSRequest, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.TextField()
    is_internal = models.BooleanField(default=False, help_text="Visible only to Wardens, Deans, and Admins")
    action_taken = models.CharField(max_length=60, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on {self.ticket.ticket_code}"
