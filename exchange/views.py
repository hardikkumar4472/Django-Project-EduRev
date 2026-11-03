import io
import base64
import qrcode
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
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
        # Server-side Gender Residency Enforcement
        if hostel_id and hasattr(user, 'gender') and user.gender:
            target_h = Hostel.objects.filter(id=hostel_id).first()
            if target_h:
                if (user.gender == User.Gender.MALE and target_h.gender_type == 'FEMALE') or \
                   (user.gender == User.Gender.FEMALE and target_h.gender_type == 'MALE'):
                    messages.error(request, "Cross-gender hostel applications are strictly prohibited by campus residency policy.")
                    return redirect('/exchange-requests/new/')

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

    rooms = Room.objects.filter(is_active=True).select_related('block__hostel').prefetch_related('beds__current_occupant')
    if current_room_type:
        rooms = rooms.filter(room_type=current_room_type)
    if hasattr(user, 'gender') and user.gender:
        gender_target = 'FEMALE' if user.gender == 'F' else 'MALE'
        rooms = rooms.filter(block__hostel__gender_type=gender_target)
    rooms = rooms[:40]

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
    Graph Cycle Explorer: Matches discovery & active proposals.
    Strictly filters cycles based on user's gender (Male students see only Boys Hostels,
    Female students see only Girls Hostels).
    """
    user = request.user
    target_id = user.id if user.is_authenticated and user.is_student else None
    user_gender = getattr(user, 'gender', None) if user.is_authenticated else None
    
    # 1. Fetch user-involved cycles if authenticated student
    student_cycles = MatchingService.find_cycles(target_student_id=target_id) if target_id else []
    
    # 2. Fetch all system-wide graph rotation cycles
    all_campus_cycles = MatchingService.find_cycles()
    
    # Filter cycles by gender policy
    from hostel.models import Bed
    def matches_user_gender(cycle_item):
        if not user_gender or not user.is_student:
            return True
        participants = cycle_item.get('participants', [])
        if not participants:
            return True
        b_id = participants[0].get('current_bed_id')
        if b_id:
            bed = Bed.objects.select_related('room__block__hostel').filter(id=b_id).first()
            if bed:
                h_gender = bed.room.block.hostel.gender_type
                if user_gender == 'M' and h_gender == 'FEMALE':
                    return False
                if user_gender == 'F' and h_gender == 'MALE':
                    return False
        return True

    student_cycles = [c for c in student_cycles if matches_user_gender(c)]
    all_campus_cycles = [c for c in all_campus_cycles if matches_user_gender(c)]

    # Prioritize user's own cycles first, followed by other active campus cycle opportunities
    seen_cycle_keys = set()
    discovered_cycles = []
    
    for c in student_cycles:
        key = tuple(c.get('node_ids', []))
        if key not in seen_cycle_keys:
            seen_cycle_keys.add(key)
            c['is_direct_match'] = True
            discovered_cycles.append(c)
            
    for c in all_campus_cycles:
        key = tuple(c.get('node_ids', []))
        if key not in seen_cycle_keys:
            seen_cycle_keys.add(key)
            c['is_direct_match'] = False
            discovered_cycles.append(c)

    # Active proposals involving this student
    active_proposals = []
    if user.is_authenticated and user.is_student:
        active_proposals = list(ExchangeProposal.objects.filter(
            participants__student=user,
            status__in=[
                ExchangeProposal.ProposalStatus.PENDING_ACCEPTANCE,
                ExchangeProposal.ProposalStatus.PARTIALLY_ACCEPTED,
                ExchangeProposal.ProposalStatus.READY_FOR_APPROVAL
            ]
        ).prefetch_related('participants__student', 'participants__current_bed__room__block__hostel', 'participants__target_bed__room__block__hostel').distinct())

    # Hostels matching user's gender for filter dropdown
    filter_hostels = Hostel.objects.filter(is_active=True)
    if user_gender and user.is_student:
        target_g = 'FEMALE' if user_gender == 'F' else 'MALE'
        filter_hostels = filter_hostels.filter(gender_type=target_g)

    total_count = len(discovered_cycles)
    display_cycles = discovered_cycles[:60]

    return render(request, 'exchange/cycle_explorer.html', {
        'cycles': display_cycles,
        'total_matches': total_count,
        'active_proposals': active_proposals,
        'filter_hostels': filter_hostels,
    })


@require_POST
def initiate_proposal_view(request):
    """
    Converts a discovered match cycle into an active ExchangeProposal.
    """
    user = request.user
    cycle_index = int(request.POST.get('cycle_index', 0))
    target_id = user.id if user.is_authenticated and user.is_student else None
    user_gender = getattr(user, 'gender', None) if user.is_authenticated else None
    
    student_cycles = MatchingService.find_cycles(target_student_id=target_id) if target_id else []
    all_campus_cycles = MatchingService.find_cycles()
    
    from hostel.models import Bed
    def matches_user_gender(cycle_item):
        if not user_gender or not user.is_student:
            return True
        participants = cycle_item.get('participants', [])
        if not participants:
            return True
        b_id = participants[0].get('current_bed_id')
        if b_id:
            bed = Bed.objects.select_related('room__block__hostel').filter(id=b_id).first()
            if bed:
                h_gender = bed.room.block.hostel.gender_type
                if user_gender == 'M' and h_gender == 'FEMALE':
                    return False
                if user_gender == 'F' and h_gender == 'MALE':
                    return False
        return True

    student_cycles = [c for c in student_cycles if matches_user_gender(c)]
    all_campus_cycles = [c for c in all_campus_cycles if matches_user_gender(c)]

    seen_cycle_keys = set()
    discovered_cycles = []
    for c in student_cycles:
        key = tuple(c.get('node_ids', []))
        if key not in seen_cycle_keys:
            seen_cycle_keys.add(key)
            discovered_cycles.append(c)
    for c in all_campus_cycles:
        key = tuple(c.get('node_ids', []))
        if key not in seen_cycle_keys:
            seen_cycle_keys.add(key)
            discovered_cycles.append(c)

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
        # Chief warden sees proposals ready for final execution:
        # If single hostel: can approve directly.
        # If cross-hostel: only after all involved hostel wardens have given their consent!
        all_ready = ExchangeProposal.objects.filter(
            status=ExchangeProposal.ProposalStatus.READY_FOR_APPROVAL
        )
        pending_proposals = all_ready
        recent_approvals = Approval.objects.select_related('proposal', 'approver').order_by('-created_at')[:15]
    else:
        # Hostel warden sees proposals where their hostel is involved
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
        'participants__target_bed__room__block__hostel',
        'approvals__approver'
    )

    return render(request, 'exchange/warden_dashboard.html', {
        'pending_proposals': pending_proposals,
        'recent_approvals': recent_approvals,
        'managed_hostels': managed_hostels,
        'is_chief_or_admin': is_chief_or_admin,
    })

def warden_review_view(request, pk):
    """
    Warden Review:
    - If cross-hostel: Each involved hostel's warden reviews and grants 'WARDEN_CONSENT'.
    - Once all involved hostel wardens have approved, Chief Warden / Admin executes final atomic transfer.
    - If single hostel: The hostel's warden or Chief Warden can execute transfer directly.
    """
    proposal = get_object_or_404(ExchangeProposal, id=pk)
    user = request.user
    is_chief_or_admin = (user.is_chief_warden or user.is_admin_role)
    managed_hostels = user.managed_hostels.all()

    # Determine all involved hostels
    involved_hostels = proposal.involved_hostels
    warden_status_list = proposal.get_warden_approval_status()
    all_wardens_approved = proposal.all_hostel_wardens_approved
    is_cross_hostel = proposal.is_cross_hostel

    # Permission check for regular hostel warden
    user_managed_involved = [h for h in involved_hostels if h in managed_hostels]
    user_has_approved = proposal.approvals.filter(approver=user, decision=Approval.Decision.APPROVED).exists()

    if not is_chief_or_admin and not user_managed_involved:
        assigned_names = ", ".join([h.name for h in managed_hostels]) or "No assigned hostel"
        messages.error(
            request,
            f"Access Denied: You are only authorized to review proposals involving your assigned hostel ({assigned_names})."
        )
        return redirect('/warden/approvals/')

    participants = proposal.participants.select_related(
        'student',
        'current_bed__room__block__hostel',
        'target_bed__room__block__hostel'
    ).all()

    if request.method == 'POST':
        action = request.POST.get('action')
        remarks = request.POST.get('remarks', 'Warden review finalized.').strip()

        if action == 'WARDEN_APPROVE':
            # Hostel warden records approval for their hostel
            Approval.objects.create(
                proposal=proposal,
                approver=user,
                decision=Approval.Decision.APPROVED,
                remarks=remarks or f"Consent granted by {user.get_full_name()}."
            )
            AuditService.log(
                action="PROPOSAL_APPROVED_BY_HOSTEL_WARDEN",
                entity_type="ExchangeProposal",
                entity_id=proposal.id,
                actor=user,
                metadata={"remarks": remarks, "warden": user.username}
            )

            # Re-check if all wardens approved
            if proposal.all_hostel_wardens_approved:
                messages.success(
                    request,
                    f"Consent recorded! All involved hostel wardens have now signed off. Proposal is escalated to Chief Warden for final execution."
                )
            else:
                messages.success(
                    request,
                    f"Consent recorded! Waiting for remaining hostel warden(s) to sign off before escalation to Chief Warden."
                )
            return redirect('/warden/approvals/')

        elif action == 'EXECUTE_ATOMIC':
            # Execution check: if cross-hostel, must be chief_warden or admin, and all hostel wardens must have approved (unless admin override)
            if is_cross_hostel and not all_wardens_approved and not user.is_admin_role:
                messages.error(
                    request,
                    "Cannot execute transfer yet: All involved hostel wardens must approve this cross-hostel swap first."
                )
                return redirect(f'/warden/approvals/{proposal.id}/')

            try:
                res = AtomicOccupancyEngine.execute_proposal_atomic(proposal.id, user, remarks=remarks or "Approved and executed.")
                messages.success(
                    request,
                    f"SUCCESS: Atomic room swap transaction executed cleanly! {res['transfers_count']} room allocations updated with 0 partial transfers."
                )
                return redirect('/warden/approvals/')
            except OccupancyTransferError as exc:
                messages.error(request, f"Atomic Transfer Aborted & Rolled Back: {str(exc)}")

        elif action == 'REJECT':
            proposal.status = ExchangeProposal.ProposalStatus.DECLINED
            proposal.save()
            Approval.objects.create(
                proposal=proposal,
                approver=user,
                decision=Approval.Decision.REJECTED,
                remarks=remarks
            )
            AuditService.log(
                action="PROPOSAL_REJECTED_BY_WARDEN",
                entity_type="ExchangeProposal",
                entity_id=proposal.id,
                actor=user,
                metadata={"remarks": remarks}
            )
            messages.info(request, f"Proposal {proposal.proposal_code} has been rejected.")
            return redirect('/warden/approvals/')

    return render(request, 'exchange/warden_review.html', {
        'proposal': proposal,
        'participants': participants,
        'is_cross_hostel': is_cross_hostel,
        'warden_status_list': warden_status_list,
        'all_wardens_approved': all_wardens_approved,
        'user_has_approved': user_has_approved,
        'is_chief_or_admin': is_chief_or_admin,
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

    # Hostel migration and room type metrics for charts
    import json
    hostels_all = list(Hostel.objects.filter(is_active=True).values('id', 'name', 'code'))
    hostel_labels = [h['code'] or h['name'] for h in hostels_all]
    
    # Inbound and outbound demand counts per hostel
    hostel_in_demand = []
    hostel_out_demand = []
    for h in hostels_all:
        in_count = ExchangeRequest.objects.filter(preferred_hostel_id=h['id']).count()
        out_count = ExchangeRequest.objects.filter(current_bed__room__block__hostel_id=h['id']).count()
        hostel_in_demand.append(in_count)
        hostel_out_demand.append(out_count)

    # Room type demand counts
    room_types_labels = ["1-Seater", "2-Seater", "3-Seater", "4-Seater", "7-Seater", "8-Seater"]
    room_type_keys = [
        Room.RoomType.SINGLE,
        Room.RoomType.DOUBLE,
        Room.RoomType.TRIPLE,
        Room.RoomType.FOUR_SHARING,
        Room.RoomType.SEVEN_SEATER,
        Room.RoomType.EIGHT_SEATER
    ]
    room_type_counts = [
        ExchangeRequest.objects.filter(preferred_room_type=k).count() for k in room_type_keys
    ]

    # Audit logs
    audit_entries = AuditEntry.objects.select_related('actor').order_by('-timestamp')[:50]

    return render(request, 'exchange/analytics_dashboard.html', {
        'total_requests': total_requests,
        'active_requests': active_requests,
        'completed_transfers': completed_transfers,
        'proposals_count': proposals_count,
        'direct_swaps': direct_swaps,
        'multi_cycles': multi_cycles,
        'audit_entries': audit_entries,
        'hostel_labels_json': json.dumps(hostel_labels),
        'hostel_in_demand_json': json.dumps(hostel_in_demand),
        'hostel_out_demand_json': json.dumps(hostel_out_demand),
        'room_type_labels_json': json.dumps(room_types_labels),
        'room_type_counts_json': json.dumps(room_type_counts),
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


def caretaker_verify_view(request):
    """
    In-App Caretaker Verification & QR Scanner Screen.
    Allows hostel caretakers, wardens, and admins to scan or input verification tokens
    and officially confirm room key handovers.
    """
    user = request.user
    if not user.is_authenticated:
        return redirect('login')
    
    # Restrict to Staff Roles: Wardens, Chief Warden, Administrators
    if user.is_student and not (user.is_warden or user.is_admin_role or user.is_staff):
        messages.error(request, "Access restricted: The Key Handover & Verification Desk is for authorized Hostel Caretakers and Wardens only.")
        return redirect('dashboard')

    token_input = request.GET.get('token', '').strip()
    scanned_transfer = None
    verification_error = None

    if token_input:
        # Match by token or transfer_code
        scanned_transfer = TransferRecord.objects.filter(
            Q(verification_token__iexact=token_input) |
            Q(transfer_code__iexact=token_input)
        ).select_related(
            'student',
            'previous_bed__room__block__hostel',
            'new_bed__room__block__hostel',
            'approved_by',
            'proposal'
        ).first()

        if not scanned_transfer:
            verification_error = "Invalid or expired transfer pass token. Please check the order reference."

    # If caretaker confirms handover via POST
    if request.method == 'POST':
        transfer_id = request.POST.get('transfer_id')
        caretaker_notes = request.POST.get('notes', 'Keys exchanged and verified by caretaker.')
        tr = get_object_or_404(TransferRecord, id=transfer_id)
        
        AuditService.log(
            action="CARETAKER_KEY_HANDOVER_COMPLETED",
            entity_type="TransferRecord",
            entity_id=tr.id,
            actor=request.user,
            metadata={"notes": caretaker_notes, "token": str(tr.verification_token)}
        )
        messages.success(request, f"✓ Key Handover Confirmed! Resident {tr.student.get_full_name()} possession of Room {tr.new_bed.room.room_number} ({tr.new_bed.bed_number}) officially validated.")
        return redirect(f"/caretaker/verify/?token={tr.transfer_code}")

    recent_verified = TransferRecord.objects.select_related(
        'student',
        'previous_bed__room__block__hostel',
        'new_bed__room__block__hostel'
    ).order_by('-completed_at')[:10]

    return render(request, 'exchange/caretaker_scanner.html', {
        'token_input': token_input,
        'scanned_transfer': scanned_transfer,
        'verification_error': verification_error,
        'recent_verified': recent_verified
    })


def get_proposal_messages_view(request, pk):
    """
    Returns real-time discussion chat messages for a proposal in JSON format.
    Supports ?last_id=<id> for differential low-latency streaming.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"status": "error", "message": "Authentication required"}, status=401)

    proposal = get_object_or_404(ExchangeProposal, id=pk)
    user = request.user

    from .models import ProposalMessage
    messages_qs = proposal.messages.select_related('sender').order_by('id')

    last_id = request.GET.get('last_id')
    if last_id and last_id.isdigit():
        messages_qs = messages_qs.filter(id__gt=int(last_id))

    data = []
    for msg in messages_qs:
        sender_name = msg.sender.get_full_name() or msg.sender.username
        data.append({
            'id': msg.id,
            'sender_id': msg.sender_id,
            'sender_name': sender_name,
            'is_me': (msg.sender_id == user.id),
            'message': msg.message,
            'time': timezone.localtime(msg.created_at).strftime('%H:%M')
        })

    return JsonResponse({
        "status": "success",
        "total_count": proposal.messages.count(),
        "messages": data
    })


@require_POST
def send_proposal_message_view(request, pk):
    """
    Submits a discussion chat message within an active proposal.
    Supports both standard form submission and real-time AJAX / JSON fetch.
    """
    if not request.user.is_authenticated:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
            return JsonResponse({"status": "error", "message": "Authentication required"}, status=401)
        return redirect('/accounts/login/')

    proposal = get_object_or_404(ExchangeProposal, id=pk)
    user = request.user

    is_ajax = (request.headers.get('x-requested-with') == 'XMLHttpRequest' or 
               'application/json' in request.headers.get('Accept', '') or
               'application/json' in getattr(request, 'content_type', ''))

    msg_text = request.POST.get('message', '').strip()
    if not msg_text and 'application/json' in getattr(request, 'content_type', ''):
        try:
            import json
            payload = json.loads(request.body.decode('utf-8'))
            msg_text = payload.get('message', '').strip()
        except Exception:
            msg_text = ''

    if not msg_text:
        if is_ajax:
            return JsonResponse({"status": "error", "message": "Message cannot be empty"}, status=400)
        return redirect(f'/proposals/{proposal.id}/#chat')

    from .models import ProposalMessage
    msg = ProposalMessage.objects.create(
        proposal=proposal,
        sender=user,
        message=msg_text
    )

    if is_ajax:
        sender_name = user.get_full_name() or user.username
        return JsonResponse({
            "status": "success",
            "total_count": proposal.messages.count(),
            "message": {
                "id": msg.id,
                "sender_id": user.id,
                "sender_name": sender_name,
                "is_me": True,
                "message": msg.message,
                "time": timezone.localtime(msg.created_at).strftime('%H:%M')
            }
        })

    return redirect(f'/proposals/{proposal.id}/#chat')


def lifestyle_quiz_view(request):
    """
    Student Roommate Lifestyle Quiz & Compatibility Engine.
    """
    user = request.user
    if not user.is_authenticated:
        return redirect('/login/')

    from .models import StudentLifestyle
    profile, _ = StudentLifestyle.objects.get_or_create(student=user)

    if request.method == 'POST':
        profile.sleep_schedule = request.POST.get('sleep_schedule', profile.sleep_schedule)
        profile.study_habit = request.POST.get('study_habit', profile.study_habit)
        profile.ac_preference = request.POST.get('ac_preference', profile.ac_preference)
        profile.cleanliness = request.POST.get('cleanliness', profile.cleanliness)
        profile.hobbies = request.POST.get('hobbies', profile.hobbies).strip()
        profile.save()

        messages.success(request, "Roommate Lifestyle & Compatibility Profile updated successfully!")
        return redirect('/dashboard/')

    return render(request, 'exchange/lifestyle_quiz.html', {
        'profile': profile,
        'sleep_choices': StudentLifestyle.SleepSchedule.choices,
        'study_choices': StudentLifestyle.StudyHabit.choices,
        'ac_choices': StudentLifestyle.ACPreference.choices,
        'clean_choices': StudentLifestyle.Cleanliness.choices,
    })