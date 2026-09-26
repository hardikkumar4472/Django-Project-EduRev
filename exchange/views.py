import io
import base64
import qrcode
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.views.decorators.http import require_POST
from hostel.models import Hostel, Room, Bed
from hostel.services import occupancy_service
from exchange.models import (
    PolicyRule,
    ExchangeRequest,
    ExchangeProposal,
    ProposalParticipant,
    Approval,
    TransferRecord,
    AuditEntry
)
from .services.eligibility_service import EligibilityService
from .services.matching_service import MatchingService
from .services.proposal_service import ProposalService
from .services.occupancy_service import AtomicOccupancyEngine, OccupancyTransferError
from .services.audit_service import AuditService

User = get_user_model()

def landing_page(request):
    """
    Phase 20: Official University Landing Page.
    """
    total_students = User.objects.filter(role=User.Role.STUDENT).count()
    total_hostels = Hostel.objects.filter(is_active=True).count()
    completed_transfers = TransferRecord.objects.count()
    active_requests = ExchangeRequest.objects.filter(status=ExchangeRequest.RequestStatus.ACTIVE).count()

    return render(request, 'landing.html', {
        'total_students': total_students,
        'total_hostels': total_hostels,
        'completed_transfers': completed_transfers,
        'active_requests': active_requests
    })

def student_dashboard(request):
    """
    Student Cockpit: 2D Room visualizer, current bed, active proposal, countdown.
    """
    user = request.user
    if user.is_admin_role and not user.is_student:
        return redirect('/admin/policies/')
    if (user.is_chief_warden or user.is_warden) and not user.is_student:
        return redirect('/warden/approvals/')
    if user.is_dsw and not user.is_student:
        return redirect('/dean/analytics/')

    # Current bed and room
    current_bed = getattr(user, 'allocated_bed', None)
    room_matrix = None
    if current_bed:
        room_matrix = occupancy_service.get_room_visual_matrix(current_bed.room_id)

    # Active exchange request
    active_request = ExchangeRequest.objects.filter(
        requester=user,
        status__in=[
            ExchangeRequest.RequestStatus.ACTIVE,
            ExchangeRequest.RequestStatus.MATCHED,
            ExchangeRequest.RequestStatus.PROPOSED
        ]
    ).first()

    # Active proposals involving this student
    active_proposals = ExchangeProposal.objects.filter(
        participants__student=user,
        status__in=[
            ExchangeProposal.ProposalStatus.PENDING_ACCEPTANCE,
            ExchangeProposal.ProposalStatus.PARTIALLY_ACCEPTED,
            ExchangeProposal.ProposalStatus.READY_FOR_APPROVAL
        ]
    ).distinct()

    # Completed transfers
    transfers = TransferRecord.objects.filter(student=user).select_related(
        'previous_bed__room__block__hostel',
        'new_bed__room__block__hostel',
        'approved_by'
    )[:5]

    # Vacant beds for unallocated students
    vacant_beds = []
    if not current_bed:
        gender = getattr(user, 'gender', 'M')
        target_gender = 'FEMALE' if gender == 'F' else 'MALE'
        vacant_beds = Bed.objects.filter(
            occupancy_status=Bed.OccupancyStatus.VACANT,
            room__block__hostel__gender_type=target_gender
        ).select_related('room__block__hostel')[:50]

    # Eligibility quick check
    eligibility = EligibilityService.validate_student_eligibility(user)

    return render(request, 'exchange/student_dashboard.html', {
        'current_bed': current_bed,
        'room_matrix': room_matrix,
        'active_request': active_request,
        'active_proposals': active_proposals,
        'transfers': transfers,
        'eligibility': eligibility,
        'vacant_beds': vacant_beds,
    })


def create_request_view(request):
    """
    Submit exchange request with real-time policy verification.
    If student is currently allocated in a specific room type (e.g. 2-seater),
    only identical room types are eligible and displayed.
    """
    user = request.user
    eligibility = EligibilityService.validate_student_eligibility(user)

    current_bed = getattr(user, 'allocated_bed', None)
    current_room = current_bed.room if current_bed else None
    current_room_type = current_room.room_type if current_room else None

    if request.method == 'POST':
        if not eligibility['eligible']:
            failed_reasons = [c['reason'] for c in eligibility.get('checks', []) if not c.get('passed', True)]
            error_details = " ".join(failed_reasons) if failed_reasons else "Eligibility policy validation failed."
            messages.error(request, f"Cannot submit exchange request: {error_details}")
            return redirect('/exchange-requests/new/')

        hostel_id = request.POST.get('preferred_hostel')
        # If user has an allocated bed/room, enforce preferred_room_type to match their current room type
        if current_room_type:
            room_type = current_room_type
        else:
            room_type = request.POST.get('preferred_room_type', '')

        floor = request.POST.get('preferred_floor')
        specific_room_id = request.POST.get('specific_target_room')
        reason = request.POST.get('reason', '')

        req = ExchangeRequest.objects.create(
            requester=user,
            current_bed=user.allocated_bed,
            preferred_hostel_id=hostel_id if hostel_id else None,
            preferred_room_type=room_type,
            preferred_floor=int(floor) if floor else None,
            specific_target_room_id=specific_room_id if specific_room_id else None,
            reason=reason,
            status=ExchangeRequest.RequestStatus.ACTIVE
        )

        AuditService.log(
            action="REQUEST_CREATED",
            entity_type="ExchangeRequest",
            entity_id=req.id,
            actor=user,
            new_state={"status": req.status, "hostel_id": hostel_id, "room_type": room_type}
        )

        messages.success(request, "Exchange request successfully activated! The graph matching engine is actively evaluating cycles.")
        return redirect('/matches/')

    # Active request if one already exists
    active_request = ExchangeRequest.objects.filter(
        requester=user,
        status__in=[
            ExchangeRequest.RequestStatus.ACTIVE,
            ExchangeRequest.RequestStatus.MATCHED,
            ExchangeRequest.RequestStatus.PROPOSED
        ]
    ).first()

    hostels = Hostel.objects.filter(is_active=True)
    if hasattr(user, 'gender') and user.gender:
        gender_target = 'FEMALE' if user.gender == 'F' else 'MALE'
        hostels = hostels.filter(gender_type=gender_target)

    # If student is staying in a specific room type (e.g. 2-seater), show ONLY that room type
    if current_room_type:
        room_types = [(current_room_type, current_room.get_room_type_display())]
    else:
        room_types = Room.RoomType.choices

    rooms = Room.objects.filter(is_active=True).select_related('block__hostel')
    if current_room_type:
        rooms = rooms.filter(room_type=current_room_type)
    if hasattr(user, 'gender') and user.gender:
        gender_target = 'FEMALE' if user.gender == 'F' else 'MALE'
        rooms = rooms.filter(block__hostel__gender_type=gender_target)
    rooms = rooms[:100]

    return render(request, 'exchange/create_request.html', {
        'eligibility': eligibility,
        'active_request': active_request,
        'hostels': hostels,
        'rooms': rooms,
        'room_types': room_types,
        'current_room': current_room,
        'current_room_type': current_room_type,
    })

@require_POST
def withdraw_request_view(request, pk):
    """
    Allow a student to withdraw their active exchange request.
    """
    user = request.user
    req = get_object_or_404(ExchangeRequest, id=pk, requester=user)
    if req.status in [ExchangeRequest.RequestStatus.ACTIVE, ExchangeRequest.RequestStatus.MATCHED]:
        req.status = ExchangeRequest.RequestStatus.WITHDRAWN
        req.save()
        AuditService.log(
            action="REQUEST_WITHDRAWN",
            entity_type="ExchangeRequest",
            entity_id=req.id,
            actor=user,
            new_state={"status": req.status}
        )
        messages.success(request, f"Exchange request #{req.id} has been withdrawn successfully. You can now submit a new request.")
    else:
        messages.error(request, f"Request #{req.id} cannot be withdrawn in its current state ({req.get_status_display()}).")

    next_url = request.POST.get('next', '/dashboard/')
    return redirect(next_url)

def cycle_explorer_view(request):
    """
    Graph Cycle Explorer: Matches discovery & animated directional swap graph.
    """
    user = request.user
    target_id = user.id if user.is_student else None
    discovered_cycles = MatchingService.find_cycles(target_student_id=target_id)

    return render(request, 'exchange/cycle_explorer.html', {
        'cycles': discovered_cycles,
        'total_matches': len(discovered_cycles)
    })

@require_POST
def initiate_proposal_view(request):
    """
    Converts a discovered match cycle into an active ExchangeProposal.
    """
    user = request.user
    cycle_index = int(request.POST.get('cycle_index', 0))
    target_id = user.id if user.is_student else None
    discovered_cycles = MatchingService.find_cycles(target_student_id=target_id)

    if 0 <= cycle_index < len(discovered_cycles):
        match_data = discovered_cycles[cycle_index]
        proposal = ProposalService.create_proposal_from_match(match_data, creator=user)
        messages.success(request, f"Proposal {proposal.proposal_code} successfully initiated! Notifications dispatched to all participants.")
        return redirect(f"/proposals/{proposal.id}/")
    else:
        messages.error(request, "Invalid cycle selection. Please refresh and try again.")
        return redirect('/matches/')

def proposal_detail_view(request, pk):
    """
    Detailed proposal screen with participant voting table and live countdown.
    """
    proposal = get_object_or_404(ExchangeProposal, id=pk)
    participants = proposal.participants.select_related(
        'student',
        'current_bed__room__block__hostel',
        'target_bed__room__block__hostel'
    ).all()

    current_student_participant = participants.filter(student=request.user).first()
    has_voted = current_student_participant and current_student_participant.response != ProposalParticipant.ParticipantResponse.PENDING

    return render(request, 'exchange/proposal_detail.html', {
        'proposal': proposal,
        'participants': participants,
        'current_student_participant': current_student_participant,
        'has_voted': has_voted,
        'is_expired': timezone.now() > proposal.expires_at
    })

@require_POST
def respond_proposal_view(request, pk):
    proposal = get_object_or_404(ExchangeProposal, id=pk)
    decision = request.POST.get('decision', '').upper()
    result = ProposalService.respond_to_proposal(proposal, request.user, decision)

    if result.get('success'):
        messages.success(request, result.get('message'))
    else:
        messages.error(request, result.get('error', 'Error recording response.'))

    return redirect(f"/proposals/{proposal.id}/")

def warden_dashboard_view(request):
    """
    Warden Approval Queue:
    - Chief Warden & Admin: Oversee and approve requests across all 20 hostels.
    - Specific Hostel Warden: Only view and approve requests involving their assigned hostel.
    """
    user = request.user
    is_chief_or_admin = (user.is_chief_warden or user.is_admin_role)
    managed_hostels = user.managed_hostels.all()

    if is_chief_or_admin:
        pending_proposals = ExchangeProposal.objects.filter(
            status=ExchangeProposal.ProposalStatus.READY_FOR_APPROVAL
        )
        recent_approvals = Approval.objects.select_related('proposal', 'approver').order_by('-created_at')[:15]
    else:
        # Filter proposals that involve students from or moving into this warden's hostel
        pending_proposals = ExchangeProposal.objects.filter(
            status=ExchangeProposal.ProposalStatus.READY_FOR_APPROVAL
        ).filter(
            Q(participants__current_bed__room__block__hostel__in=managed_hostels) |
            Q(participants__target_bed__room__block__hostel__in=managed_hostels)
        ).distinct()

        recent_approvals = Approval.objects.filter(
            Q(proposal__participants__current_bed__room__block__hostel__in=managed_hostels) |
            Q(proposal__participants__target_bed__room__block__hostel__in=managed_hostels) |
            Q(approver=user)
        ).select_related('proposal', 'approver').distinct().order_by('-created_at')[:15]

    pending_proposals = pending_proposals.prefetch_related(
        'participants__student',
        'participants__current_bed__room__block__hostel',
        'participants__target_bed__room__block__hostel'
    )

    return render(request, 'exchange/warden_dashboard.html', {
        'pending_proposals': pending_proposals,
        'recent_approvals': recent_approvals,
        'managed_hostels': managed_hostels,
        'is_chief_or_admin': is_chief_or_admin,
    })

def warden_review_view(request, pk):
    """
    Warden Review single proposal before atomic commitment.
    Enforces that regular wardens can ONLY review/approve transfers for their assigned hostel,
    while Chief Warden and Admin can manage all hostels.
    """
    proposal = get_object_or_404(ExchangeProposal, id=pk)
    user = request.user
    is_chief_or_admin = (user.is_chief_warden or user.is_admin_role)
    managed_hostels = user.managed_hostels.all()

    if not is_chief_or_admin:
        proposal_hostel_ids = set(
            proposal.participants.values_list('current_bed__room__block__hostel_id', flat=True)
        ).union(
            set(proposal.participants.values_list('target_bed__room__block__hostel_id', flat=True))
        )
        if not managed_hostels.filter(id__in=proposal_hostel_ids).exists():
            assigned_names = ", ".join([h.name for h in managed_hostels]) or "No assigned hostel"
            messages.error(
                request,
                f"Access Denied: You are only authorized to review and approve transfers for your assigned hostel ({assigned_names})."
            )
            return redirect('/warden/approvals/')

    participants = proposal.participants.select_related(
        'student',
        'current_bed__room__block__hostel',
        'target_bed__room__block__hostel'
    ).all()

    if request.method == 'POST':
        action = request.POST.get('action')
        remarks = request.POST.get('remarks', 'Warden review finalized.')

        if action == 'APPROVE':
            try:
                res = AtomicOccupancyEngine.execute_proposal_atomic(proposal.id, request.user, remarks=remarks)
                messages.success(
                    request,
                    f"SUCCESS: Atomic transaction executed cleanly! {res['transfers_count']} room allocations updated with 0 partial transfers."
                )
                return redirect('/warden/approvals/')
            except OccupancyTransferError as exc:
                messages.error(request, f"Atomic Transfer Aborted & Rolled Back: {str(exc)}")
        elif action == 'REJECT':
            proposal.status = ExchangeProposal.ProposalStatus.DECLINED
            proposal.save()
            Approval.objects.create(
                proposal=proposal,
                approver=request.user,
                decision=Approval.Decision.REJECTED,
                remarks=remarks
            )
            AuditService.log(
                action="PROPOSAL_REJECTED_BY_WARDEN",
                entity_type="ExchangeProposal",
                entity_id=proposal.id,
                actor=request.user,
                metadata={"remarks": remarks}
            )
            messages.info(request, f"Proposal {proposal.proposal_code} has been rejected.")
            return redirect('/warden/approvals/')

    return render(request, 'exchange/warden_review.html', {
        'proposal': proposal,
        'participants': participants
    })

def transfer_letter_view(request, pk):
    """
    Phase 15: Official Printable Transfer Certificate with Base64 QR Code.
    """
    transfer = get_object_or_404(
        TransferRecord.objects.select_related(
            'student',
            'previous_bed__room__block__hostel',
            'new_bed__room__block__hostel',
            'approved_by',
            'proposal'
        ),
        id=pk
    )

    # Generate QR code for verification
    qr_data = f"EDUREV-SWAP-VERIFIED|ID:{transfer.transfer_code}|STUDENT:{transfer.student.university_id}|BED:{transfer.new_bed_id}|TOKEN:{transfer.verification_token}"
    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#172A46", back_color="#FFFFFF")
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return render(request, 'exchange/transfer_letter.html', {
        'transfer': transfer,
        'qr_base64': qr_base64
    })

def transfers_list_view(request):
    """
    List transfers: personal for students, university-wide for wardens/admins.
    """
    user = request.user
    if user.is_warden or user.is_admin_role or user.is_dsw:
        transfers = TransferRecord.objects.all().select_related(
            'student',
            'previous_bed__room__block__hostel',
            'new_bed__room__block__hostel',
            'approved_by'
        )[:50]
    else:
        transfers = TransferRecord.objects.filter(student=user).select_related(
            'student',
            'previous_bed__room__block__hostel',
            'new_bed__room__block__hostel',
            'approved_by'
        )

    return render(request, 'exchange/transfers_list.html', {'transfers': transfers})

def admin_policies_view(request):
    """
    Phase 17: Administrative Policy Configuration.
    """
    if request.method == 'POST':
        for rule_type, _ in PolicyRule.RuleType.choices:
            int_val = request.POST.get(f"int_{rule_type}")
            bool_val = request.POST.get(f"bool_{rule_type}") == 'on'
            rule, _ = PolicyRule.objects.get_or_create(rule_type=rule_type)
            if int_val is not None:
                try:
                    rule.int_value = int(int_val)
                except ValueError:
                    pass
            rule.bool_value = bool_val
            rule.updated_by = request.user
            rule.save()

        messages.success(request, "University exchange policy parameters updated successfully.")
        return redirect('/admin/policies/')

    # Default rules ensure all exist
    default_rules = [
        (PolicyRule.RuleType.COOLING_OFF_DAYS, 30, True, "Days student must wait after a completed transfer before applying again"),
        (PolicyRule.RuleType.MAX_CHAIN_LENGTH, 5, True, "Maximum multi-party cycle length (2 to 5) evaluated by the graph matching engine"),
        (PolicyRule.RuleType.PROPOSAL_VALIDITY_HOURS, 48, True, "Hours allowed for all participants to accept a proposal before automatic expiration"),
        (PolicyRule.RuleType.FEE_CLEARANCE_REQUIRED, 0, True, "Require zero hostel fee balance before allowing request submission"),
        (PolicyRule.RuleType.DISCIPLINARY_CHECK, 0, True, "Block students with active disciplinary holds from participating in room transfers"),
        (PolicyRule.RuleType.GENDER_STRICT_SEPARATION, 0, True, "Enforce strict hostel block gender residency regulations"),
    ]
    for r_type, d_int, d_bool, desc in default_rules:
        PolicyRule.objects.get_or_create(
            rule_type=r_type,
            defaults={'int_value': d_int, 'bool_value': d_bool, 'description': desc}
        )

    policies = PolicyRule.objects.all().order_by('rule_type')
    return render(request, 'exchange/admin_policies.html', {'policies': policies})

def analytics_dashboard_view(request):
    """
    Phase 17: Dean of Student Welfare (DSW) & Admin Analytics & Audit Trail.
    """
    total_requests = ExchangeRequest.objects.count()
    active_requests = ExchangeRequest.objects.filter(status=ExchangeRequest.RequestStatus.ACTIVE).count()
    completed_transfers = TransferRecord.objects.count()
    proposals_count = ExchangeProposal.objects.count()
    
    # Cycles distribution
    direct_swaps = ExchangeProposal.objects.filter(proposal_type=ExchangeProposal.ProposalType.DIRECT).count()
    multi_cycles = proposals_count - direct_swaps

    # Audit logs
    audit_entries = AuditEntry.objects.select_related('actor').order_by('-timestamp')[:50]

    return render(request, 'exchange/analytics_dashboard.html', {
        'total_requests': total_requests,
        'active_requests': active_requests,
        'completed_transfers': completed_transfers,
        'proposals_count': proposals_count,
        'direct_swaps': direct_swaps,
        'multi_cycles': multi_cycles,
        'audit_entries': audit_entries
    })

def concurrency_demo_view(request):
    """
    Phase 18 & 20E: Dedicated Concurrency Demonstration Page.
    Visualizes two racing transactions competing for overlapping beds and demonstrates
    the primary-key ordering row locking safety mechanism.
    """
    beds = Bed.objects.select_related('room__block__hostel', 'current_occupant')[:8]
    return render(request, 'exchange/concurrency_demo.html', {'beds': beds})

def room_detail_view(request, pk=None):
    """
    Screen 6: Room Detail & Architectural Cutaway Floorplan View.
    """
    if pk:
        room = get_object_or_404(Room.objects.select_related('block__hostel').prefetch_related('beds__current_occupant'), id=pk)
    else:
        room = Room.objects.select_related('block__hostel').prefetch_related('beds__current_occupant').first()
    
    beds = room.beds.all() if room else []
    return render(request, 'exchange/room_detail.html', {
        'room': room,
        'beds': beds
    })