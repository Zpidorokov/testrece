from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.integrations.telegram import TelegramGateway
from app.models import Client, Dialog
from app.services.audit import log_audit_event
from app.services.crm import get_or_create_topic_link


def _topic_title(client: Client) -> str:
    base = client.full_name or client.username or f"Client #{client.id}"
    return f"{base} | {client.status}"


async def ensure_topic(
    db: Session,
    *,
    settings: Settings,
    gateway: TelegramGateway,
    client: Client,
    dialog: Dialog,
) -> int:
    if dialog.forum_thread_id:
        return dialog.forum_thread_id

    title = _topic_title(client)
    try:
        created = await gateway.create_forum_topic(settings.staff_group_chat_id, title)
        topic = get_or_create_topic_link(
            db,
            client_id=client.id,
            title=title,
            chat_id=settings.staff_group_chat_id,
            message_thread_id=created.message_thread_id or 1001,
        )
        dialog.forum_topic_id = topic.id
        dialog.forum_thread_id = topic.message_thread_id
        db.add(dialog)
        db.flush()
        log_audit_event(
            db,
            actor_type="system",
            actor_id=None,
            action="forum_topic_created",
            entity_type="dialog",
            entity_id=str(dialog.id),
            payload={"thread_id": topic.message_thread_id},
        )
        await gateway.send_topic_message(
            settings.staff_group_chat_id,
            dialog.forum_thread_id,
            (
                '<tg-emoji emoji-id="5870994129244131212">👤</tg-emoji> '
                f"<b>{client.full_name or 'Новый клиент'}</b>\n"
                f"Статус: {client.status}\n"
                + (f"Telegram: @{client.username}" if client.username else f"ID: {client.telegram_user_id}")
            ),
        )
        return dialog.forum_thread_id
    except Exception as exc:
        log_audit_event(
            db,
            actor_type="system",
            actor_id=None,
            action="forum_topic_failed",
            entity_type="dialog",
            entity_id=str(dialog.id),
            payload={"error": str(exc), "staff_group_chat_id": settings.staff_group_chat_id},
        )
        return 0


async def mirror_to_topic(
    db: Session,
    *,
    settings: Settings,
    gateway: TelegramGateway,
    dialog: Dialog,
    text: str,
    prefix: Optional[str] = None,
) -> None:
    if not dialog.forum_thread_id:
        return
    body = f"{prefix}\n{text}" if prefix else text
    try:
        await gateway.send_topic_message(settings.staff_group_chat_id, dialog.forum_thread_id, body)
        log_audit_event(
            db,
            actor_type="system",
            actor_id=None,
            action="topic_message_synced",
            entity_type="dialog",
            entity_id=str(dialog.id),
            payload={"text": body[:120]},
        )
    except Exception as exc:
        log_audit_event(
            db,
            actor_type="system",
            actor_id=None,
            action="topic_message_sync_failed",
            entity_type="dialog",
            entity_id=str(dialog.id),
            payload={"error": str(exc)},
        )
