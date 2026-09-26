from typing import Optional, Dict, Any
from django.contrib.auth import get_user_model
from exchange.models import AuditEntry

User = get_user_model()

class AuditService:
    @staticmethod
    def log(
        action: str,
        entity_type: str,
        entity_id: Any,
        actor: Optional[User] = None,
        previous_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """
        Creates an immutable audit log entry for university record-keeping.
        """
        return AuditEntry.objects.create(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            previous_state=previous_state,
            new_state=new_state,
            metadata=metadata or {}
        )
