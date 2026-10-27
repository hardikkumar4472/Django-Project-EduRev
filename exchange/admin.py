from django.contrib import admin
from .models import (
    PolicyRule,
    ExchangeRequest,
    ExchangeProposal,
    ProposalParticipant,
    Approval,
    TransferRecord,
    Notification,
    AuditEntry,
    ProposalMessage,
)

@admin.register(PolicyRule)
class PolicyRuleAdmin(admin.ModelAdmin):
    list_display = ('rule_type', 'is_active', 'int_value', 'bool_value', 'updated_at', 'updated_by')
    list_filter = ('is_active',)
    search_fields = ('rule_type', 'description')

@admin.register(ExchangeRequest)
class ExchangeRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'requester', 'current_bed', 'preferred_hostel', 'preferred_room_type', 'status', 'created_at')
    list_filter = ('status', 'preferred_room_type', 'preferred_hostel')
    search_fields = ('requester__username', 'requester__first_name', 'requester__last_name', 'requester__university_id')
    ordering = ('-created_at',)

class ProposalParticipantInline(admin.TabularInline):
    model = ProposalParticipant
    extra = 0
    readonly_fields = ('responded_at',)

class ApprovalInline(admin.TabularInline):
    model = Approval
    extra = 0
    readonly_fields = ('created_at',)

@admin.register(ExchangeProposal)
class ExchangeProposalAdmin(admin.ModelAdmin):
    list_display = ('proposal_code', 'proposal_type', 'status', 'compatibility_score', 'expires_at', 'created_at')
    list_filter = ('status', 'proposal_type')
    search_fields = ('proposal_code',)
    inlines = [ProposalParticipantInline, ApprovalInline]
    ordering = ('-created_at',)

@admin.register(ProposalParticipant)
class ProposalParticipantAdmin(admin.ModelAdmin):
    list_display = ('id', 'proposal', 'student', 'current_bed', 'target_bed', 'response', 'responded_at')
    list_filter = ('response',)
    search_fields = ('student__username', 'student__university_id', 'proposal__proposal_code')

@admin.register(Approval)
class ApprovalAdmin(admin.ModelAdmin):
    list_display = ('id', 'proposal', 'approver', 'decision', 'created_at')
    list_filter = ('decision',)
    search_fields = ('approver__username', 'proposal__proposal_code')

@admin.register(TransferRecord)
class TransferRecordAdmin(admin.ModelAdmin):
    list_display = ('transfer_code', 'proposal', 'student', 'previous_bed', 'new_bed', 'approved_by', 'completed_at')
    search_fields = ('transfer_code', 'student__username', 'student__university_id')
    ordering = ('-completed_at',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('recipient__username', 'title')

@admin.register(AuditEntry)
class AuditEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'timestamp', 'actor', 'action', 'entity_type', 'entity_id')
    list_filter = ('action', 'entity_type')
    search_fields = ('actor__username', 'action', 'entity_type', 'entity_id')
    ordering = ('-timestamp',)

@admin.register(ProposalMessage)
class ProposalMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'proposal', 'sender', 'created_at')
    search_fields = ('sender__username', 'proposal__proposal_code', 'message')
