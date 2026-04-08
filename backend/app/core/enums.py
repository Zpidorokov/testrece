from __future__ import annotations

from enum import Enum


class DialogStatus(str, Enum):
    NEW = "new"
    ACTIVE = "active"
    WAITING_CLIENT = "waiting_client"
    WAITING_SLOT_SELECTION = "waiting_slot_selection"
    BOOKED = "booked"
    ESCALATED = "escalated"
    MANUAL = "manual"
    CLOSED = "closed"
    LOST = "lost"


class DialogMode(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"


class LeadStage(str, Enum):
    NEW = "new"
    QUALIFIED = "qualified"
    SERVICE_SELECTED = "service_selected"
    SLOT_SELECTED = "slot_selected"
    BOOKED = "booked"
    CANCELED = "canceled"
    LOST = "lost"
    RETURNING = "returning"


class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    RESCHEDULED = "rescheduled"
    CANCELED_BY_CLIENT = "canceled_by_client"
    CANCELED_BY_STAFF = "canceled_by_staff"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class ClientStatus(str, Enum):
    NEW = "new"
    CONSULTING = "consulting"
    INTERESTED = "interested"
    BOOKING_IN_PROGRESS = "booking_in_progress"
    BOOKED = "booked"
    LOYAL = "loyal"
    VIP = "vip"
    PROBLEMATIC = "problematic"
    ARCHIVED = "archived"


class MessageDirection(str, Enum):
    IN = "in"
    OUT = "out"


class SenderType(str, Enum):
    CLIENT = "client"
    AI = "ai"
    STAFF = "staff"
    SYSTEM = "system"


class ContentType(str, Enum):
    TEXT = "text"
    PHOTO = "photo"
    VOICE = "voice"
    FILE = "file"
    SYSTEM = "system"


class NotificationStatus(str, Enum):
    UNREAD = "unread"
    READ = "read"


class NotificationType(str, Enum):
    NEW_CLIENT = "new_client"
    NEW_BOOKING = "new_booking"
    RESCHEDULE = "reschedule"
    CANCELLATION = "cancellation"
    TAKEOVER = "takeover"
    HUMAN_REQUEST = "human_request"
    CONFLICT = "conflict"
    AI_ERROR = "ai_error"
    SCHEDULE_ERROR = "schedule_error"


class KnowledgeKind(str, Enum):
    SERVICE_INFO = "service_info"
    FAQ = "faq"
    POLICY = "policy"
    CONTRAINDICATION = "contraindication"
    PROMO = "promo"
    TONE_OF_VOICE = "tone_of_voice"
    OBJECTION_HANDLING = "objection_handling"
    ESCALATION_RULE = "escalation_rule"


class AirouterDecision(str, Enum):
    REPLY = "reply"
    ESCALATE = "escalate"
    ASK_CLARIFICATION = "ask_clarification"
    DRAFT_ONLY = "draft_only"
    NO_REPLY = "no_reply"

