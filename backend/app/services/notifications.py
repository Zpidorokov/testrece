from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.enums import NotificationStatus, NotificationType
from app.models import Notification
from app.services.audit import log_audit_event


def create_notification(
    db: Session,
    *,
    notification_type: str,
    dialog_id: Optional[int] = None,
    booking_id: Optional[int] = None,
    target_user_id: Optional[int] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> Notification:
    notification = Notification(
        type=notification_type,
        dialog_id=dialog_id,
        booking_id=booking_id,
        target_user_id=target_user_id,
        status=NotificationStatus.UNREAD.value,
        payload_json=payload or {},
    )
    db.add(notification)
    db.flush()
    log_audit_event(
        db,
        actor_type="system",
        actor_id=None,
        action="notification_created",
        entity_type="notification",
        entity_id=str(notification.id),
        payload=payload or {},
    )
    return notification


def mark_notification_read(db: Session, notification_id: int) -> Notification:
    notification = db.get(Notification, notification_id)
    if not notification:
        raise ValueError("Notification not found")
    notification.status = NotificationStatus.READ.value
    db.add(notification)
    db.flush()
    return notification


DEFAULT_NOTIFICATION_TYPES = {
    "new_client": NotificationType.NEW_CLIENT.value,
    "new_booking": NotificationType.NEW_BOOKING.value,
}

