from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.core.exceptions import PermissionDenied
from .models import Hostel, Block, Room, Bed

def require_admin_or_dsw(view_func):
    """Decorator to enforce Admin or DSW role."""
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/login/?next={request.path}")
        if not (request.user.is_admin_role or request.user.is_dsw):
            messages.error(request, "Access Denied: Hostel management requires Administrator or DSW role.")
            return redirect('/dashboard/')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@login_required
@require_admin_or_dsw
def hostels_list_view(request):
    """
    Lists all hostels with room/bed capacity statistics, active status, and dynamic CRUD actions.
    """
    gender_filter = request.GET.get('gender', 'ALL')
    search_query = request.GET.get('q', '').strip()

    hostels_qs = Hostel.objects.all().order_by('gender_type', 'code')

    if gender_filter in [Hostel.GenderType.MALE, Hostel.GenderType.FEMALE, Hostel.GenderType.COED]:
        hostels_qs = hostels_qs.filter(gender_type=gender_filter)

    if search_query:
        hostels_qs = hostels_qs.filter(
            Q(name__icontains=search_query) | Q(code__icontains=search_query)
        )

    # Compute aggregate KPI metrics across all hostels
    total_hostels = Hostel.objects.count()
    total_boys = Hostel.objects.filter(gender_type=Hostel.GenderType.MALE).count()
    total_girls = Hostel.objects.filter(gender_type=Hostel.GenderType.FEMALE).count()
    total_beds = Bed.objects.count()
    occupied_beds = Bed.objects.filter(occupancy_status=Bed.OccupancyStatus.OCCUPIED).count()
    vacant_beds = Bed.objects.filter(occupancy_status=Bed.OccupancyStatus.VACANT).count()

    context = {
        'hostels': hostels_qs,
        'gender_filter': gender_filter,
        'search_query': search_query,
        'total_hostels': total_hostels,
        'total_boys': total_boys,
        'total_girls': total_girls,
        'total_beds': total_beds,
        'occupied_beds': occupied_beds,
        'vacant_beds': vacant_beds,
        'GenderType': Hostel.GenderType,
    }
    return render(request, 'hostel/hostels_list.html', context)


@login_required
@require_admin_or_dsw
def hostel_create_view(request):
    """
    Dynamically creates a new Hostel and auto-provisions Blocks, Rooms, and Beds.
    """
    if request.method != 'POST':
        return redirect('hostels_list')

    name = request.POST.get('name', '').strip()
    code = request.POST.get('code', '').strip().upper()
    gender_type = request.POST.get('gender_type', Hostel.GenderType.MALE)
    
    try:
        blocks_count = max(1, min(int(request.POST.get('blocks_count', 2)), 6))
        floors_count = max(1, min(int(request.POST.get('floors_count', 3)), 8))
        rooms_per_floor = max(1, min(int(request.POST.get('rooms_per_floor', 4)), 20))
    except (ValueError, TypeError):
        blocks_count = 2
        floors_count = 3
        rooms_per_floor = 4

    room_type_pattern = request.POST.get('room_type_pattern', 'mixed')

    if not name or not code:
        messages.error(request, "Hostel Name and Code are required.")
        return redirect('hostels_list')

    if Hostel.objects.filter(code__iexact=code).exists():
        messages.error(request, f"A hostel with code '{code}' already exists.")
        return redirect('hostels_list')

    if Hostel.objects.filter(name__iexact=name).exists():
        messages.error(request, f"A hostel with name '{name}' already exists.")
        return redirect('hostels_list')

    with transaction.atomic():
        hostel = Hostel.objects.create(
            name=name,
            code=code,
            gender_type=gender_type,
            is_active=True
        )

        # Generate blocks A, B, C...
        created_beds_count = 0
        for b_idx in range(blocks_count):
            letter = chr(65 + b_idx)
            block = Block.objects.create(
                hostel=hostel,
                name=f"Block {letter}",
                code=letter
            )

            for floor in range(1, floors_count + 1):
                for r_idx in range(1, rooms_per_floor + 1):
                    r_number = f"{floor}{r_idx:02d}"

                    if room_type_pattern == 'single':
                        r_type = Room.RoomType.SINGLE
                        cap = 1
                    elif room_type_pattern == 'double':
                        r_type = Room.RoomType.DOUBLE
                        cap = 2
                    elif room_type_pattern == 'triple':
                        r_type = Room.RoomType.TRIPLE
                        cap = 3
                    elif room_type_pattern == 'quad':
                        r_type = Room.RoomType.FOUR_SHARING
                        cap = 4
                    elif room_type_pattern == 'dorm7':
                        r_type = Room.RoomType.SEVEN_SEATER
                        cap = 7
                    elif room_type_pattern == 'dorm8':
                        r_type = Room.RoomType.EIGHT_SEATER
                        cap = 8
                    elif room_type_pattern == 'diverse':
                        # Distribute across 1, 2, 3, 4, 7, 8
                        configs = [
                            (Room.RoomType.SINGLE, 1),
                            (Room.RoomType.DOUBLE, 2),
                            (Room.RoomType.TRIPLE, 3),
                            (Room.RoomType.FOUR_SHARING, 4),
                            (Room.RoomType.SEVEN_SEATER, 7),
                            (Room.RoomType.EIGHT_SEATER, 8),
                        ]
                        r_type, cap = configs[(r_idx - 1) % len(configs)]
                    else:
                        # Mixed: alternating double and single
                        is_double = (r_idx % 2 == 0)
                        r_type = Room.RoomType.DOUBLE if is_double else Room.RoomType.SINGLE
                        cap = 2 if is_double else 1

                    room = Room.objects.create(
                        block=block,
                        room_number=r_number,
                        floor=floor,
                        room_type=r_type,
                        capacity=cap,
                        has_attached_bath=(r_idx == 1),
                        has_ac=(floor >= 2)
                    )

                    for bed_num in range(1, cap + 1):
                        Bed.objects.create(
                            room=room,
                            bed_number=f"Bed {bed_num}",
                            occupancy_status=Bed.OccupancyStatus.VACANT
                        )
                        created_beds_count += 1

    messages.success(
        request,
        f"Hostel '{hostel.name}' ({hostel.code}) successfully created with {blocks_count} Blocks and {created_beds_count} Beds."
    )
    return redirect('hostels_list')


@login_required
@require_admin_or_dsw
def hostel_delete_view(request, pk):
    """
    Safely deletes a hostel. Rejects deletion if any beds are currently occupied.
    """
    if request.method != 'POST':
        return redirect('hostels_list')

    hostel = get_object_or_404(Hostel, pk=pk)

    # Check for occupied beds
    occupied_count = Bed.objects.filter(
        room__block__hostel=hostel,
        occupancy_status=Bed.OccupancyStatus.OCCUPIED
    ).count()

    if occupied_count > 0:
        messages.error(
            request,
            f"Cannot delete '{hostel.name} ({hostel.code})': {occupied_count} resident student(s) currently occupy rooms here. Vacate or reassign residents before deletion."
        )
        return redirect('hostels_list')

    hostel_name = hostel.name
    hostel_code = hostel.code

    with transaction.atomic():
        # Clear out beds, rooms, blocks cleanly
        Bed.objects.filter(room__block__hostel=hostel).delete()
        Room.objects.filter(block__hostel=hostel).delete()
        Block.objects.filter(hostel=hostel).delete()
        hostel.delete()

    messages.success(request, f"Hostel '{hostel_name} ({hostel_code})' and its associated rooms have been removed.")
    return redirect('hostels_list')


@login_required
@require_admin_or_dsw
def hostel_toggle_status_view(request, pk):
    """
    Toggles the active/inactive state of a hostel.
    """
    if request.method != 'POST':
        return redirect('hostels_list')

    hostel = get_object_or_404(Hostel, pk=pk)
    hostel.is_active = not hostel.is_active
    hostel.save()

    status_str = "Active" if hostel.is_active else "Inactive"
    messages.info(request, f"Hostel '{hostel.name}' is now marked as {status_str}.")
    return redirect('hostels_list')
