from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.enums import ContentType, DialogMode, DialogStatus, MessageDirection, SenderType
from app.core.settings import Settings
from app.integrations.telegram import TelegramGateway
from app.models import Dialog
from app.schemas.crm import SendDialogMessageRequest, TakeoverRequest
from app.services.audit import log_audit_event
from app.services.crm import get_dialog_detail, record_message
from app.services.topic_sync import mirror_to_topic


async def takeover_dialog(db: Session, dialog_id: int, payload: TakeoverRequest) -> Dialog:
    dialog = db.get(Dialog, dialog_id)
    if not dialog:
        raise ValueError("Dialog not found")
    dialog.mode = DialogMode.MANUAL.value
    dialog.status = DialogStatus.MANUAL.value
    dialog.assigned_user_id = payload.assigned_user_id
    db.add(dialog)
    db.flush()
    log_audit_event(
        db,
        actor_type="staff",
        actor_id=str(payload.assigned_user_id),
        action="takeover",
        entity_type="dialog",
        entity_id=str(dialog.id),
        payload={"reason": payload.reason},
    )
    return dialog


def return_dialog_to_auto(db: Session, dialog_id: int) -> Dialog:
    dialog = db.get(Dialog, dialog_id)
    if not dialog:
        raise ValueError("Dialog not found")
    dialog.mode = DialogMode.AUTO.value
    dialog.status = DialogStatus.ACTIVE.value
    dialog.assigned_user_id = None
    db.add(dialog)
    db.flush()
    log_audit_event(
        db,
        actor_type="staff",
        actor_id=None,
        action="return_to_auto",
        entity_type="dialog",
        entity_id=str(dialog.id),
        payload={},
    )
    return dialog


async def send_manual_message(
    db: Session,
    *,
    settings: Settings,
    dialog_id: int,
    payload: SendDialogMessageRequest,
) -> Dialog:
    dialog = get_dialog_detail(db, dialog_id)
    if not dialog:
        raise ValueError("Dialog not found")
    gateway = TelegramGateway(settings)
    sent = await gateway.send_business_message(
        business_connection_id=dialog.business_connection_id or "",
        chat_id=dialog.telegram_chat_id,
        text=payload.text,
    )
    record_message(
        db,
        dialog=dialog,
        telegram_message_id=sent.get("result", {}).get("message_id"),
        business_connection_id=dialog.business_connection_id,
        direction=MessageDirection.OUT.value,
        sender_type=SenderType.STAFF.value,
        content_type=ContentType.TEXT.value,
        text_content=payload.text,
        payload_json={"split_mode": payload.split_mode},
    )
    await mirror_to_topic(
        db,
        settings=settings,
        gateway=gateway,
        dialog=dialog,
        text=payload.text,
        prefix='<tg-emoji emoji-id="5870994129244131212">👤</tg-emoji> Сотрудник',
    )
    return dialog
