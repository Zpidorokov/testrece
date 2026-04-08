from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AirouterDecision, ContentType, DialogMode, KnowledgeKind
from app.core.settings import Settings
from app.integrations.openrouter import OpenRouterAdapter, build_fallback_output
from app.models import Client, Dialog, KnowledgeItem
from app.schemas.telegram import AIRouterInput, AIRouterOutput


HIGH_RISK_KEYWORDS = [
    "жалоб",
    "возврат",
    "refund",
    "врач",
    "аллерг",
    "кров",
    "ожог",
    "позовите человека",
    "manager",
]
BOOKING_KEYWORDS = ["запис", "slot", "окно", "перенес", "отмен", "appointment", "сегодня", "завтра"]
PRICE_KEYWORDS = ["цена", "стоим", "сколько"]
SERVICE_KEYWORDS = ["услуг", "маник", "бров", "лазер", "окраш"]


def _detect_intent(text: str) -> str:
    lower = text.lower()
    if any(keyword in lower for keyword in HIGH_RISK_KEYWORDS):
        return "complaint"
    if any(keyword in lower for keyword in BOOKING_KEYWORDS):
        if "перенес" in lower:
            return "reschedule"
        if "отмен" in lower:
            return "cancel"
        return "booking"
    if any(keyword in lower for keyword in PRICE_KEYWORDS):
        return "price"
    if any(keyword in lower for keyword in SERVICE_KEYWORDS):
        return "service_info"
    if any(word in lower for word in ["привет", "hello", "добрый"]):
        return "greeting"
    return "unknown"


def _risk_level(text: str) -> str:
    lower = text.lower()
    return "high" if any(keyword in lower for keyword in HIGH_RISK_KEYWORDS) else "low"


def _simple_knowledge_search(db: Session, text: str) -> List[KnowledgeItem]:
    words = [word.strip(".,!?").lower() for word in text.split() if len(word.strip(".,!?")) > 3]
    items = list(db.scalars(select(KnowledgeItem).where(KnowledgeItem.is_active.is_(True))).all())
    ranked = []
    for item in items:
        haystack = f"{item.title} {item.content}".lower()
        score = sum(1 for word in words if word in haystack)
        if score > 0 or item.kind == KnowledgeKind.TONE_OF_VOICE.value:
            ranked.append((score, item))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in ranked[:3]]


def _heuristic_messages(intent: str, text: str, knowledge_items: List[KnowledgeItem]) -> AIRouterOutput:
    risk = _risk_level(text)
    if risk == "high":
        return build_fallback_output(
            intent=intent,
            risk_level="high",
            should_escalate=True,
            messages=["Поняла вас. Подключаю администратора, чтобы помочь аккуратно и по делу."],
            next_action="handoff_to_human",
        )

    knowledge_hint = knowledge_items[0].content[:160] if knowledge_items else ""
    if intent == "booking":
        messages = [
            "Да, можем подобрать запись в Telegram.",
            "Подскажите, какая услуга вам нужна и удобнее днём или ближе к вечеру?",
        ]
        return build_fallback_output(intent, "medium", False, messages, "request_time_preference")
    if intent == "reschedule":
        return build_fallback_output(
            intent,
            "medium",
            False,
            ["Помогу с переносом. Напишите, пожалуйста, на какой день или время хотите перенести визит."],
            "request_new_slot",
        )
    if intent == "cancel":
        return build_fallback_output(
            intent,
            "medium",
            False,
            ["Подтверждаю отмену. Если захотите, сразу помогу подобрать новую удобную дату."],
            "confirm_cancel",
        )
    if intent == "price":
        answer = knowledge_hint or "Подскажу по стоимости. Напишите, пожалуйста, какая именно услуга вас интересует."
        return build_fallback_output(intent, "low", False, [answer], "clarify_service")
    if intent == "service_info":
        answer = knowledge_hint or "Расскажу по услуге и помогу выбрать подходящий вариант."
        return build_fallback_output(intent, "low", False, [answer, "Если удобно, после этого сразу подберу свободное окно."], "offer_booking")
    if intent == "greeting":
        return build_fallback_output(
            intent,
            "low",
            False,
            ["Здравствуйте. Помогу с услугами, ценами и записью.", "Что вас интересует сейчас?"],
            "await_question",
        )
    return build_fallback_output(
        "unknown",
        "medium",
        False,
        ["Хочу ответить точно, поэтому немного уточню: какая услуга или вопрос вас интересует?"],
        "ask_clarification",
    )


async def route_ai(
    db: Session,
    *,
    settings: Settings,
    client: Client,
    dialog: Dialog,
    message_text: str,
    content_type: str,
    context: dict,
) -> AIRouterOutput:
    if dialog.mode == DialogMode.MANUAL.value:
        return AIRouterOutput(
            decision=AirouterDecision.NO_REPLY.value,
            intent="manual_mode",
            risk_level="low",
            should_escalate=False,
            reply={"split": False, "messages": []},
            extracted_entities={},
            next_action="none",
        )

    intent = _detect_intent(message_text)
    knowledge_items = _simple_knowledge_search(db, message_text)
    fallback = _heuristic_messages(intent, message_text, knowledge_items)
    input_payload = AIRouterInput(
        client={"id": client.id, "name": client.full_name, "status": client.status, "tags": [tag.tag for tag in client.tags]},
        dialog={
            "id": dialog.id,
            "mode": dialog.mode,
            "history": [{"role": msg.sender_type, "text": msg.text_content or ""} for msg in dialog.messages[-8:]],
        },
        message={"text": message_text, "content_type": content_type},
        context=context,
        rules={
            "medical_sensitive": True,
            "allow_humor": True,
            "max_message_len": settings.max_ai_message_len,
        },
    )
    prompt = (
        "You are a Russian-first salon receptionist AI. Use structured JSON only.\n"
        f"Input: {input_payload.model_dump_json(ensure_ascii=False)}\n"
        f"Knowledge: {[{'title': item.title, 'content': item.content[:240]} for item in knowledge_items]}"
    )
    adapter = OpenRouterAdapter(settings)
    try:
        result = await adapter.generate(prompt=prompt, fallback=fallback)
    except Exception:
        result = fallback
    if content_type == ContentType.PHOTO.value and result.risk_level == "high":
        result.decision = AirouterDecision.ESCALATE.value
        result.should_escalate = True
    if len(result.reply.messages) > 3:
        result.reply.messages = result.reply.messages[:3]
    return result
