from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.api.deps import DbSession, get_current_user
from app.models import Notification
from app.schemas.common import StatusMessage
from app.services.notifications import mark_notification_read

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("")
def get_notifications(db: DbSession) -> list[dict]:
    return [
        {
            "id": item.id,
            "type": item.type,
            "status": item.status,
            "dialog_id": item.dialog_id,
            "booking_id": item.booking_id,
            "payload_json": item.payload_json,
            "created_at": item.created_at,
        }
        for item in db.scalars(select(Notification).order_by(Notification.created_at.desc())).all()
    ]


@router.post("/{notification_id}/read", response_model=StatusMessage)
def read_notification(notification_id: int, db: DbSession) -> StatusMessage:
    try:
        mark_notification_read(db, notification_id)
        db.commit()
        return StatusMessage(message="Notification marked as read")
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
