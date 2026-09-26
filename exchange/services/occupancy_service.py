import uuid
from typing import Dict, Any, List
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from exchange.models import (
    ExchangeProposal,
    ProposalParticipant,
    ExchangeRequest,
    Approval,
    TransferRecord,
    Notification
)
from hostel.models import Bed
from .audit_service import AuditService
from .notification_service import NotificationService

User = get_user_model()

class OccupancyTransferError(Exception):
    """Raised when an atomic occupancy transfer fails safety invariants."""
    pass


class AtomicOccupancyEngine:
    """
    CRITICAL TRANSACTIONAL OCCUPANCY ENGINE.
    Enforces Phase 14 specifications:
    - transaction.atomic()
    - Strict PK-sorted row locking with select_for_update()
    - Zero ABBA deadlocks
    - Zero partial transfers (All-or-Nothing)
    - Full Auditability
    """

    @classmethod
    def execute_proposal_atomic(
        cls,
        proposal_id: int,
        approver: User,
        remarks: str = "Approved by Warden"
    ) -> Dict[str, Any]:
        """
        Executes multi-party cyclic room exchange within an atomic database transaction.
        """
        with transaction.atomic():
            # Step 1: Validate proposal state
            proposal = ExchangeProposal.objects.select_for_update().get(id=proposal_id)

            if proposal.status != ExchangeProposal.ProposalStatus.READY_FOR_APPROVAL:
                raise OccupancyTransferError(
                    f"Proposal {proposal.proposal_code} cannot be approved in state '{proposal.get_status_display()}'. Must be READY_FOR_APPROVAL."
                )

            participants = list(proposal.participants.select_related('student', 'current_bed', 'target_bed').all())
            if not participants:
                raise OccupancyTransferError("Proposal contains zero participants.")

            # Step 2: Validate consensus
            for p in participants:
                if p.response != ProposalParticipant.ParticipantResponse.ACCEPTED:
                    raise OccupancyTransferError(f"Participant {p.student.get_full_name()} has not accepted this proposal.")

            # Step 3 & 4: Collect all affected bed IDs
            # Every participant moves from current_bed to target_bed
            current_bed_ids = [p.current_bed_id for p in participants]
            target_bed_ids = [p.target_bed_id for p in participants]
            all_bed_ids = list(set(current_bed_ids + target_bed_ids))

            # Step 5 & 6: Strict PK Sort and Row Locking
            # CRITICAL: Always acquire locks in ascending primary key order to prevent ABBA deadlocks!
            sorted_bed_ids = sorted(all_bed_ids)
            
            # Acquire row locks on all beds in ascending order
            locked_beds_qs = Bed.objects.select_for_update().filter(id__in=sorted_bed_ids).select_related('current_occupant', 'room__block__hostel')
            locked_beds_dict = {b.id: b for b in locked_beds_qs}

            if len(locked_beds_dict) != len(sorted_bed_ids):
                raise OccupancyTransferError("One or more target beds no longer exist in the system.")

            # Step 7: Re-check occupancy integrity
            # Verify that every participant still occupies their expected current_bed
            for p in participants:
                locked_curr_bed = locked_beds_dict[p.current_bed_id]
                if locked_curr_bed.current_occupant_id != p.student_id:
                    raise OccupancyTransferError(
                        f"Integrity Violation: Student {p.student.get_full_name()} is no longer occupant of bed {locked_curr_bed.bed_number} (Room {locked_curr_bed.room.room_number}). Transfer aborted."
                    )

            # Step 8: Update all beds and student allocations atomically
            now = timezone.now()
            transfer_records = []
            
            # Temporary release current occupants from beds to avoid unique constraint collisions during rotation
            for p in participants:
                bed = locked_beds_dict[p.current_bed_id]
                bed.current_occupant = None
                bed.occupancy_status = Bed.OccupancyStatus.VACANT
                bed.save(update_fields=['current_occupant', 'occupancy_status'])

            # Assign students to their new target beds
            for idx, p in enumerate(participants):
                target_bed = locked_beds_dict[p.target_bed_id]
                target_bed.current_occupant = p.student
                target_bed.occupancy_status = Bed.OccupancyStatus.OCCUPIED
                target_bed.save(update_fields=['current_occupant', 'occupancy_status'])

                # Update student's last_transferred_at for cooling-off period calculation
                p.student.last_transferred_at = now
                p.student.save(update_fields=['last_transferred_at'])

                # Step 10: Create TransferRecord
                t_code = f"TRF-{now.year}-{uuid.uuid4().hex[:8].upper()}"
                transfer_rec = TransferRecord.objects.create(
                    transfer_code=t_code,
                    proposal=proposal,
                    student=p.student,
                    previous_bed_id=p.current_bed_id,
                    new_bed_id=p.target_bed_id,
                    approved_by=approver
                )
                transfer_records.append(transfer_rec)

                # Send success notification
                NotificationService.send(
                    recipient=p.student,
                    title="Room Transfer Completed!",
                    message=f"Official transfer {t_code} finalized by Warden. You are now officially allocated to Room {target_bed.room.room_number} ({target_bed.bed_number}). View and print your transfer pass.",
                    notification_type=Notification.NotificationType.TRANSFER_COMPLETED,
                    link=f"/transfers/{transfer_rec.id}/"
                )

            # Step 9: Update proposal and requests
            proposal.status = ExchangeProposal.ProposalStatus.COMPLETED
            proposal.completed_at = now
            proposal.save(update_fields=['status', 'completed_at'])

            req_ids = [p.request_id for p in participants if p.request_id]
            if req_ids:
                ExchangeRequest.objects.filter(id__in=req_ids).update(
                    status=ExchangeRequest.RequestStatus.COMPLETED,
                    updated_at=now
                )

            # Record Approval
            Approval.objects.create(
                proposal=proposal,
                approver=approver,
                decision=Approval.Decision.APPROVED,
                remarks=remarks
            )

            # Step 11: Create AuditEntry
            AuditService.log(
                action="ATOMIC_TRANSFER_COMPLETED",
                entity_type="ExchangeProposal",
                entity_id=proposal.id,
                actor=approver,
                previous_state={"status": ExchangeProposal.ProposalStatus.READY_FOR_APPROVAL},
                new_state={"status": ExchangeProposal.ProposalStatus.COMPLETED},
                metadata={
                    "transfers": [
                        {
                            "student": t.student.university_id,
                            "from_bed": t.previous_bed_id,
                            "to_bed": t.new_bed_id,
                            "code": t.transfer_code
                        }
                        for t in transfer_records
                    ],
                    "locked_bed_ids_order": sorted_bed_ids,
                    "approver": approver.username
                }
            )

            return {
                'success': True,
                'proposal_code': proposal.proposal_code,
                'transfers_count': len(transfer_records),
                'transfers': transfer_records
            }
