from django.contrib.auth import get_user_model

User = get_user_model()

def rbac_context(request):
    """
    Supplies role flags to all templates for the top navbar.
    """
    user = request.user
    context = {
        'is_student': False,
        'is_warden': False,
        'is_chief_warden': False,
        'is_admin_role': False,
        'is_dsw': False,
        'unread_notifications_count': 0,
    }

    if user.is_authenticated:
        context['is_student'] = getattr(user, 'is_student', False)
        context['is_warden'] = getattr(user, 'is_warden', False)
        context['is_chief_warden'] = getattr(user, 'is_chief_warden', False)
        context['is_admin_role'] = getattr(user, 'is_admin_role', False)
        context['is_dsw'] = getattr(user, 'is_dsw', False)
        context['user_allocated_bed'] = getattr(user, 'allocated_bed', None)
        
        try:
            from exchange.models import Notification
            context['unread_notifications_count'] = Notification.objects.filter(recipient=user, is_read=False).count()
        except Exception:
            context['unread_notifications_count'] = 0
    else:
        context['user_allocated_bed'] = None

    return context
