from __future__ import annotations

import hashlib
import re
from datetime import datetime, time, timedelta
from decimal import Decimal
from typing import Iterable, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AirouterDecision, ClientStatus, ContentType, DialogMode, DialogStatus, KnowledgeKind, LeadStage
from app.core.settings import Settings
from app.integrations.openrouter import OpenRouterAdapter, build_fallback_output
from app.models import Branch, Client, Dialog, KnowledgeItem, Service, StaffMember
from app.schemas.telegram import AIRouterInput, AIRouterOutput
from app.services.scheduling import list_slots


PREMIUM_EMOJI = {
    "smile": ('5870764288364252592', "🙂"),
    "calendar": ('5890937706803894250', "📅"),
    "check": ('5870633910337015697', "✅"),
    "pencil": ('5870676941614354370', "🖋"),
}

HIGH_RISK_KEYWORDS = [
    "жалоб",
    "возврат",
    "refund",
    "врач",
    "аллерг",
    "кров",
    "ожог",
    "позовите человека",
    "администратор",
    "manager",
]
TONE_COMPLAINT_PATTERNS = [
    "чё за тон",
    "на ты",
    "так общаешься",
    "грубо",
    "хам",
    "общайся нормально",
    "нормально общайся",
    "на вы",
]
BOOKING_KEYWORDS = ["запис", "окно", "slot", "appointment", "давайте", "подбер", "свободн", "давай", "запиши"]
PRICE_KEYWORDS = ["цена", "стоим", "сколько", "прайс"]
SERVICE_KEYWORDS = ["услуг", "маник", "педик", "бров", "ресниц", "ламин", "стриж", "уклад", "окраш", "airtouch"]
GENERAL_SERVICE_PATTERNS = [
    "какие услуги",
    "какие есть",
    "какие есть услуги",
    "что есть",
    "что делаете",
    "по услугам",
    "какие процедуры",
    "что у вас есть",
]
AFFIRMATIVE_PATTERNS = ["да", "ага", "давай", "давайте", "подходит", "ок", "окей", "беру", "запиши", "записывайте"]
NEGATIVE_PATTERNS = ["нет", "не подходит", "неудобно", "не хочу", "не надо", "другое время", "другой день"]
WEEKDAY_MAP = {
    "понедельник": 0,
    "вторник": 1,
    "среда": 2,
    "четверг": 3,
    "пятница": 4,
    "суббота": 5,
    "воскресенье": 6,
}
MONTH_NAMES = {
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


def _emoji(key: str) -> str:
    emoji_id, fallback = PREMIUM_EMOJI[key]
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'


def _tokenize(text: str) -> list[str]:
    return [word.strip(".,!?():;\"'").lower() for word in text.split() if len(word.strip(".,!?():;\"'")) > 1]


def _normalize_text(text: str) -> str:
    return " ".join(_tokenize(text))


def _hash_messages(messages: list[str]) -> str:
    normalized = "\n".join(_normalize_text(message) for message in messages if message.strip())
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


def _reply(
    *,
    intent: str,
    risk_level: str,
    messages: list[str],
    next_action: str,
    should_escalate: bool = False,
    state_patch: Optional[dict] = None,
    status_patch: Optional[dict] = None,
    extracted: Optional[dict] = None,
) -> AIRouterOutput:
    output = build_fallback_output(intent, risk_level, should_escalate, messages, next_action)
    if state_patch:
        output.extracted_entities["state_patch"] = state_patch
    if status_patch:
        output.extracted_entities["status_patch"] = status_patch
    if extracted:
        output.extracted_entities.update(extracted)
    return output


def _state(dialog: Dialog) -> dict:
    return dict(dialog.ai_state_json or {})


def _detect_intent(text: str) -> str:
    lower = text.lower()
    if any(keyword in lower for keyword in HIGH_RISK_KEYWORDS):
        return "complaint"
    if any(keyword in lower for keyword in TONE_COMPLAINT_PATTERNS):
        return "tone_repair"
    if "перенес" in lower:
        return "reschedule"
    if "отмен" in lower:
        return "cancel"
    if any(keyword in lower for keyword in BOOKING_KEYWORDS):
        return "booking"
    if any(keyword in lower for keyword in PRICE_KEYWORDS):
        return "price"
    if any(pattern in lower for pattern in GENERAL_SERVICE_PATTERNS) or any(keyword in lower for keyword in SERVICE_KEYWORDS):
        return "service_info"
    if any(word in lower for word in ["привет", "здравств", "добрый"]):
        return "greeting"
    return "unknown"


def _is_catalog_question(text: str) -> bool:
    lower = text.lower()
    if any(pattern in lower for pattern in GENERAL_SERVICE_PATTERNS):
        return True
    return (
        ("какие" in lower and "есть" in lower)
        or ("что" in lower and "есть" in lower)
        or ("что" in lower and "делаете" in lower)
        or ("что" in lower and "можете" in lower)
    )


def _is_affirmative(text: str) -> bool:
    lower = text.lower()
    return any(pattern in lower for pattern in AFFIRMATIVE_PATTERNS)


def _is_negative(text: str) -> bool:
    lower = text.lower()
    return any(pattern in lower for pattern in NEGATIVE_PATTERNS)


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
            KnowledgeKind.TONE_OF_VOICE.value: 3,
            KnowledgeKind.PROMO.value: 2,
        },
        "price": {
            KnowledgeKind.SERVICE_INFO.value: 5,
            KnowledgeKind.PROMO.value: 3,
            KnowledgeKind.TONE_OF_VOICE.value: 2,
        },
        "booking": {
            KnowledgeKind.POLICY.value: 4,
            KnowledgeKind.SERVICE_INFO.value: 3,
            KnowledgeKind.TONE_OF_VOICE.value: 2,
        },
        "complaint": {
            KnowledgeKind.CONTRAINDICATION.value: 5,
            KnowledgeKind.ESCALATION_RULE.value: 5,
        },
        "tone_repair": {
            KnowledgeKind.TONE_OF_VOICE.value: 5,
            KnowledgeKind.OBJECTION_HANDLING.value: 3,
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


def _load_staff_map(db: Session) -> dict[int, StaffMember]:
    return {staff.id: staff for staff in db.scalars(select(StaffMember).where(StaffMember.is_active.is_(True))).all()}


def _resolve_branch_id(db: Session, client: Client, staff_map: dict[int, StaffMember]) -> Optional[int]:
    if client.preferred_branch_id:
        return client.preferred_branch_id
    if client.preferred_staff_id and client.preferred_staff_id in staff_map:
        return staff_map[client.preferred_staff_id].branch_id
    return db.scalar(select(Branch.id).where(Branch.is_active.is_(True)).order_by(Branch.id.asc()).limit(1))


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


def _match_services(text: str, services: Iterable[Service]) -> List[Service]:
    words = set(_tokenize(text))
    ranked: list[tuple[int, Service]] = []
    for service in services:
        haystack = f"{service.name} {service.description or ''}".lower()
        score = sum(2 for word in words if word in haystack)
        alias_boosts = {
            "маник": 5,
            "педик": 5,
            "бров": 5,
            "ресниц": 5,
            "ламин": 4,
            "стриж": 5,
            "уклад": 4,
            "окраш": 5,
            "airtouch": 5,
        }
        for alias, bonus in alias_boosts.items():
            if alias in text.lower() and alias in haystack:
                score += bonus
        if score > 0:
            ranked.append((score, service))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [service for _, service in ranked[:3]]


def _current_service(state: dict, services: list[Service]) -> Optional[Service]:
    service_id = state.get("selected_service_id")
    if not service_id:
        return None
    return next((service for service in services if service.id == service_id), None)


def _service_groups(services: list[Service]) -> list[str]:
    names = " ".join(service.name.lower() for service in services)
    groups: list[str] = []
    if "маник" in names or "педик" in names:
        groups.append("маникюр и педикюр")
    if "бров" in names or "ресниц" in names or "ламини" in names:
        groups.append("брови и ресницы")
    if "стриж" in names or "уклад" in names:
        groups.append("стрижки и укладки")
    if "окраш" in names or "airtouch" in names:
        groups.append("консультации по окрашиванию")
    return groups or ["маникюр и педикюр", "брови и ресницы", "стрижки и укладки"]


def _catalog_message(services: list[Service]) -> str:
    lines = "\n".join(f"• {item}" for item in _service_groups(services))
    return (
        "Сейчас можем помочь с такими направлениями:\n"
        f"{lines}\n\n"
        "Если скажете, что именно хочется сделать, я сразу подберу подходящую услугу и ближайшие окна."
    )


def _service_summary(service: Service) -> str:
    description = (service.description or "").strip()
    first_sentence = description.split(".")[0].strip()
    summary = f"По услуге «{service.name}» ориентир такой: {_format_price_band(service)}, около {service.duration_min} минут."
    if first_sentence:
        summary = f"{summary} {first_sentence}."
    return summary


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


def _extract_requested_period(text: str) -> Optional[str]:
    lower = text.lower()
    if any(word in lower for word in ["утром", "утро", "с утра"]):
        return "morning"
    if any(word in lower for word in ["днем", "днём", "после обеда"]):
        return "afternoon"
    if any(word in lower for word in ["вечером", "вечер", "после работы"]):
        return "evening"
    return None


def _extract_explicit_time(text: str) -> Optional[tuple[int, int]]:
    match = re.search(r"(?:\bв\b|\bна\b)?\s*([01]?\d|2[0-3])(?::([0-5]\d))?\b", text.lower())
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    return hour, minute


def _next_weekday(now: datetime, weekday: int) -> datetime:
    delta = (weekday - now.weekday()) % 7
    if delta == 0:
        delta = 7
    return now + timedelta(days=delta)


def _extract_requested_day(text: str, now: datetime) -> Optional[tuple[datetime, datetime, str]]:
    lower = text.lower()
    if "сегодня" in lower:
        day = now
        label = "сегодня"
    elif "завтра" in lower:
        day = now + timedelta(days=1)
        label = "завтра"
    elif "послезавтра" in lower:
        day = now + timedelta(days=2)
        label = "послезавтра"
    else:
        day = None
        label = ""
        for word, weekday in WEEKDAY_MAP.items():
            if word in lower:
                day = _next_weekday(now, weekday)
                label = f"в {word}"
                break
    if day is None:
        return None
    start = datetime.combine(day.date(), time.min)
    end = datetime.combine(day.date(), time.max)
    return start, end, label


def _day_window(now: datetime, explicit_day: Optional[tuple[datetime, datetime, str]], period: Optional[str]) -> tuple[datetime, datetime, Optional[str]]:
    if explicit_day:
        start, end, label = explicit_day
        return start, end, label
    start = now + timedelta(minutes=30)
    if period == "evening":
        end = now + timedelta(days=5)
    else:
        end = now + timedelta(days=4)
    return start, end, None


def _slot_matches_period(slot_start: datetime, period: Optional[str]) -> bool:
    hour = slot_start.hour
    if period == "morning":
        return 9 <= hour < 13
    if period == "afternoon":
        return 13 <= hour < 17
    if period == "evening":
        return 17 <= hour < 22
    return True


def _slot_matches_time(slot_start: datetime, explicit_time: Optional[tuple[int, int]]) -> bool:
    if explicit_time is None:
        return True
    hour, minute = explicit_time
    target_minutes = hour * 60 + minute
    slot_minutes = slot_start.hour * 60 + slot_start.minute
    return abs(slot_minutes - target_minutes) <= 30


def _serialize_slots(slots: list, *, branch_id: Optional[int]) -> list[dict]:
    return [
        {
            "start_at": slot.start_at.isoformat(),
            "end_at": slot.end_at.isoformat(),
            "staff_id": slot.staff_id,
            "branch_id": branch_id,
        }
        for slot in slots
    ]


def _parse_serialized_slot(item: dict) -> Optional[dict]:
    try:
        return {
            "start_at": datetime.fromisoformat(item["start_at"]),
            "end_at": datetime.fromisoformat(item["end_at"]),
            "staff_id": item.get("staff_id"),
            "branch_id": item.get("branch_id"),
        }
    except Exception:
        return None


def _format_slot_label(slot_start: datetime, staff_name: Optional[str]) -> str:
    date_part = f"{slot_start.day} {MONTH_NAMES[slot_start.month]}"
    time_part = slot_start.strftime("%H:%M")
    if staff_name:
        return f"{date_part} в {time_part} — {staff_name}"
    return f"{date_part} в {time_part}"


def _select_offered_slot(text: str, offered_slots: list[dict]) -> Optional[dict]:
    if not offered_slots:
        return None
    lower = text.lower()
    if any(word in lower for word in ["перв", "вариант 1", "1"]):
        return offered_slots[0]
    if len(offered_slots) > 1 and any(word in lower for word in ["втор", "вариант 2", "2"]):
        return offered_slots[1]
    if len(offered_slots) > 2 and any(word in lower for word in ["трет", "вариант 3", "3"]):
        return offered_slots[2]
    explicit_time = _extract_explicit_time(text)
    if explicit_time:
        hour, minute = explicit_time
        target = hour * 60 + minute
        for slot in offered_slots:
            parsed = _parse_serialized_slot(slot)
            if parsed is None:
                continue
            slot_value = parsed["start_at"].hour * 60 + parsed["start_at"].minute
            if abs(slot_value - target) <= 30:
                return slot
    if _is_affirmative(text):
        return offered_slots[0]
    return None


def _offer_slots(
    db: Session,
    *,
    client: Client,
    service: Service,
    message_text: str,
    state: dict,
    staff_map: dict[int, StaffMember],
) -> AIRouterOutput:
    now = datetime.now().replace(second=0, microsecond=0)
    requested_day = _extract_requested_day(message_text, now)
    requested_period = _extract_requested_period(message_text) or state.get("requested_period")
    explicit_time = _extract_explicit_time(message_text)
    branch_id = _resolve_branch_id(db, client, staff_map)
    date_from, date_to, requested_day_label = _day_window(now, requested_day, requested_period)
    slots = list_slots(
        db,
        service_id=service.id,
        date_from=date_from,
        date_to=date_to,
        branch_id=branch_id,
        staff_id=client.preferred_staff_id,
    )
    filtered = [
        slot
        for slot in slots
        if _slot_matches_period(slot.start_at, requested_period) and _slot_matches_time(slot.start_at, explicit_time)
    ]
    if not filtered and (requested_day or requested_period or explicit_time):
        filtered = slots

    if not filtered:
        return _reply(
            intent="booking",
            risk_level="low",
            messages=[
                "По этой услуге в запрошенное время свободных окон прямо сейчас не вижу.",
                "Могу подобрать ближайшие варианты на другой день или другое время — напишите, как Вам удобнее.",
            ],
            next_action="request_time_preference",
            state_patch={
                "selected_service_id": service.id,
                "requested_day_text": requested_day_label,
                "requested_period": requested_period,
                "offered_slots": [],
                "last_ai_action": "request_time_preference",
            },
            status_patch={
                "client_status": ClientStatus.BOOKING_IN_PROGRESS.value,
                "dialog_status": DialogStatus.ACTIVE.value,
                "lead_stage": LeadStage.SERVICE_SELECTED.value,
                "lead_service_id": service.id,
            },
        )

    shortlisted = filtered[:3]
    slot_lines = []
    for index, slot in enumerate(shortlisted, start=1):
        staff_name = staff_map.get(slot.staff_id).full_name if slot.staff_id in staff_map else None
        slot_lines.append(f"{index}. {_format_slot_label(slot.start_at, staff_name)}")
    lead_message = f"{_emoji('calendar')} По услуге «{service.name}» могу предложить:"
    message = (
        f"{lead_message}\n"
        f"{chr(10).join(slot_lines)}\n\n"
        "Напишите номер варианта, удобное время или просто «да», и я зафиксирую первый свободный слот."
    )
    return _reply(
        intent="booking",
        risk_level="low",
        messages=[message],
        next_action="offer_slots",
        state_patch={
            "selected_service_id": service.id,
            "requested_day_text": requested_day_label or state.get("requested_day_text"),
            "requested_period": requested_period,
            "offered_slots": _serialize_slots(shortlisted, branch_id=branch_id),
            "last_ai_action": "offer_slots",
        },
        status_patch={
            "client_status": ClientStatus.BOOKING_IN_PROGRESS.value,
            "dialog_status": DialogStatus.WAITING_SLOT_SELECTION.value,
            "lead_stage": LeadStage.SERVICE_SELECTED.value,
            "lead_service_id": service.id,
        },
    )


def _service_follow_up(service: Service, state: dict, text: str) -> AIRouterOutput:
    if _is_affirmative(text):
        prompt = "Подберу ближайшие окна. Если есть пожелание по дню или времени, напишите его сразу."
    else:
        prompt = "Если удобно, сразу подберу 2-3 ближайших окна. Можно написать день или диапазон времени, например: «завтра вечером»."
    return _reply(
        intent="service_info",
        risk_level="low",
        messages=[f"{_service_summary(service)} {prompt}"],
        next_action="request_time_preference",
        state_patch={
            "selected_service_id": service.id,
            "offered_slots": [],
            "last_ai_action": "service_selected",
        },
        status_patch={
            "client_status": ClientStatus.INTERESTED.value,
            "dialog_status": DialogStatus.ACTIVE.value,
            "lead_stage": LeadStage.SERVICE_SELECTED.value,
            "lead_service_id": service.id,
        },
    )


def _continue_after_tone_repair(service: Optional[Service], state: dict) -> AIRouterOutput:
    if service and state.get("offered_slots"):
        return _reply(
            intent="tone_repair",
            risk_level="low",
            messages=[
                "Поняла Вас. Буду общаться на Вы, коротко и по делу. Чтобы не тянуть, могу сразу зафиксировать первый вариант из предложенных окон или подобрать другие."
            ],
            next_action="offer_slots",
            state_patch={"last_ai_action": "tone_repair"},
        )
    if service:
        return _reply(
            intent="tone_repair",
            risk_level="low",
            messages=[f"Поняла Вас. Буду общаться на Вы и без лишнего. {_service_summary(service)} Если удобно, сразу предложу ближайшие окна."],
            next_action="request_time_preference",
            state_patch={"selected_service_id": service.id, "last_ai_action": "tone_repair"},
        )
    return _reply(
        intent="tone_repair",
        risk_level="low",
        messages=["Поняла Вас. Буду общаться на Вы, спокойно и по делу. Напишите, пожалуйста, какая услуга нужна, и я сразу помогу с записью."],
        next_action="await_question",
        state_patch={"last_ai_action": "tone_repair"},
    )


def _unknown_flow(state: dict) -> AIRouterOutput:
    if state.get("selected_service_id"):
        return _reply(
            intent="unknown",
            risk_level="low",
            messages=["Чтобы двинуться дальше, подскажите, пожалуйста, удобнее сегодня, завтра или в другой день. Можно сразу написать и время, например: «завтра после 18:00»."],
            next_action="request_time_preference",
            state_patch={"last_ai_action": "request_time_preference"},
        )
    return _reply(
        intent="unknown",
        risk_level="low",
        messages=["С удовольствием помогу. Подскажите, пожалуйста, какая услуга Вас интересует или на что хотите записаться."],
        next_action="ask_clarification",
        state_patch={"last_ai_action": "ask_clarification"},
    )


def _break_loop(previous_state: dict, services: list[Service]) -> AIRouterOutput:
    current_service = _current_service(previous_state, services)
    if current_service and previous_state.get("offered_slots"):
        return _reply(
            intent="booking",
            risk_level="low",
            messages=["Чтобы не повторяться: могу сразу зафиксировать первый предложенный слот или подобрать другие варианты. Напишите «да» или новый день/время."],
            next_action="offer_slots",
            state_patch={"last_ai_action": "offer_slots"},
        )
    if current_service:
        return _reply(
            intent="booking",
            risk_level="low",
            messages=["Чтобы не тянуть, могу сразу предложить ближайшие окна. Напишите, пожалуйста, «да» или удобный день и время."],
            next_action="request_time_preference",
            state_patch={"selected_service_id": current_service.id, "last_ai_action": "request_time_preference"},
        )
    return _reply(
        intent="unknown",
        risk_level="low",
        messages=["Давайте коротко и по делу: напишите, пожалуйста, какая услуга нужна, и я сразу предложу ближайшие варианты."],
        next_action="ask_clarification",
        state_patch={"last_ai_action": "ask_clarification"},
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

    state = _state(dialog)
    intent = _detect_intent(message_text)
    services = _load_active_services(db)
    staff_map = _load_staff_map(db)
    knowledge_items = _simple_knowledge_search(db, message_text, intent)
    current_service = _current_service(state, services)
    matched_services = _match_services(message_text, services)
    selected_service = matched_services[0] if matched_services else current_service

    if _risk_level(message_text) == "high":
        return _reply(
            intent=intent,
            risk_level="high",
            messages=["Поняла Вас. Подключаю администратора, чтобы помочь аккуратно и по делу."],
            next_action="handoff_to_human",
            should_escalate=True,
            state_patch={"last_ai_action": "handoff_to_human"},
        )

    offered_slots = state.get("offered_slots", [])
    if offered_slots:
        if _is_negative(message_text):
            return _reply(
                intent="booking",
                risk_level="low",
                messages=["Хорошо, тогда подберу другой вариант. Напишите, пожалуйста, какой день или время Вам удобнее."],
                next_action="request_time_preference",
                state_patch={
                    "offered_slots": [],
                    "last_ai_action": "request_time_preference",
                },
                status_patch={
                    "client_status": ClientStatus.BOOKING_IN_PROGRESS.value,
                    "dialog_status": DialogStatus.ACTIVE.value,
                },
            )
        chosen_slot = _select_offered_slot(message_text, offered_slots)
        if chosen_slot:
            slot = _parse_serialized_slot(chosen_slot)
            if slot:
                return _reply(
                    intent="booking",
                    risk_level="low",
                    messages=[],
                    next_action="book_slot",
                    state_patch={"last_ai_action": "book_slot"},
                    extracted={
                        "selected_slot": chosen_slot,
                        "selected_service_id": (selected_service.id if selected_service else state.get("selected_service_id")),
                    },
                )

    if intent == "tone_repair":
        return _continue_after_tone_repair(selected_service, state)

    if intent == "cancel":
        return _reply(
            intent="cancel",
            risk_level="medium",
            messages=["Помогу с отменой. Напишите, пожалуйста, на какой день и время была запись, чтобы я всё проверила и передала администратору без ошибки."],
            next_action="request_cancel_details",
            state_patch={"last_ai_action": "request_cancel_details"},
        )

    if intent == "reschedule":
        return _reply(
            intent="reschedule",
            risk_level="medium",
            messages=["Помогу с переносом. Напишите, пожалуйста, какой день и время Вам удобнее, и я предложу ближайшие окна."],
            next_action="request_new_slot",
            state_patch={"last_ai_action": "request_new_slot"},
        )

    if intent == "service_info" and not matched_services and _is_catalog_question(message_text):
        return _reply(
            intent="service_info",
            risk_level="low",
            messages=[_catalog_message(services)],
            next_action="clarify_service",
            state_patch={"last_ai_action": "list_services"},
        )

    if selected_service:
        wants_slots = (
            intent in {"booking", "price"}
            or _is_affirmative(message_text)
            or _extract_requested_day(message_text, datetime.now()) is not None
            or _extract_requested_period(message_text) is not None
            or _extract_explicit_time(message_text) is not None
        )
        if wants_slots and intent != "price":
            result = _offer_slots(
                db,
                client=client,
                service=selected_service,
                message_text=message_text,
                state=state,
                staff_map=staff_map,
            )
        elif intent == "price":
            result = _reply(
                intent="price",
                risk_level="low",
                messages=[f"{_service_summary(selected_service)} Если удобно, после этого сразу предложу ближайшие окна."],
                next_action="offer_booking",
                state_patch={
                    "selected_service_id": selected_service.id,
                    "last_ai_action": "service_selected",
                },
                status_patch={
                    "client_status": ClientStatus.INTERESTED.value,
                    "lead_stage": LeadStage.SERVICE_SELECTED.value,
                    "lead_service_id": selected_service.id,
                },
            )
        else:
            result = _service_follow_up(selected_service, state, message_text)
    elif intent == "greeting":
        result = _reply(
            intent="greeting",
            risk_level="low",
            messages=[f"{_emoji('smile')} Здравствуйте. Помогу с услугами, стоимостью и записью. Если подскажете, что хотите сделать, я сразу предложу подходящий вариант."],
            next_action="await_question",
            state_patch={"last_ai_action": "await_question"},
        )
    else:
        fallback = _unknown_flow(state)
        knowledge_facts = _knowledge_facts(knowledge_items)
        input_payload = AIRouterInput(
            client={"id": client.id, "name": client.full_name, "status": client.status, "tags": [tag.tag for tag in client.tags]},
            dialog={
                "id": dialog.id,
                "mode": dialog.mode,
                "history": [{"role": msg.sender_type, "text": msg.text_content or ""} for msg in dialog.messages[-8:]],
                "ai_state": state,
            },
            message={"text": message_text, "content_type": content_type},
            context=context,
            rules={
                "medical_sensitive": True,
                "formal_voice": True,
                "address_user_as": "Вы",
                "allow_custom_emoji_markup": False,
                "max_message_len": settings.max_ai_message_len,
            },
        )
        service_catalog = [
            {
                "name": service.name,
                "duration_min": service.duration_min,
                "price": _format_price_band(service),
            }
            for service in services[:8]
        ]
        prompt = (
            "You are a Russian-speaking salon receptionist inside Telegram.\n"
            "Return structured JSON only.\n"
            "Always address the user formally using 'Вы'. Never use slang, sarcasm, or rude mirroring.\n"
            "Knowledge facts are internal notes. Never quote them verbatim and never dump long paragraphs from them.\n"
            "First answer the user's actual question in a concise, helpful way. Then gently move to the next useful step.\n"
            "If the user asks about services, summarize categories or concise service facts instead of policies or address.\n"
            "Usually return one short message. Use two messages only if the second is a separate CTA.\n"
            "Do not use plain emoji characters.\n"
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

    last_reply_hash = state.get("last_reply_hash")
    current_hash = _hash_messages(result.reply.messages) if result.reply.messages else ""
    if current_hash and current_hash == last_reply_hash:
        result = _break_loop(state, services)
    return result
