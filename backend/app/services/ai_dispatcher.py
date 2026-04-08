from __future__ import annotations

import asyncio
import html
import hashlib
import re
from datetime import datetime
from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.enums import AirouterDecision, ClientStatus, ContentType, DialogMode, DialogStatus, LeadStage, MessageDirection, NotificationType, SenderType
from app.core.settings import Settings
from app.db.session import SessionLocal
from app.integrations.telegram import TelegramGateway
from app.models import Client, Dialog, Lead, Message, Service, StaffMember
from app.schemas.booking import BookingCreateRequest
from app.schemas.telegram import AIRouterOutput
from app.services.ai_router import route_ai
from app.services.audit import log_audit_event
from app.services.crm import record_message
from app.services.notifications import create_notification
from app.services.scheduling import create_booking
from app.services.topic_sync import mirror_to_topic


_dialog_generations: dict[int, int] = {}
_dialog_tasks: dict[int, asyncio.Task[None]] = {}
_TG_EMOJI_RE = re.compile(r'<tg-emoji emoji-id="[^"]+">.*?</tg-emoji>', re.DOTALL)


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
    ordered = sorted(dialog.messages, key=lambda item: item.id)
    last_outbound_id: Optional[int] = None
    for message in ordered:
        if message.direction == MessageDirection.OUT.value:
            last_outbound_id = message.id

    pending: list[Message] = []
    for message in ordered:
        if message.direction != MessageDirection.IN.value or message.sender_type != SenderType.CLIENT.value:
            continue
        if last_outbound_id and message.id <= last_outbound_id:
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


def _merge_ai_state(dialog: Dialog, patch: Optional[dict]) -> dict:
    state = dict(dialog.ai_state_json or {})
    if patch:
        state.update(patch)
    dialog.ai_state_json = state
    return state


def _latest_lead(db: Session, client_id: int) -> Optional[Lead]:
    return db.scalar(select(Lead).where(Lead.client_id == client_id).order_by(desc(Lead.created_at)).limit(1))


def _apply_status_patch(db: Session, dialog: Dialog, client: Client, patch: Optional[dict]) -> None:
    if not patch:
        return
    dialog_status = patch.get("dialog_status")
    client_status = patch.get("client_status")
    lead_stage = patch.get("lead_stage")
    lead_service_id = patch.get("lead_service_id")

    if dialog_status:
        dialog.status = dialog_status
        db.add(dialog)
    if client_status:
        client.status = client_status
        db.add(client)
    if lead_stage or lead_service_id:
        lead = _latest_lead(db, client.id)
        if lead:
            if lead_stage:
                lead.stage = lead_stage
            if lead_service_id:
                lead.first_interest_service_id = lead_service_id
            db.add(lead)


def _format_slot_label(slot_start: datetime, staff: Optional[StaffMember]) -> str:
    month_names = {
        1: "января",
        2: "февраля",
        3: "марта",
        4: "апреля",
        5: "мая",
        6: "июня",
        7: "июля",
        8: "августа",
        9: "сентября",
        10: "октября",
        11: "ноября",
        12: "декабря",
    }
    date_part = f"{slot_start.day} {month_names[slot_start.month]}"
    time_part = slot_start.strftime("%H:%M")
    if staff:
        return f"{date_part} в {time_part}, мастер {staff.full_name}"
    return f"{date_part} в {time_part}"


def _reply_hash(messages: list[str]) -> str:
    normalized = "\n".join(message.strip().lower() for message in messages if message.strip())
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


def _sanitize_outbound_html(message: str) -> str:
    placeholders: dict[str, str] = {}

    def protect(match: re.Match[str]) -> str:
        key = f"__TG_EMOJI_{len(placeholders)}__"
        placeholders[key] = match.group(0)
        return key

    protected = _TG_EMOJI_RE.sub(protect, message.strip())
    escaped = html.escape(protected, quote=False)
    for key, value in placeholders.items():
        escaped = escaped.replace(key, value)
    escaped = re.sub(r"[ \t]+\n", "\n", escaped)
    escaped = re.sub(r"\n{3,}", "\n\n", escaped)
    escaped = re.sub(r"[ \t]{2,}", " ", escaped)
    return escaped.strip()


def _render_outbound_parts(ai_output: AIRouterOutput) -> list[str]:
    parts = [_sanitize_outbound_html(part) for part in ai_output.reply.messages if part and part.strip()]
    if not parts:
        return []
    if not ai_output.reply.split:
        return ["\n\n".join(parts)]
    return parts


def _parse_selected_slot(item: Optional[dict]) -> Optional[dict]:
    if not item or "start_at" not in item:
        return None
    try:
        return {
            "start_at": datetime.fromisoformat(item["start_at"]),
            "staff_id": item.get("staff_id"),
            "branch_id": item.get("branch_id"),
        }
    except Exception:
        return None


def _finalize_booking_reply(
    db: Session,
    *,
    dialog: Dialog,
    client: Client,
    ai_output: AIRouterOutput,
) -> AIRouterOutput:
    slot = _parse_selected_slot(ai_output.extracted_entities.get("selected_slot"))
    service_id = ai_output.extracted_entities.get("selected_service_id")
    if slot is None or service_id is None:
        ai_output.reply.messages = ["Чтобы зафиксировать запись без ошибки, уточните, пожалуйста, удобный день или выберите один из предложенных вариантов."]
        ai_output.reply.split = False
        ai_output.next_action = "request_time_preference"
        ai_output.extracted_entities["state_patch"] = {
            **(ai_output.extracted_entities.get("state_patch") or {}),
            "last_ai_action": "request_time_preference",
        }
        return ai_output

    service = db.get(Service, service_id)
    staff = db.get(StaffMember, slot["staff_id"]) if slot.get("staff_id") else None
    if not service:
        ai_output.reply.messages = ["Не получилось корректно определить услугу для записи. Напишите, пожалуйста, еще раз, что хотите сделать, и я быстро соберу запись заново."]
        ai_output.reply.split = False
        ai_output.next_action = "clarify_service"
        return ai_output

    try:
        booking = create_booking(
            db,
            BookingCreateRequest(
                client_id=client.id,
                service_id=service.id,
                staff_id=slot.get("staff_id"),
                branch_id=slot.get("branch_id"),
                start_at=slot["start_at"],
                comment="Создано авто-ассистентом в Telegram",
            ),
        )
    except ValueError:
        ai_output.reply.messages = [
            "Пока фиксировала запись, это окно уже заняли. Могу сразу подобрать 2-3 новых варианта — напишите, пожалуйста, удобный день или просто «да»."
        ]
        ai_output.reply.split = False
        ai_output.next_action = "request_time_preference"
        ai_output.extracted_entities["state_patch"] = {
            **(ai_output.extracted_entities.get("state_patch") or {}),
            "offered_slots": [],
            "last_ai_action": "request_time_preference",
        }
        return ai_output

    dialog.status = DialogStatus.BOOKED.value
    client.status = ClientStatus.BOOKED.value
    db.add(dialog)
    db.add(client)
    lead = _latest_lead(db, client.id)
    if lead:
        lead.stage = LeadStage.BOOKED.value
        lead.first_interest_service_id = service.id
        db.add(lead)

    create_notification(
        db,
        notification_type=NotificationType.NEW_BOOKING.value,
        dialog_id=dialog.id,
        booking_id=booking.id,
        payload={"client_id": client.id, "service_id": service.id, "start_at": booking.start_at.isoformat()},
    )

    ai_output.reply.messages = [
        (
            '<tg-emoji emoji-id="5870633910337015697">✅</tg-emoji> '
            f"Запись зафиксировала: {service.name}, {_format_slot_label(booking.start_at, staff)}."
        ),
        "Если захотите, я могу сразу подсказать, как подготовиться к визиту или помочь с переносом.",
    ]
    ai_output.reply.split = True
    ai_output.next_action = "booking_created"
    ai_output.extracted_entities["state_patch"] = {
        **(ai_output.extracted_entities.get("state_patch") or {}),
        "selected_service_id": service.id,
        "offered_slots": [],
        "last_ai_action": "booking_created",
        "booked_booking_id": booking.id,
        "booked_start_at": booking.start_at.isoformat(),
    }
    ai_output.extracted_entities["status_patch"] = {
        "dialog_status": DialogStatus.BOOKED.value,
        "client_status": ClientStatus.BOOKED.value,
        "lead_stage": LeadStage.BOOKED.value,
        "lead_service_id": service.id,
    }
    return ai_output


def _apply_ai_output(db: Session, dialog: Dialog, client: Client, ai_output: AIRouterOutput) -> AIRouterOutput:
    _merge_ai_state(dialog, ai_output.extracted_entities.get("state_patch"))
    _apply_status_patch(db, dialog, client, ai_output.extracted_entities.get("status_patch"))
    if ai_output.next_action == "book_slot":
        ai_output = _finalize_booking_reply(db, dialog=dialog, client=client, ai_output=ai_output)
        _merge_ai_state(dialog, ai_output.extracted_entities.get("state_patch"))
        _apply_status_patch(db, dialog, client, ai_output.extracted_entities.get("status_patch"))
    return ai_output


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
    ai_output = _apply_ai_output(db, dialog, dialog.client, ai_output)

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
    outbound_parts = _render_outbound_parts(ai_output)
    for index, part in enumerate(outbound_parts):
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
        if index < len(outbound_parts) - 1:
            await asyncio.sleep(1.0)
    state = dict(dialog.ai_state_json or {})
    state["last_reply_hash"] = _reply_hash(outbound_parts)
    state["last_ai_action"] = ai_output.extracted_entities.get("state_patch", {}).get("last_ai_action", ai_output.next_action)
    dialog.ai_state_json = state
    db.add(dialog)
