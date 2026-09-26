from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

class UniversalAuthBackend(ModelBackend):
    """
    Allows authentication via Email, Username, or University ID.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if not username or not password:
            return None

        clean_identifier = username.strip()
        try:
            user = User.objects.filter(
                Q(username__iexact=clean_identifier) |
                Q(email__iexact=clean_identifier) |
                Q(university_id__iexact=clean_identifier)
            ).first()
        except Exception:
            return None

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
