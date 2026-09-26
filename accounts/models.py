from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'student', 'Student'
        WARDEN = 'warden', 'Hostel Warden'
        CHIEF_WARDEN = 'chief_warden', 'Chief Warden'
        ADMIN = 'admin', 'Hostel Administrator'
        DSW = 'dsw', 'Dean of Student Welfare (DSW)'

    class Gender(models.TextChoices):
        MALE = 'M', 'Male'
        FEMALE = 'F', 'Female'
        OTHER = 'O', 'Other'

    university_id = models.CharField(max_length=30, unique=True, db_index=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT, db_index=True)
    phone = models.CharField(max_length=20, blank=True)
    gender = models.CharField(max_length=1, choices=Gender.choices, default=Gender.MALE)
    
    # Eligibility indicators
    has_fee_clearance = models.BooleanField(default=True, help_text="Verified student fee clearance")
    has_disciplinary_hold = models.BooleanField(default=False, help_text="Active university disciplinary restriction")
    last_transferred_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp of last completed room swap")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.university_id}) [{self.role.upper()}]"

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_warden(self):
        return self.role in (self.Role.WARDEN, self.Role.CHIEF_WARDEN)

    @property
    def is_chief_warden(self):
        return self.role == self.Role.CHIEF_WARDEN

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_dsw(self):
        return self.role == self.Role.DSW
