from typing import Optional
from django.contrib.auth import get_user_model
from exchange.models import Notification

User = get_user_model()

class NotificationService:
    @staticmethod
    def send(
        recipient: User,
        title: str,
        message: str,
        notification_type: str = Notification.NotificationType.GENERAL_ALERT,
        link: str = ""
    ) -> Notification:
        """
        Dispatches in-app notification to the recipient user.
        """
        return Notification.objects.create(
            recipient=recipient,
            title=title,
            message=message,
            notification_type=notification_type,
            link=link
        )
