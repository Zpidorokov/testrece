from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select

from app.api.deps import DbSession, get_current_user
from app.models import AuditLog, WebhookEvent

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/errors")
def system_errors(db: DbSession) -> list[dict]:
    stmt = select(AuditLog).where(AuditLog.action.like("%error%")).order_by(desc(AuditLog.created_at)).limit(100)
    return [
        {
            "id": item.id,
            "action": item.action,
            "entity_type": item.entity_type,
            "entity_id": item.entity_id,
            "payload_json": item.payload_json,
            "created_at": item.created_at,
        }
        for item in db.scalars(stmt).all()
    ]


@router.get("/jobs")
def jobs(db: DbSession) -> list[dict]:
    stmt = select(WebhookEvent).order_by(desc(WebhookEvent.created_at)).limit(20)
    return [
        {"id": event.id, "event_key": event.event_key, "created_at": event.created_at}
        for event in db.scalars(stmt).all()
    ]


@router.get("/audit-logs")
def audit_logs(db: DbSession) -> list[dict]:
    stmt = select(AuditLog).order_by(desc(AuditLog.created_at)).limit(200)
    return [
        {
            "id": item.id,
            "actor_type": item.actor_type,
            "action": item.action,
            "entity_type": item.entity_type,
            "entity_id": item.entity_id,
            "payload_json": item.payload_json,
            "created_at": item.created_at,
        }
        for item in db.scalars(stmt).all()
    ]
