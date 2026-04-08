from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.core.enums import AirouterDecision, ContentType, DialogMode, MessageDirection, NotificationType, SenderType
from app.core.settings import Settings
from app.db.session import SessionLocal
from app.integrations.telegram import TelegramGateway
from app.models import Client, Dialog, Message
from app.schemas.telegram import AIRouterOutput
from app.services.ai_router import route_ai
from app.services.audit import log_audit_event
from app.services.crm import record_message
from app.services.notifications import create_notification
from app.services.topic_sync import mirror_to_topic


_dialog_generations: dict[int, int] = {}
_dialog_tasks: dict[int, asyncio.Task[None]] = {}


def schedule_dialog_ai_response(
    *,
    settings: Settings,
    dialog_id: int,
    business_connection_id: Optional[str],
    chat_id: int,
) -> None:
    generation = _dialog_generations.get(dialog_id, 0) + 1
    _dialog_generations[dialog_id] = generation

    existing = _dialog_tasks.get(dialog_id)
    if existing and not existing.done():
        existing.cancel()

    task = asyncio.create_task(
        _run_dialog_ai_response(
            settings=settings,
            dialog_id=dialog_id,
            business_connection_id=business_connection_id,
            chat_id=chat_id,
            generation=generation,
        )
    )
    _dialog_tasks[dialog_id] = task


async def _run_dialog_ai_response(
    *,
    settings: Settings,
    dialog_id: int,
    business_connection_id: Optional[str],
    chat_id: int,
    generation: int,
) -> None:
    gateway = TelegramGateway(settings)
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(
        _typing_pulse(
            gateway=gateway,
            chat_id=chat_id,
            business_connection_id=business_connection_id,
            stop_event=stop_typing,
        )
    )
    try:
        await asyncio.sleep(settings.ai_reply_debounce_seconds)
        if _dialog_generations.get(dialog_id) != generation:
            return
        with SessionLocal() as db:
            await process_dialog_auto_reply(
                db,
                settings=settings,
                gateway=gateway,
                dialog_id=dialog_id,
                business_connection_id=business_connection_id,
                chat_id=chat_id,
            )
            db.commit()
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        with SessionLocal() as db:
            log_audit_event(
                db,
                actor_type="system",
                actor_id=None,
                action="ai_dispatch_failed",
                entity_type="dialog",
                entity_id=str(dialog_id),
                payload={"error": str(exc)},
            )
            create_notification(
                db,
                notification_type=NotificationType.AI_ERROR.value,
                dialog_id=dialog_id,
                payload={"error": str(exc)},
            )
            db.commit()
        try:
            await gateway.send_staff_alert(f"AI не смог обработать диалог #{dialog_id}: {exc}")
        except Exception:
            pass
    finally:
        stop_typing.set()
        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass
        current = _dialog_tasks.get(dialog_id)
        if current is asyncio.current_task():
            _dialog_tasks.pop(dialog_id, None)


async def _typing_pulse(
    *,
    gateway: TelegramGateway,
    chat_id: int,
    business_connection_id: Optional[str],
    stop_event: asyncio.Event,
) -> None:
    while not stop_event.is_set():
        try:
            await gateway.send_chat_action(
                chat_id=chat_id,
                action="typing",
                business_connection_id=business_connection_id,
            )
        except Exception:
            return
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=4.0)
        except asyncio.TimeoutError:
            continue


def _collect_pending_messages(dialog: Dialog) -> list[Message]:
    ordered = sorted(dialog.messages, key=lambda item: item.created_at)
    last_outbound_at: Optional[datetime] = None
    for message in ordered:
        if message.direction == MessageDirection.OUT.value:
            last_outbound_at = message.created_at

    pending: list[Message] = []
    for message in ordered:
        if message.direction != MessageDirection.IN.value or message.sender_type != SenderType.CLIENT.value:
            continue
        if last_outbound_at and message.created_at <= last_outbound_at:
            continue
        pending.append(message)
    return pending


def _merge_pending_messages(messages: list[Message]) -> tuple[str, str]:
    if not messages:
        return "", ContentType.TEXT.value
    content_type = messages[-1].content_type
    parts = [(message.text_content or "").strip() for message in messages if (message.text_content or "").strip()]
    if not parts:
        parts = ["Клиент отправил несколько сообщений без текста."]
    return "\n".join(parts), content_type


async def process_dialog_auto_reply(
    db: Session,
    *,
    settings: Settings,
    gateway: TelegramGateway,
    dialog_id: int,
    business_connection_id: Optional[str],
    chat_id: int,
) -> bool:
    dialog = db.get(Dialog, dialog_id)
    if not dialog:
        return False
    db.refresh(dialog, attribute_names=["messages", "client"])
    if dialog.mode == DialogMode.MANUAL.value or not dialog.client:
        return False

    pending_messages = _collect_pending_messages(dialog)
    if not pending_messages:
        return False

    merged_text, content_type = _merge_pending_messages(pending_messages)
    ai_output = await route_ai(
        db,
        settings=settings,
        client=dialog.client,
        dialog=dialog,
        message_text=merged_text,
        content_type=content_type,
        context={
            "batched_message_count": len(pending_messages),
            "batched_message_ids": [message.id for message in pending_messages],
        },
    )

    if ai_output.should_escalate or ai_output.decision == AirouterDecision.ESCALATE.value:
        dialog.mode = DialogMode.MANUAL.value
        dialog.status = "escalated"
        db.add(dialog)
        create_notification(
            db,
            notification_type=NotificationType.HUMAN_REQUEST.value,
            dialog_id=dialog.id,
            payload={
                "reason": ai_output.intent,
                "batched_message_count": len(pending_messages),
            },
        )
        if ai_output.reply.messages:
            await send_ai_messages(
                db,
                gateway=gateway,
                dialog=dialog,
                business_connection_id=business_connection_id,
                chat_id=chat_id,
                ai_output=ai_output,
            )
        await gateway.send_staff_alert(f"Диалог #{dialog.id} требует внимания сотрудника.")
        return True

    if ai_output.reply.messages:
        await send_ai_messages(
            db,
            gateway=gateway,
            dialog=dialog,
            business_connection_id=business_connection_id,
            chat_id=chat_id,
            ai_output=ai_output,
        )
        return True
    return False


async def send_ai_messages(
    db: Session,
    *,
    gateway: TelegramGateway,
    dialog: Dialog,
    business_connection_id: Optional[str],
    chat_id: int,
    ai_output: AIRouterOutput,
) -> None:
    for part in ai_output.reply.messages:
        await gateway.send_chat_action(
            chat_id=chat_id,
            action="typing",
            business_connection_id=business_connection_id,
        )
        sent = await gateway.send_business_message(
            business_connection_id=business_connection_id or "",
            chat_id=chat_id,
            text=part,
        )
        record_message(
            db,
            dialog=dialog,
            telegram_message_id=sent.get("result", {}).get("message_id"),
            business_connection_id=business_connection_id,
            direction=MessageDirection.OUT.value,
            sender_type=SenderType.AI.value,
            content_type=ContentType.TEXT.value,
            text_content=part,
            payload_json={"ai_intent": ai_output.intent},
        )
        await mirror_to_topic(
            db,
            settings=gateway.settings,
            gateway=gateway,
            dialog=dialog,
            text=part,
            prefix='<tg-emoji emoji-id="6030400221232501136">🤖</tg-emoji> AI',
        )
