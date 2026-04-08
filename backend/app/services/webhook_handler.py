from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import ContentType, DialogMode, MessageDirection, NotificationType, SenderType
from app.core.settings import Settings
from app.integrations.telegram import TelegramGateway
from app.models import Client, Dialog, Message, WebhookEvent
from app.schemas.telegram import AIRouterOutput
from app.services.ai_router import route_ai
from app.services.audit import log_audit_event
from app.services.crm import get_or_create_client_from_telegram, get_or_create_dialog, record_message
from app.services.notifications import create_notification
from app.services.topic_sync import ensure_topic, mirror_to_topic


def _event_key(update: Dict[str, Any]) -> str:
    if "update_id" in update:
        return f"telegram:{update['update_id']}"
    if "business_message" in update:
        return f"business:{update['business_message']['message_id']}"
    return f"telegram:raw:{hash(str(update))}"


def _extract_text_and_type(message: Dict[str, Any]) -> tuple[str, str, Dict[str, Any]]:
    if "text" in message:
        return message.get("text", ""), ContentType.TEXT.value, {}
    if "photo" in message:
        caption = message.get("caption", "")
        return caption or "Клиент отправил фото", ContentType.PHOTO.value, {"photo": message.get("photo", [])}
    if "voice" in message:
        transcript = message["voice"].get("transcript") or message.get("caption") or ""
        payload = {"voice": message["voice"], "transcript": transcript}
        if transcript:
            return transcript, ContentType.VOICE.value, payload
        return "Клиент отправил голосовое сообщение", ContentType.VOICE.value, payload
    return "Получено сообщение unsupported type", ContentType.FILE.value, message


async def process_telegram_update(db: Session, *, settings: Settings, update: Dict[str, Any]) -> bool:
    event_key = _event_key(update)
    if db.scalar(select(WebhookEvent).where(WebhookEvent.event_key == event_key)):
        return False

    db.add(WebhookEvent(event_key=event_key, payload_json=update))
    db.flush()

    gateway = TelegramGateway(settings)

    if "message" in update and update["message"].get("text") == "/admin":
        await gateway.send_admin_entrypoint(update["message"]["chat"]["id"])
        log_audit_event(
            db,
            actor_type="staff",
            actor_id=str(update["message"]["from"]["id"]),
            action="admin_command_requested",
            entity_type="telegram_chat",
            entity_id=str(update["message"]["chat"]["id"]),
            payload={},
        )
        return True

    if "business_connection" in update:
        log_audit_event(
            db,
            actor_type="system",
            actor_id=None,
            action="business_connection_update",
            entity_type="business_connection",
            entity_id=str(update["business_connection"].get("id", event_key)),
            payload=update["business_connection"],
        )
        return True

    if "edited_business_message" in update:
        edited = update["edited_business_message"]
        log_audit_event(
            db,
            actor_type="system",
            actor_id=None,
            action="edited_business_message",
            entity_type="telegram_message",
            entity_id=str(edited.get("message_id", event_key)),
            payload=edited,
        )
        return True

    if "message" in update and update["message"].get("web_app_data"):
        log_audit_event(
            db,
            actor_type="staff",
            actor_id=str(update["message"]["from"]["id"]),
            action="web_app_data_received",
            entity_type="telegram_chat",
            entity_id=str(update["message"]["chat"]["id"]),
            payload=update["message"]["web_app_data"],
        )
        return True

    if "callback_query" in update:
        await gateway.answer_callback_query(update["callback_query"]["id"], "Принято")
        return True

    if "business_message" not in update:
        log_audit_event(
            db,
            actor_type="system",
            actor_id=None,
            action="unsupported_update",
            entity_type="update",
            entity_id=event_key,
            payload=update,
        )
        return True

    message = update["business_message"]
    text, content_type, payload_json = _extract_text_and_type(message)
    client, is_new_client = get_or_create_client_from_telegram(db, message["from"])
    dialog, is_new_dialog = get_or_create_dialog(
        db,
        client=client,
        chat_id=message["chat"]["id"],
        business_connection_id=message.get("business_connection_id"),
    )
    incoming = record_message(
        db,
        dialog=dialog,
        telegram_message_id=message.get("message_id"),
        business_connection_id=message.get("business_connection_id"),
        direction=MessageDirection.IN.value,
        sender_type=SenderType.CLIENT.value,
        content_type=content_type,
        text_content=text,
        payload_json=payload_json,
    )
    await ensure_topic(db, settings=settings, gateway=gateway, client=client, dialog=dialog)
    await mirror_to_topic(
        db,
        settings=settings,
        gateway=gateway,
        dialog=dialog,
        text=text,
        prefix='<tg-emoji emoji-id="5870994129244131212">👤</tg-emoji> Клиент',
    )
    if is_new_client:
        create_notification(
            db,
            notification_type=NotificationType.NEW_CLIENT.value,
            dialog_id=dialog.id,
            payload={"client_id": client.id},
        )

    if content_type == ContentType.VOICE.value and not payload_json.get("transcript"):
        create_notification(
            db,
            notification_type=NotificationType.AI_ERROR.value,
            dialog_id=dialog.id,
            payload={"reason": "voice_without_transcript"},
        )
        await gateway.send_staff_alert(f"Не удалось надёжно расшифровать голосовое в диалоге #{dialog.id}.")

    if dialog.mode == DialogMode.MANUAL.value:
        log_audit_event(
            db,
            actor_type="system",
            actor_id=None,
            action="manual_mode_skip_ai",
            entity_type="dialog",
            entity_id=str(dialog.id),
            payload={"message_id": incoming.id},
        )
        return True

    ai_output = await route_ai(
        db,
        settings=settings,
        client=client,
        dialog=dialog,
        message_text=text,
        content_type=content_type,
        context={"dialog_is_new": is_new_dialog},
    )
    if ai_output.should_escalate or ai_output.decision == "escalate":
        dialog.mode = DialogMode.MANUAL.value
        dialog.status = "escalated"
        db.add(dialog)
        create_notification(
            db,
            notification_type=NotificationType.HUMAN_REQUEST.value,
            dialog_id=dialog.id,
            payload={"reason": ai_output.intent},
        )
        if ai_output.reply.messages:
            await _send_ai_messages(
                db,
                gateway=gateway,
                dialog=dialog,
                business_connection_id=message.get("business_connection_id"),
                chat_id=message["chat"]["id"],
                ai_output=ai_output,
            )
        await gateway.send_staff_alert(f"Диалог #{dialog.id} требует внимания сотрудника.")
        return True

    if ai_output.reply.messages:
        await _send_ai_messages(
            db,
            gateway=gateway,
            dialog=dialog,
            business_connection_id=message.get("business_connection_id"),
            chat_id=message["chat"]["id"],
            ai_output=ai_output,
        )

    return True


async def _send_ai_messages(
    db: Session,
    *,
    gateway: TelegramGateway,
    dialog: Dialog,
    business_connection_id: Optional[str],
    chat_id: int,
    ai_output: AIRouterOutput,
) -> None:
    for part in ai_output.reply.messages:
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
