from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from exchange.models import (
    ExchangeProposal,
    ProposalParticipant,
    ExchangeRequest,
    PolicyRule,
    Notification
)
from hostel.models import Bed
from .audit_service import AuditService
from .notification_service import NotificationService

User = get_user_model()

class ProposalService:
    @classmethod
    def get_validity_hours(cls) -> int:
        try:
            rule = PolicyRule.objects.filter(rule_type=PolicyRule.RuleType.PROPOSAL_VALIDITY_HOURS, is_active=True).first()
            return rule.int_value if rule else 48
        except Exception:
            return 48

    @classmethod
    def create_proposal_from_match(cls, match_data: dict, creator: User) -> ExchangeProposal:
        """
        Creates an ExchangeProposal from a discovered graph cycle and initializes all participants.
        """
        with transaction.atomic():
            now = timezone.now()
            hours = cls.get_validity_hours()
            expires_at = now + timedelta(hours=hours)

            # Generate unique proposal code
            count = ExchangeProposal.objects.count() + 1
            code = f"PROP-{now.year}-{count:04d}"

            proposal = ExchangeProposal.objects.create(
                proposal_code=code,
                proposal_type=match_data.get('proposal_type', ExchangeProposal.ProposalType.DIRECT),
                status=ExchangeProposal.ProposalStatus.PENDING_ACCEPTANCE,
                compatibility_score=match_data.get('compatibility_score', 100.0),
                expires_at=expires_at
            )

            # Add participants
            participants = match_data.get('participants', [])
            for idx, p in enumerate(participants):
                student_id = p['student_id']
                student = User.objects.get(id=student_id)
                current_bed = Bed.objects.get(id=p['current_bed_id'])
                target_bed = Bed.objects.get(id=p['target_bed_id'])
                req_id = p.get('request_id')

                # If creator is the one initiating, mark as ACCEPTED right away
                resp = ProposalParticipant.ParticipantResponse.ACCEPTED if student == creator else ProposalParticipant.ParticipantResponse.PENDING
                resp_at = now if student == creator else None

                ProposalParticipant.objects.create(
                    proposal=proposal,
                    student=student,
                    request_id=req_id,
                    current_bed=current_bed,
                    target_bed=target_bed,
                    response=resp,
                    responded_at=resp_at,
                    order_index=idx
                )

                # Set request to PROPOSED
                if req_id:
                    ExchangeRequest.objects.filter(id=req_id).update(status=ExchangeRequest.RequestStatus.PROPOSED)

                # Send in-app notification
                if student != creator:
                    NotificationService.send(
                        recipient=student,
                        title="New Room Exchange Proposal Received",
                        message=f"You have been matched in a {proposal.get_proposal_type_display()} ({proposal.proposal_code}) for room {target_bed.room.room_number}. Review and accept before {expires_at.strftime('%d %b %H:%M')}.",
                        notification_type=Notification.NotificationType.PROPOSAL_RECEIVED,
                        link=f"/proposals/{proposal.id}/"
                    )

            # Check if all participants accepted (in case single-party or auto-acceptance)
            cls._evaluate_consensus(proposal)

            AuditService.log(
                action="PROPOSAL_CREATED",
                entity_type="ExchangeProposal",
                entity_id=proposal.id,
                actor=creator,
                new_state={"code": proposal.proposal_code, "type": proposal.proposal_type, "status": proposal.status},
                metadata={"participant_count": len(participants), "compatibility_score": proposal.compatibility_score}
            )

            return proposal

    @classmethod
    def respond_to_proposal(cls, proposal: ExchangeProposal, student: User, decision: str) -> dict:
        """
        Records participant's response. Enforces all-or-nothing consensus.
        """
        with transaction.atomic():
            participant = proposal.participants.filter(student=student).first()
            if not participant:
                return {'success': False, 'error': 'Student is not a participant in this proposal.'}

            if proposal.status not in [ExchangeProposal.ProposalStatus.PENDING_ACCEPTANCE, ExchangeProposal.ProposalStatus.PARTIALLY_ACCEPTED]:
                return {'success': False, 'error': f"Proposal cannot be modified. Current status: {proposal.get_status_display()}"}

            if timezone.now() > proposal.expires_at:
                proposal.status = ExchangeProposal.ProposalStatus.EXPIRED
                proposal.save()
                return {'success': False, 'error': 'Proposal has expired and can no longer receive responses.'}

            now = timezone.now()
            if decision == 'DECLINE':
                participant.response = ProposalParticipant.ParticipantResponse.DECLINED
                participant.responded_at = now
                participant.save()

                proposal.status = ExchangeProposal.ProposalStatus.DECLINED
                proposal.save()

                # Revert requests back to ACTIVE
                req_ids = proposal.participants.values_list('request_id', flat=True)
                ExchangeRequest.objects.filter(id__in=req_ids).update(status=ExchangeRequest.RequestStatus.ACTIVE)

                # Notify other participants
                for other_p in proposal.participants.exclude(student=student):
                    NotificationService.send(
                        recipient=other_p.student,
                        title="Exchange Proposal Terminated",
                        message=f"Proposal {proposal.proposal_code} was declined by a participant. Your exchange request has returned to active searching.",
                        notification_type=Notification.NotificationType.PARTICIPANT_DECLINED,
                        link=f"/proposals/{proposal.id}/"
                    )

                AuditService.log(
                    action="PROPOSAL_DECLINED",
                    entity_type="ExchangeProposal",
                    entity_id=proposal.id,
                    actor=student,
                    new_state={"status": proposal.status},
                    metadata={"declined_by": student.university_id}
                )

                return {'success': True, 'status': 'DECLINED', 'message': 'Proposal has been declined and terminated.'}

            elif decision == 'ACCEPT':
                participant.response = ProposalParticipant.ParticipantResponse.ACCEPTED
                participant.responded_at = now
                participant.save()

                consensus_status = cls._evaluate_consensus(proposal)

                AuditService.log(
                    action="PARTICIPANT_ACCEPTED",
                    entity_type="ExchangeProposal",
                    entity_id=proposal.id,
                    actor=student,
                    new_state={"status": proposal.status},
                    metadata={"accepted_by": student.university_id}
                )

                return {
                    'success': True,
                    'status': consensus_status,
                    'message': 'Your acceptance has been recorded.' if consensus_status != 'READY_FOR_APPROVAL' else 'All participants accepted! Proposal submitted to Warden for approval.'
                }

    @classmethod
    def _evaluate_consensus(cls, proposal: ExchangeProposal) -> str:
        """
        Evaluates whether all participants have accepted.
        If all accepted, sets status to READY_FOR_APPROVAL and alerts the Warden.
        """
        total = proposal.participants.count()
        accepted = proposal.participants.filter(response=ProposalParticipant.ParticipantResponse.ACCEPTED).count()

        if total > 0 and total == accepted:
            proposal.status = ExchangeProposal.ProposalStatus.READY_FOR_APPROVAL
            proposal.save()

            # Dispatch notification to wardens
            from accounts.models import User
            wardens = User.objects.filter(role__in=[User.Role.WARDEN, User.Role.CHIEF_WARDEN])
            for w in wardens:
                NotificationService.send(
                    recipient=w,
                    title="New Proposal Awaiting Warden Review",
                    message=f"Proposal {proposal.proposal_code} has full consensus ({total} students accepted). Ready for administrative verification and atomic execution.",
                    notification_type=Notification.NotificationType.READY_FOR_APPROVAL,
                    link=f"/warden/approvals/{proposal.id}/"
                )
            return ExchangeProposal.ProposalStatus.READY_FOR_APPROVAL
        elif accepted > 0:
            proposal.status = ExchangeProposal.ProposalStatus.PARTIALLY_ACCEPTED
            proposal.save()
            return ExchangeProposal.ProposalStatus.PARTIALLY_ACCEPTED
        else:
            return ExchangeProposal.ProposalStatus.PENDING_ACCEPTANCE

    @classmethod
    def sweep_expired_proposals(cls) -> int:
        """
        Background sweep task (Phase 11): Marks past-due proposals as EXPIRED.
        """
        now = timezone.now()
        expired_proposals = ExchangeProposal.objects.filter(
            expires_at__lt=now,
            status__in=[
                ExchangeProposal.ProposalStatus.PENDING_ACCEPTANCE,
                ExchangeProposal.ProposalStatus.PARTIALLY_ACCEPTED
            ]
        )
        count = 0
        for prop in expired_proposals:
            with transaction.atomic():
                prop.status = ExchangeProposal.ProposalStatus.EXPIRED
                prop.save()

                req_ids = prop.participants.values_list('request_id', flat=True)
                ExchangeRequest.objects.filter(id__in=req_ids).update(status=ExchangeRequest.RequestStatus.ACTIVE)

                for p in prop.participants.all():
                    NotificationService.send(
                        recipient=p.student,
                        title="Proposal Expired",
                        message=f"Proposal {prop.proposal_code} expired before all participants accepted. Your request has been reset to active search.",
                        notification_type=Notification.NotificationType.PROPOSAL_EXPIRED,
                        link=f"/proposals/{prop.id}/"
                    )

                AuditService.log(
                    action="PROPOSAL_EXPIRED",
                    entity_type="ExchangeProposal",
                    entity_id=prop.id,
                    new_state={"status": prop.status}
                )
                count += 1
        return count
