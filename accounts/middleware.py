from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import get_user_model

User = get_user_model()

class RBACMiddleware:
    """
    Role-Based Access Control middleware.
    Enforces server-side route guards for student, warden, admin, and dean views.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        user = request.user

        # Public paths that never require auth
        public_prefixes = ['/login/', '/signup/', '/static/', '/media/', '/django-admin/']
        is_public = path == '/' or any(path.startswith(p) for p in public_prefixes)

        if not is_public and not user.is_authenticated:
            return redirect(f"/login/?next={path}")

        if user.is_authenticated:
            # Warden routes (Warden, Chief Warden, Admin)
            if path.startswith('/warden/') and not (user.is_warden or user.is_chief_warden or user.is_admin_role):
                messages.error(request, "Access Denied: Warden authorization required for this section.")
                return redirect('/dashboard/')

            # Admin routes (Admin only)
            if path.startswith('/admin/') and not user.is_admin_role:
                messages.error(request, "Access Denied: Administrator privileges required for this section.")
                return redirect('/dashboard/')

            # Dean / DSW analytics (DSW, Chief Warden, Admin)
            if path.startswith('/dean/') and not (user.is_dsw or user.is_chief_warden or user.is_admin_role):
                messages.error(request, "Access Denied: Dean of Student Welfare (DSW) or Administrative role required.")
                return redirect('/dashboard/')

            # Hostel management (Admin and DSW only)
            if path.startswith('/hostels/') and not (user.is_dsw or user.is_admin_role):
                messages.error(request, "Access Denied: Administrator or DSW role required to manage hostels.")
                return redirect('/dashboard/')

            # Student-only exchange routes
            if (path.startswith('/exchange-requests/') or path.startswith('/matches/')) and not user.is_student:
                messages.error(request, "Access Denied: Room exchange creation and matching are reserved for resident students.")
                return redirect('/dashboard/')

        response = self.get_response(request)
        return response
