from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse
from hostel.models import Hostel, Room
from .models import RMSRequest, RMSComment

@login_required
def rms_dashboard_view(request):
    """
    Main RMS Entrypoint:
    - Students see 'Log Request' tab and 'RMS History' tab with status filter pills.
    - Focuses strictly on Hostel Maintenance & Room Complaints.
    - Staff (Warden / Chief Warden / Dean / Admin) see the Resolution & Escalation Console for their jurisdiction.
    """
    user = request.user
    tab = request.GET.get('tab', 'history' if user.is_student else 'queue')
    status_filter = request.GET.get('status', 'ALL')

    # Student View
    if user.is_student:
        user_bed = getattr(user, 'allocated_bed', None)
        user_room = user_bed.room if user_bed else None
        user_hostel = user_room.block.hostel if user_room else None

        requests_qs = RMSRequest.objects.filter(student=user).select_related('hostel', 'room', 'assigned_to', 'resolved_by')

        if status_filter == 'OPEN':
            requests_qs = requests_qs.filter(status__in=[
                RMSRequest.Status.OPEN,
                RMSRequest.Status.IN_PROGRESS,
                RMSRequest.Status.ESCALATED_DEAN,
                RMSRequest.Status.ESCALATED_CHIEF_WARDEN,
                RMSRequest.Status.ESCALATED_ADMIN
            ])
        elif status_filter == 'CLOSED':
            requests_qs = requests_qs.filter(status__in=[RMSRequest.Status.RESOLVED, RMSRequest.Status.CLOSED])

        total_count = RMSRequest.objects.filter(student=user).count()
        open_count = RMSRequest.objects.filter(
            student=user,
            status__in=[
                RMSRequest.Status.OPEN,
                RMSRequest.Status.IN_PROGRESS,
                RMSRequest.Status.ESCALATED_DEAN,
                RMSRequest.Status.ESCALATED_CHIEF_WARDEN,
                RMSRequest.Status.ESCALATED_ADMIN
            ]
        ).count()
        closed_count = total_count - open_count

        return render(request, 'rms/student_rms.html', {
            'requests': requests_qs,
            'tab': tab,
            'status_filter': status_filter,
            'total_count': total_count,
            'open_count': open_count,
            'closed_count': closed_count,
            'user_bed': user_bed,
            'user_room': user_room,
            'user_hostel': user_hostel,
            'message_types': RMSRequest.MessageType.choices,
            'categories': RMSRequest.Category.choices,
            'sub_categories': RMSRequest.SubCategory.choices,
        })

    # Staff / Administration Console (Warden, Chief Warden, Dean DSW, Admin)
    else:
        is_admin_or_super = user.is_admin_role
        is_dean = user.is_dsw
        is_chief_warden = user.is_chief_warden
        managed_hostels = user.managed_hostels.all()

        queue_qs = RMSRequest.objects.all().select_related('student', 'hostel', 'room', 'assigned_to', 'resolved_by', 'escalated_by')

        # Jurisdictional Routing:
        # Regular hostel warden sees only their managed hostel's requests (or tickets assigned to them)
        if not (is_admin_or_super or is_dean or is_chief_warden):
            queue_qs = queue_qs.filter(
                Q(hostel__in=managed_hostels) | Q(assigned_to=user)
            )

        # Higher Authorities (Dean, Chief Warden, Admin) see escalated tickets + general campus tickets
        jurisdiction_label = "Campus-wide Jurisdiction"
        if is_chief_warden:
            jurisdiction_label = "Chief Warden Escalation Desk"
        elif is_dean:
            jurisdiction_label = "Dean of Student Welfare (DSW) Grievance Desk"
        elif is_admin_or_super:
            jurisdiction_label = "System Administrator Master Console"
        else:
            hostel_names = ", ".join([h.name for h in managed_hostels]) or "Assigned Hostel"
            jurisdiction_label = f"Warden Care Desk ({hostel_names})"

        # Status filtering
        if status_filter == 'OPEN':
            queue_qs = queue_qs.filter(status=RMSRequest.Status.OPEN)
        elif status_filter == 'IN_PROGRESS':
            queue_qs = queue_qs.filter(status=RMSRequest.Status.IN_PROGRESS)
        elif status_filter == 'ESCALATED':
            queue_qs = queue_qs.filter(status__in=[
                RMSRequest.Status.ESCALATED_DEAN,
                RMSRequest.Status.ESCALATED_CHIEF_WARDEN,
                RMSRequest.Status.ESCALATED_ADMIN
            ])
        elif status_filter == 'RESOLVED':
            queue_qs = queue_qs.filter(status__in=[RMSRequest.Status.RESOLVED, RMSRequest.Status.CLOSED])

        total_queue = queue_qs.count()
        escalated_count = RMSRequest.objects.filter(status__in=[
            RMSRequest.Status.ESCALATED_DEAN,
            RMSRequest.Status.ESCALATED_CHIEF_WARDEN,
            RMSRequest.Status.ESCALATED_ADMIN
        ]).count()
        unresolved_count = queue_qs.exclude(status__in=[RMSRequest.Status.RESOLVED, RMSRequest.Status.CLOSED]).count()

        return render(request, 'rms/staff_rms.html', {
            'requests': queue_qs,
            'status_filter': status_filter,
            'jurisdiction_label': jurisdiction_label,
            'total_queue': total_queue,
            'escalated_count': escalated_count,
            'unresolved_count': unresolved_count,
            'is_chief_warden': is_chief_warden,
            'is_dean': is_dean,
            'is_admin_or_super': is_admin_or_super,
        })


@login_required
@require_POST
def create_rms_request_view(request):
    """
    Submits a new RMS ticket raised by a student.
    Automatically tags the student's allocated hostel and room for targeted routing to the hostel warden.
    """
    user = request.user
    if not user.is_student:
        messages.error(request, "Only registered students can log an RMS request.")
        return redirect('/rms/')

    user_bed = getattr(user, 'allocated_bed', None)
    user_room = user_bed.room if user_bed else None
    user_hostel = user_room.block.hostel if user_room else None

    # Fallback to chosen hostel if student has no allocated bed yet
    hostel_id = request.POST.get('hostel_id')
    if not user_hostel and hostel_id:
        user_hostel = Hostel.objects.filter(id=hostel_id).first()

    message_type = request.POST.get('message_type', RMSRequest.MessageType.MAINTENANCE_REQUEST)
    category = request.POST.get('category', RMSRequest.Category.ELECTRICAL)
    sub_category = request.POST.get('sub_category', RMSRequest.SubCategory.AIR_CONDITIONER)

    subject = request.POST.get('subject', '').strip()
    description = request.POST.get('description', '').strip()
    contact_phone = request.POST.get('contact_phone', user.phone or '').strip()
    availability_date = request.POST.get('availability_date') or None
    time_slot = request.POST.get('time_slot', '').strip()

    if not subject or not description:
        messages.error(request, "Please provide a subject and detailed description of the maintenance issue.")
        return redirect('/rms/?tab=form')

    # Find warden assigned to this hostel
    assigned_warden = user_hostel.warden if user_hostel else None

    ticket = RMSRequest.objects.create(
        student=user,
        hostel=user_hostel,
        room=user_room,
        room_number_str=user_room.full_name if user_room else "Not Assigned",
        contact_phone=contact_phone,
        message_type=message_type,
        category=category,
        sub_category=sub_category,
        subject=subject,
        description=description,
        availability_date=availability_date,
        time_slot=time_slot,
        status=RMSRequest.Status.OPEN,
        assigned_to=assigned_warden
    )

    # Add initial creation tracking log
    RMSComment.objects.create(
        ticket=ticket,
        author=user,
        comment=f"Hostel maintenance complaint registered: {subject}",
        action_taken="TICKET_CREATED"
    )

    warden_name = assigned_warden.get_full_name() if assigned_warden else "Hostel Warden Office"
    messages.success(request, f"Maintenance Request {ticket.ticket_code} successfully registered! Assigned to {warden_name}.")
    return redirect(f"/rms/tickets/{ticket.id}/")


@login_required
def rms_ticket_detail_view(request, pk):
    """
    Detailed screen of the RMS request showing:
    - Query description, metadata, time slot
    - Live tracking timeline of notes and remarks
    - Action controls for Warden / Dean / Chief Warden / Admin (Resolve, Escalate, Assign, Add Remark)
    """
    ticket = get_object_or_404(
        RMSRequest.objects.select_related('student', 'hostel', 'room', 'assigned_to', 'resolved_by', 'escalated_by'),
        id=pk
    )
    user = request.user

    # Security check: Students can only view their own requests
    if user.is_student and ticket.student != user:
        messages.error(request, "Access Denied: You cannot view this student's RMS ticket.")
        return redirect('/rms/')

    comments = ticket.comments.select_related('author').order_by('created_at')

    # Check authority permissions
    can_resolve = (
        not user.is_student and (
            user.is_admin_role or
            user.is_dsw or
            user.is_chief_warden or
            (user.is_warden and (ticket.hostel in user.managed_hostels.all() or ticket.assigned_to == user))
        )
    )

    can_escalate = (
        not user.is_student and
        user.is_warden and
        not (ticket.status in [RMSRequest.Status.RESOLVED, RMSRequest.Status.CLOSED])
    )

    return render(request, 'rms/ticket_detail.html', {
        'ticket': ticket,
        'comments': comments,
        'can_resolve': can_resolve,
        'can_escalate': can_escalate,
        'is_student': user.is_student,
    })


@login_required
@require_POST
def escalate_rms_request_view(request, pk):
    """
    If the issue cannot be resolved by the hostel warden:
    Warden escalates to Dean (DSW), Chief Warden, or System Administrator.
    """
    ticket = get_object_or_404(RMSRequest, id=pk)
    user = request.user

    if user.is_student:
        messages.error(request, "Students cannot trigger staff escalation.")
        return redirect(f"/rms/tickets/{pk}/")

    target_authority = request.POST.get('target_authority', 'DEAN') # DEAN, CHIEF_WARDEN, ADMIN
    reason = request.POST.get('escalation_reason', '').strip()

    if not reason:
        messages.error(request, "Please enter an explanation of why the query cannot be resolved at the hostel level.")
        return redirect(f"/rms/tickets/{pk}/")

    if target_authority == 'CHIEF_WARDEN':
        ticket.status = RMSRequest.Status.ESCALATED_CHIEF_WARDEN
        target_name = "Chief Warden Central Office"
    elif target_authority == 'ADMIN':
        ticket.status = RMSRequest.Status.ESCALATED_ADMIN
        target_name = "System Administrator"
    else:
        ticket.status = RMSRequest.Status.ESCALATED_DEAN
        target_name = "Dean of Student Welfare (DSW)"

    ticket.escalated_from_warden = True
    ticket.escalation_reason = reason
    ticket.escalated_at = timezone.now()
    ticket.escalated_by = user
    ticket.save()

    RMSComment.objects.create(
        ticket=ticket,
        author=user,
        comment=f"Escalated to {target_name}. Reason: {reason}",
        action_taken=f"ESCALATED_{target_authority}"
    )

    messages.warning(request, f"Ticket {ticket.ticket_code} has been escalated to {target_name} for higher-level resolution.")
    return redirect(f"/rms/tickets/{pk}/")


@login_required
@require_POST
def resolve_rms_request_view(request, pk):
    """
    Warden, Chief Warden, Dean (DSW), or Administrator resolves the query with closing remarks.
    """
    ticket = get_object_or_404(RMSRequest, id=pk)
    user = request.user

    if user.is_student:
        messages.error(request, "Permission denied.")
        return redirect(f"/rms/tickets/{pk}/")

    closing_remarks = request.POST.get('closing_remarks', '').strip()
    if not closing_remarks:
        messages.error(request, "Closing remarks are required to resolve a ticket.")
        return redirect(f"/rms/tickets/{pk}/")

    ticket.status = RMSRequest.Status.RESOLVED
    ticket.closing_remarks = closing_remarks
    ticket.resolved_by = user
    ticket.resolved_at = timezone.now()
    ticket.save()

    RMSComment.objects.create(
        ticket=ticket,
        author=user,
        comment=closing_remarks,
        action_taken="TICKET_RESOLVED"
    )

    messages.success(request, f"Ticket {ticket.ticket_code} has been marked as RESOLVED.")
    return redirect(f"/rms/tickets/{pk}/")


@login_required
@require_POST
def add_rms_comment_view(request, pk):
    """
    Add remark / progress note / inquiry reply to an active RMS ticket.
    """
    ticket = get_object_or_404(RMSRequest, id=pk)
    user = request.user

    comment_text = request.POST.get('comment', '').strip()
    if comment_text:
        RMSComment.objects.create(
            ticket=ticket,
            author=user,
            comment=comment_text,
            action_taken="NOTE_ADDED"
        )
        if ticket.status == RMSRequest.Status.OPEN and not user.is_student:
            ticket.status = RMSRequest.Status.IN_PROGRESS
            ticket.save()

        messages.success(request, "Update recorded successfully.")

    return redirect(f"/rms/tickets/{pk}/")


@login_required
@require_POST
def rate_rms_request_view(request, pk):
    """
    Student rates the resolution (1 to 5 stars) once closed/resolved.
    """
    ticket = get_object_or_404(RMSRequest, id=pk)
    if ticket.student != request.user:
        messages.error(request, "You can only rate your own tickets.")
        return redirect('/rms/')

    rating = request.POST.get('rating')
    if rating:
        try:
            rating_val = int(rating)
            if 1 <= rating_val <= 5:
                ticket.student_rating = rating_val
                ticket.status = RMSRequest.Status.CLOSED
                ticket.save()
                messages.success(request, "Thank you for your feedback rating!")
        except ValueError:
            pass

    return redirect(f"/rms/tickets/{pk}/")
