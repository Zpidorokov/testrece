from __future__ import annotations

from decimal import Decimal
from typing import Iterable, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AirouterDecision, ContentType, DialogMode, KnowledgeKind
from app.core.settings import Settings
from app.integrations.openrouter import OpenRouterAdapter, build_fallback_output
from app.models import Client, Dialog, KnowledgeItem, Service
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
GENERAL_SERVICE_PATTERNS = [
    "какие услуги",
    "что есть",
    "что делаете",
    "по услугам",
    "какие процедуры",
    "что у вас есть",
]


def _tokenize(text: str) -> list[str]:
    return [word.strip(".,!?():;\"'").lower() for word in text.split() if len(word.strip(".,!?():;\"'")) > 2]


def _looks_like_general_service_question(text: str) -> bool:
    lower = text.lower()
    return any(pattern in lower for pattern in GENERAL_SERVICE_PATTERNS)


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
    if _looks_like_general_service_question(lower) or any(keyword in lower for keyword in SERVICE_KEYWORDS):
        return "service_info"
    if any(word in lower for word in ["привет", "hello", "добрый"]):
        return "greeting"
    return "unknown"


def _risk_level(text: str) -> str:
    lower = text.lower()
    return "high" if any(keyword in lower for keyword in HIGH_RISK_KEYWORDS) else "low"


def _simple_knowledge_search(db: Session, text: str, intent: str) -> List[KnowledgeItem]:
    words = _tokenize(text)
    items = list(db.scalars(select(KnowledgeItem).where(KnowledgeItem.is_active.is_(True))).all())
    ranked = []
    kind_weights = {
        "service_info": {
            KnowledgeKind.SERVICE_INFO.value: 5,
            KnowledgeKind.PROMO.value: 2,
            KnowledgeKind.OBJECTION_HANDLING.value: 1,
        },
        "price": {
            KnowledgeKind.SERVICE_INFO.value: 4,
            KnowledgeKind.PROMO.value: 3,
            KnowledgeKind.OBJECTION_HANDLING.value: 2,
        },
        "booking": {
            KnowledgeKind.POLICY.value: 4,
            KnowledgeKind.SERVICE_INFO.value: 2,
            KnowledgeKind.FAQ.value: 1,
        },
        "reschedule": {
            KnowledgeKind.POLICY.value: 5,
        },
        "cancel": {
            KnowledgeKind.POLICY.value: 5,
        },
        "complaint": {
            KnowledgeKind.CONTRAINDICATION.value: 5,
            KnowledgeKind.ESCALATION_RULE.value: 5,
        },
    }
    for item in items:
        haystack = f"{item.title} {item.content}".lower()
        score = sum(1 for word in words if word in haystack)
        score += kind_weights.get(intent, {}).get(item.kind, 0)
        if score > 0 or item.kind == KnowledgeKind.TONE_OF_VOICE.value:
            ranked.append((score, item))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in ranked[:4]]


def _load_active_services(db: Session) -> List[Service]:
    return list(db.scalars(select(Service).where(Service.is_active.is_(True)).order_by(Service.id.asc())).all())


def _format_amount(value: Decimal | float | int | None) -> str:
    if value is None:
        return ""
    amount = float(value)
    if amount.is_integer():
        return str(int(amount))
    return f"{amount:.0f}"


def _format_price_band(service: Service) -> str:
    low = _format_amount(service.price_from)
    high = _format_amount(service.price_to)
    if low and high and low != high:
        return f"{low}-{high} ₽"
    if low:
        return f"от {low} ₽"
    if high:
        return f"до {high} ₽"
    return "цену уточним у администратора"


def _service_line(service: Service) -> str:
    return f"{service.name} — {_format_price_band(service)}, {service.duration_min} мин"


def _match_services(text: str, services: Iterable[Service]) -> List[Service]:
    words = set(_tokenize(text))
    ranked: list[tuple[int, Service]] = []
    for service in services:
        haystack = f"{service.name} {service.description or ''}".lower()
        score = sum(2 for word in words if word in haystack)
        if "маник" in haystack and "маник" in text.lower():
            score += 4
        if "педик" in haystack and "педик" in text.lower():
            score += 4
        if "бров" in haystack and "бров" in text.lower():
            score += 4
        if "ресниц" in haystack and "ресниц" in text.lower():
            score += 4
        if "стриж" in haystack and "стриж" in text.lower():
            score += 4
        if "окраш" in haystack and "окраш" in text.lower():
            score += 4
        if score > 0:
            ranked.append((score, service))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [service for _, service in ranked[:3]]


def _catalog_messages(services: List[Service]) -> list[str]:
    if not services:
        lines = "\n".join(
            [
                "• маникюр и педикюр",
                "• брови и ресницы",
                "• стрижки и укладки",
                "• консультации по окрашиванию",
            ]
        )
        return [
            f"Сейчас обычно помогаем с такими направлениями:\n{lines}",
            "Если хочешь, подскажу, что подойдет именно тебе и что можно сделать в ближайшее время.",
        ]
    lines = "\n".join(f"• {_service_line(service)}" for service in services[:6])
    return [
        f"У нас сейчас можно записаться на:\n{lines}",
        "Если хочешь, подскажу, что лучше подойдет по запросу, бюджету или по времени.",
    ]


def _service_detail_messages(services: List[Service]) -> list[str]:
    primary = services[0]
    details = primary.description or primary.name
    message = f"{primary.name}: {_format_price_band(primary)}, около {primary.duration_min} мин. {details}"
    if len(services) > 1:
        alternatives = ", ".join(service.name for service in services[1:])
        return [
            message,
            f"Если хочешь, могу еще сравнить с вариантами: {alternatives}.",
        ]
    return [message, "Если удобно, после этого сразу подберу свободное окно."]


def _knowledge_facts(knowledge_items: List[KnowledgeItem]) -> list[str]:
    facts: list[str] = []
    for item in knowledge_items:
        first_sentence = item.content.split(".")[0].strip()
        if first_sentence:
            facts.append(f"{item.title}: {first_sentence}.")
    return facts[:4]


def _text_overlap(left: str, right: str) -> float:
    left_tokens = set(_tokenize(left))
    right_tokens = set(_tokenize(right))
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / max(len(left_tokens), 1)


def _looks_like_knowledge_dump(result: AIRouterOutput, knowledge_items: List[KnowledgeItem]) -> bool:
    for message in result.reply.messages:
        if len(_tokenize(message)) < 8:
            continue
        normalized_message = " ".join(_tokenize(message))
        for item in knowledge_items:
            normalized_item = " ".join(_tokenize(item.content))
            if not normalized_item:
                continue
            if normalized_message in normalized_item:
                return True
            if _text_overlap(message, item.content) >= 0.72:
                return True
    return False


def _heuristic_messages(intent: str, text: str, knowledge_items: List[KnowledgeItem], services: List[Service]) -> AIRouterOutput:
    risk = _risk_level(text)
    if risk == "high":
        return build_fallback_output(
            intent=intent,
            risk_level="high",
            should_escalate=True,
            messages=["Поняла вас. Подключаю администратора, чтобы помочь аккуратно и по делу."],
            next_action="handoff_to_human",
        )

    matched_services = _match_services(text, services)
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
        if matched_services:
            messages = [
                f"По стоимости могу сориентировать так: {_service_line(matched_services[0])}.",
                "Если хочешь, сразу подберу удобное окно или покажу ближайшие варианты по этой услуге.",
            ]
            return build_fallback_output(intent, "low", False, messages, "offer_booking")
        return build_fallback_output(
            intent,
            "low",
            False,
            ["Подскажу по стоимости. Напишите, пожалуйста, какая именно услуга вас интересует: маникюр, педикюр, брови, ресницы, стрижка или окрашивание."],
            "clarify_service",
        )
    if intent == "service_info":
        if _looks_like_general_service_question(text) or not matched_services:
            return build_fallback_output(intent, "low", False, _catalog_messages(services), "clarify_service")
        return build_fallback_output(intent, "low", False, _service_detail_messages(matched_services), "offer_booking")
    if intent == "greeting":
        return build_fallback_output(
            intent,
            "low",
            False,
            ["Здравствуйте. Помогу с услугами, ценами и записью в салон.", "Что хотите подобрать: маникюр, педикюр, брови, ресницы, стрижку или окрашивание?"],
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
    services = _load_active_services(db)
    knowledge_items = _simple_knowledge_search(db, message_text, intent)
    fallback = _heuristic_messages(intent, message_text, knowledge_items, services)
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
    knowledge_facts = _knowledge_facts(knowledge_items)
    service_catalog = [
        {
            "name": service.name,
            "description": service.description,
            "duration_min": service.duration_min,
            "price_from": _format_amount(service.price_from),
            "price_to": _format_amount(service.price_to),
        }
        for service in services[:8]
    ]
    prompt = (
        "You are a Russian-speaking salon receptionist.\n"
        "Return structured JSON only.\n"
        "Knowledge facts are internal notes. Never quote them verbatim and never dump long paragraphs from them.\n"
        "First answer the user's actual question in a natural, helpful way.\n"
        "If the user asks which services are available, summarize the service catalog rather than talking about address or policies.\n"
        "Mention address, working hours, promo or policy only when relevant to the user's question.\n"
        "Usually reply in 1-2 short messages. Ask at most one clarifying question.\n"
        f"Input: {input_payload.model_dump_json(ensure_ascii=False)}\n"
        f"Service catalog: {service_catalog}\n"
        f"Knowledge facts: {knowledge_facts}"
    )
    adapter = OpenRouterAdapter(settings)
    try:
        result = await adapter.generate(prompt=prompt, fallback=fallback)
    except Exception:
        result = fallback
    if _looks_like_knowledge_dump(result, knowledge_items):
        result = fallback
    if content_type == ContentType.PHOTO.value and result.risk_level == "high":
        result.decision = AirouterDecision.ESCALATE.value
        result.should_escalate = True
    if len(result.reply.messages) > 3:
        result.reply.messages = result.reply.messages[:3]
    return result
