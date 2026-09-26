import uuid
from django.db import models
from django.conf import settings
from hostel.models import Hostel, Room, Bed

class PolicyRule(models.Model):
    class RuleType(models.TextChoices):
        COOLING_OFF_DAYS = 'COOLING_OFF_DAYS', 'Cooling-Off Period (Days)'
        MAX_CHAIN_LENGTH = 'MAX_CHAIN_LENGTH', 'Maximum Cycle Chain Length'
        PROPOSAL_VALIDITY_HOURS = 'PROPOSAL_VALIDITY_HOURS', 'Proposal Validity (Hours)'
        FEE_CLEARANCE_REQUIRED = 'FEE_CLEARANCE_REQUIRED', 'Mandatory Fee Clearance'
        DISCIPLINARY_CHECK = 'DISCIPLINARY_CHECK', 'Strict Disciplinary Hold Check'
        GENDER_STRICT_SEPARATION = 'GENDER_STRICT_SEPARATION', 'Strict Gender Residence Policy'

    rule_type = models.CharField(max_length=40, choices=RuleType.choices, unique=True)
    is_active = models.BooleanField(default=True)
    int_value = models.IntegerField(default=0, help_text="Numeric parameter e.g. 30 days or 5 chain length")
    bool_value = models.BooleanField(default=True, help_text="Boolean policy flag")
    description = models.CharField(max_length=255)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='modified_policies'
    )

    def __str__(self):
        val = self.int_value if 'DAYS' in self.rule_type or 'LENGTH' in self.rule_type or 'HOURS' in self.rule_type else self.bool_value
        return f"Policy [{self.get_rule_type_display()}]: {val} (Active: {self.is_active})"


class ExchangeRequest(models.Model):
    class RequestStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        ACTIVE = 'ACTIVE', 'Active & Searching'
        MATCHED = 'MATCHED', 'Match Found'
        PROPOSED = 'PROPOSED', 'In Proposal Cycle'
        COMPLETED = 'COMPLETED', 'Transfer Completed'
        WITHDRAWN = 'WITHDRAWN', 'Withdrawn by Student'
        EXPIRED = 'EXPIRED', 'Expired'
        REJECTED = 'REJECTED', 'Eligibility Rejected'

    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exchange_requests')
    current_bed = models.ForeignKey(Bed, on_delete=models.PROTECT, related_name='source_exchange_requests')
    
    # Target Preferences
    preferred_hostel = models.ForeignKey(Hostel, null=True, blank=True, on_delete=models.SET_NULL, related_name='targeted_requests')
    preferred_room_type = models.CharField(max_length=20, choices=Room.RoomType.choices, blank=True)
    preferred_floor = models.IntegerField(null=True, blank=True)
    specific_target_room = models.ForeignKey(Room, null=True, blank=True, on_delete=models.SET_NULL, related_name='directly_requested_in')
    reason = models.TextField(blank=True, help_text="Academic, medical, or study preference explanation")
    
    status = models.CharField(max_length=20, choices=RequestStatus.choices, default=RequestStatus.ACTIVE, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Req #{self.id} · {self.requester.get_full_name()} ({self.current_bed.room}) [{self.status}]"


class ExchangeProposal(models.Model):
    class ProposalType(models.TextChoices):
        DIRECT = 'DIRECT', 'Direct 2-Party Swap'
        CYCLE_3 = 'CYCLE_3', '3-Party Multi-Hop Cycle'
        CYCLE_4 = 'CYCLE_4', '4-Party Multi-Hop Cycle'
        CYCLE_5 = 'CYCLE_5', '5-Party Multi-Hop Cycle'

    class ProposalStatus(models.TextChoices):
        PENDING_ACCEPTANCE = 'PENDING_ACCEPTANCE', 'Pending Participant Acceptance'
        PARTIALLY_ACCEPTED = 'PARTIALLY_ACCEPTED', 'Partially Accepted'
        READY_FOR_APPROVAL = 'READY_FOR_APPROVAL', 'All Accepted · Ready for Warden'
        APPROVED = 'APPROVED', 'Warden Approved'
        DECLINED = 'DECLINED', 'Declined by Participant'
        EXPIRED = 'EXPIRED', 'Proposal Expired'
        COMPLETED = 'COMPLETED', 'Occupancy Transferred'
        CANCELLED = 'CANCELLED', 'Cancelled'

    proposal_code = models.CharField(max_length=30, unique=True, db_index=True)
    proposal_type = models.CharField(max_length=20, choices=ProposalType.choices, default=ProposalType.DIRECT)
    status = models.CharField(max_length=25, choices=ProposalStatus.choices, default=ProposalStatus.PENDING_ACCEPTANCE, db_index=True)
    compatibility_score = models.FloatField(default=100.0)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.proposal_code} [{self.get_proposal_type_display()}] — {self.get_status_display()}"

    @property
    def total_participants(self):
        return self.participants.count()

    @property
    def accepted_participants_count(self):
        return self.participants.filter(response=ProposalParticipant.ParticipantResponse.ACCEPTED).count()

    @property
    def is_cross_hostel(self):
        hostel_ids = set(self.participants.values_list('current_bed__room__block__hostel_id', flat=True))
        return len(hostel_ids) > 1


class ProposalParticipant(models.Model):
    class ParticipantResponse(models.TextChoices):
        PENDING = 'PENDING', 'Pending Decision'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        DECLINED = 'DECLINED', 'Declined'

    proposal = models.ForeignKey(ExchangeProposal, on_delete=models.CASCADE, related_name='participants')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='proposal_participations')
    request = models.ForeignKey(ExchangeRequest, null=True, blank=True, on_delete=models.SET_NULL, related_name='participations')
    current_bed = models.ForeignKey(Bed, on_delete=models.PROTECT, related_name='participant_departures')
    target_bed = models.ForeignKey(Bed, on_delete=models.PROTECT, related_name='participant_destinations')
    response = models.CharField(max_length=15, choices=ParticipantResponse.choices, default=ParticipantResponse.PENDING)
    responded_at = models.DateTimeField(null=True, blank=True)
    order_index = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('proposal', 'student')
        ordering = ['order_index']

    def __str__(self):
        return f"{self.student.get_full_name()} ({self.current_bed.room.room_number} -> {self.target_bed.room.room_number}) [{self.response}]"


class Approval(models.Model):
    class Decision(models.TextChoices):
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    proposal = models.ForeignKey(ExchangeProposal, on_delete=models.CASCADE, related_name='approvals')
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='granted_approvals')
    decision = models.CharField(max_length=15, choices=Decision.choices, default=Decision.APPROVED)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.decision} by {self.approver.get_full_name()} on {self.proposal.proposal_code}"


class TransferRecord(models.Model):
    transfer_code = models.CharField(max_length=35, unique=True, db_index=True)
    proposal = models.ForeignKey(ExchangeProposal, on_delete=models.PROTECT, related_name='transfer_records')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='completed_transfers')
    previous_bed = models.ForeignKey(Bed, on_delete=models.PROTECT, related_name='transferred_from_records')
    new_bed = models.ForeignKey(Bed, on_delete=models.PROTECT, related_name='transferred_to_records')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='authorized_transfers')
    completed_at = models.DateTimeField(auto_now_add=True)
    verification_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        ordering = ['-completed_at']

    def __str__(self):
        return f"{self.transfer_code} · {self.student.get_full_name()} -> {self.new_bed.room.full_name}"


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        PROPOSAL_RECEIVED = 'PROPOSAL_RECEIVED', 'Exchange Proposal Received'
        PARTICIPANT_ACCEPTED = 'PARTICIPANT_ACCEPTED', 'Participant Accepted'
        PARTICIPANT_DECLINED = 'PARTICIPANT_DECLINED', 'Participant Declined'
        READY_FOR_APPROVAL = 'READY_FOR_APPROVAL', 'Proposal Ready for Warden Approval'
        TRANSFER_COMPLETED = 'TRANSFER_COMPLETED', 'Transfer Completed Successfully'
        PROPOSAL_EXPIRED = 'PROPOSAL_EXPIRED', 'Proposal Expired'
        GENERAL_ALERT = 'GENERAL_ALERT', 'General Alert'

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=150)
    message = models.TextField()
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices, default=NotificationType.GENERAL_ALERT)
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.notification_type}] -> {self.recipient.username}: {self.title}"


class AuditEntry(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_actions')
    action = models.CharField(max_length=80, db_index=True)
    entity_type = models.CharField(max_length=50, db_index=True)
    entity_id = models.CharField(max_length=50)
    previous_state = models.JSONField(null=True, blank=True)
    new_state = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        actor_name = self.actor.username if self.actor else "SYSTEM"
        return f"{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} · {actor_name} -> {self.action} [{self.entity_type} #{self.entity_id}]"
