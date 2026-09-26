from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, get_user_model
from django.contrib import messages
from hostel.models import Bed
from .forms import UniversityLoginForm, StudentSignupForm

User = get_user_model()

def login_view(request):
    if request.user.is_authenticated:
        return redirect('/dashboard/')

    if request.method == 'POST':
        form = UniversityLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            next_url = request.GET.get('next')
            if not next_url or next_url == '/dashboard/':
                if user.is_student:
                    next_url = '/dashboard/'
                elif user.role == 'chief_warden' or user.role == 'warden':
                    next_url = '/warden/approvals/'
                elif user.is_dsw:
                    next_url = '/dean/analytics/'
                elif user.is_admin_role:
                    next_url = '/admin/policies/'
                else:
                    next_url = '/dashboard/'
            return redirect(next_url)
        else:
            for error_list in form.errors.values():
                for err in error_list:
                    messages.error(request, err)
    else:
        form = UniversityLoginForm()

    return render(request, 'accounts/login.html', {'form': form})

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('/dashboard/')

    if request.method == 'POST':
        form = StudentSignupForm(request.POST)
        bed_id = request.POST.get('allocated_bed')
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.role = User.Role.STUDENT
            user.save()

            # If student selected an available bed or assign first available matching gender
            if bed_id:
                try:
                    bed = Bed.objects.get(id=bed_id, occupancy_status=Bed.OccupancyStatus.VACANT)
                    bed.current_occupant = user
                    bed.occupancy_status = Bed.OccupancyStatus.OCCUPIED
                    bed.save()
                except Bed.DoesNotExist:
                    pass

            login(request, user)
            messages.success(request, f"Registration successful! Welcome to CampusExchange, {user.first_name}.")
            return redirect('/dashboard/')
    else:
        form = StudentSignupForm()

    vacant_beds = Bed.objects.filter(
        occupancy_status=Bed.OccupancyStatus.VACANT
    ).select_related('room__block__hostel')[:30]

    return render(request, 'accounts/signup.html', {
        'form': form,
        'vacant_beds': vacant_beds
    })

def logout_view(request):
    logout(request)
    messages.info(request, "You have been securely signed out.")
    return redirect('/')

def claim_bed_view(request):
    if not request.user.is_authenticated or not request.user.is_student:
        return redirect('/dashboard/')

    if request.method == 'POST':
        bed_id = request.POST.get('bed_id')
        if bed_id:
            try:
                existing_bed = getattr(request.user, 'allocated_bed', None)
                if existing_bed:
                    messages.warning(request, f"You are already allocated to {existing_bed.room.full_name} ({existing_bed.bed_number}).")
                    return redirect('/dashboard/')

                bed = Bed.objects.select_related('room__block__hostel').get(id=bed_id, occupancy_status=Bed.OccupancyStatus.VACANT)
                hostel_gender = bed.room.block.hostel.gender_type
                if (request.user.gender == User.Gender.MALE and hostel_gender == 'FEMALE') or \
                   (request.user.gender == User.Gender.FEMALE and hostel_gender == 'MALE'):
                    messages.error(request, "Selected room does not match hostel gender residency policy.")
                    return redirect('/dashboard/')

                bed.current_occupant = request.user
                bed.occupancy_status = Bed.OccupancyStatus.OCCUPIED
                bed.save()
                messages.success(request, f"Room allotment successful! You are assigned to {bed.room.full_name} ({bed.bed_number}).")
            except Bed.DoesNotExist:
                messages.error(request, "Selected bed is no longer vacant. Please choose another bed.")
    return redirect('/dashboard/')


# =========================================================================
# ADMIN USER MANAGEMENT (CREATE, MODIFY ROLE, DELETE)
# =========================================================================

def require_admin(view_func):
    """Restricts access exclusively to Administrator role."""
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/login/?next={request.path}")
        if not request.user.is_admin_role:
            messages.error(request, "Access Denied: Administrator role required to manage users.")
            return redirect('/dashboard/')
        return view_func(request, *args, **kwargs)
    return _wrapped


@require_admin
def admin_users_list_view(request):
    """
    Renders user directory with role filters, search, and dynamic modification tools.
    """
    role_filter = request.GET.get('role', 'ALL')
    search_query = request.GET.get('q', '').strip()

    users_qs = User.objects.all().select_related('allocated_bed__room__block__hostel').order_by('-created_at')

    if role_filter in [r.value for r in User.Role]:
        users_qs = users_qs.filter(role=role_filter)

    if search_query:
        from django.db.models import Q
        users_qs = users_qs.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(university_id__icontains=search_query)
        )

    # Metrics
    total_users = User.objects.count()
    students_count = User.objects.filter(role=User.Role.STUDENT).count()
    wardens_count = User.objects.filter(role__in=[User.Role.WARDEN, User.Role.CHIEF_WARDEN]).count()
    dsw_count = User.objects.filter(role=User.Role.DSW).count()
    admins_count = User.objects.filter(role=User.Role.ADMIN).count()

    context = {
        'users': users_qs,
        'role_filter': role_filter,
        'search_query': search_query,
        'total_users': total_users,
        'students_count': students_count,
        'wardens_count': wardens_count,
        'dsw_count': dsw_count,
        'admins_count': admins_count,
        'roles': User.Role.choices,
    }
    return render(request, 'accounts/admin_users_list.html', context)


@require_admin
def admin_user_create_view(request):
    """
    Admin dynamically creates a user with any chosen role.
    """
    if request.method != 'POST':
        return redirect('admin_users_list')

    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip()
    password = request.POST.get('password', '').strip()
    university_id = request.POST.get('university_id', '').strip()
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    role = request.POST.get('role', User.Role.STUDENT)
    gender = request.POST.get('gender', User.Gender.MALE)

    if not username or not email or not password or not university_id:
        messages.error(request, "Username, Email, Password, and University ID are required.")
        return redirect('admin_users_list')

    if User.objects.filter(username__iexact=username).exists():
        messages.error(request, f"A user with username '{username}' already exists.")
        return redirect('admin_users_list')

    if User.objects.filter(email__iexact=email).exists():
        messages.error(request, f"A user with email '{email}' already exists.")
        return redirect('admin_users_list')

    if User.objects.filter(university_id__iexact=university_id).exists():
        messages.error(request, f"A user with University ID '{university_id}' already exists.")
        return redirect('admin_users_list')

    is_staff = (role == User.Role.ADMIN)
    is_superuser = (role == User.Role.ADMIN and request.POST.get('is_superuser') == 'on')

    user = User.objects.create(
        username=username,
        email=email,
        university_id=university_id,
        first_name=first_name,
        last_name=last_name,
        role=role,
        gender=gender,
        is_staff=is_staff,
        is_superuser=is_superuser,
    )
    user.set_password(password)
    user.save()

    messages.success(request, f"User '{user.username}' successfully created with role '{user.get_role_display()}'.")
    return redirect('admin_users_list')


@require_admin
def admin_user_modify_view(request, pk):
    """
    Admin dynamically modifies any user's profile, credentials, and role.
    """
    from django.shortcuts import get_object_or_404
    if request.method != 'POST':
        return redirect('admin_users_list')

    target_user = get_object_or_404(User, pk=pk)

    new_role = request.POST.get('role', target_user.role)
    new_email = request.POST.get('email', target_user.email).strip()
    new_first_name = request.POST.get('first_name', target_user.first_name).strip()
    new_last_name = request.POST.get('last_name', target_user.last_name).strip()
    new_university_id = request.POST.get('university_id', target_user.university_id).strip()
    new_gender = request.POST.get('gender', target_user.gender)
    new_password = request.POST.get('new_password', '').strip()
    is_active = request.POST.get('is_active') == 'on'

    # Check for email uniqueness if changed
    if new_email and new_email.lower() != target_user.email.lower():
        if User.objects.filter(email__iexact=new_email).exclude(pk=target_user.pk).exists():
            messages.error(request, f"Email '{new_email}' is already in use by another user.")
            return redirect('admin_users_list')
        target_user.email = new_email

    # Check for university_id uniqueness if changed
    if new_university_id and new_university_id.lower() != target_user.university_id.lower():
        if User.objects.filter(university_id__iexact=new_university_id).exclude(pk=target_user.pk).exists():
            messages.error(request, f"University ID '{new_university_id}' is already in use.")
            return redirect('admin_users_list')
        target_user.university_id = new_university_id

    # Handle role change
    old_role = target_user.role
    if new_role in [r.value for r in User.Role]:
        target_user.role = new_role

        # If changed away from student, free allocated bed
        if old_role == User.Role.STUDENT and new_role != User.Role.STUDENT:
            if hasattr(target_user, 'allocated_bed'):
                bed = target_user.allocated_bed
                bed.current_occupant = None
                bed.occupancy_status = Bed.OccupancyStatus.VACANT
                bed.save()

        # If changed to admin, grant staff permissions
        if new_role == User.Role.ADMIN:
            target_user.is_staff = True
        elif old_role == User.Role.ADMIN and new_role != User.Role.ADMIN and not target_user.is_superuser:
            target_user.is_staff = False

    target_user.first_name = new_first_name
    target_user.last_name = new_last_name
    target_user.gender = new_gender
    target_user.is_active = is_active

    if new_password:
        target_user.set_password(new_password)

    target_user.save()
    messages.success(
        request,
        f"User '{target_user.username}' successfully updated! Role set to '{target_user.get_role_display()}'."
    )
    return redirect('admin_users_list')


@require_admin
def admin_user_delete_view(request, pk):
    """
    Admin permanently deletes a user account with cascade and bed cleanup.
    """
    from django.shortcuts import get_object_or_404
    if request.method != 'POST':
        return redirect('admin_users_list')

    target_user = get_object_or_404(User, pk=pk)

    # Protect against self-deletion
    if target_user.pk == request.user.pk:
        messages.error(request, "Cannot delete your own active administrator account.")
        return redirect('admin_users_list')

    username = target_user.username

    # Safely free occupied bed if any
    if hasattr(target_user, 'allocated_bed'):
        bed = target_user.allocated_bed
        bed.current_occupant = None
        bed.occupancy_status = Bed.OccupancyStatus.VACANT
        bed.save()

    target_user.delete()
    messages.success(request, f"User '{username}' and associated records have been removed.")
    return redirect('admin_users_list')


