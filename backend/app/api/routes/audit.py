from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import desc, select

from app.api.deps import DbSession, get_current_user
from app.models import AuditLog

router = APIRouter(dependencies=[Depends(get_current_user)])


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
