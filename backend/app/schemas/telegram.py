from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class TelegramWebhookResponse(BaseModel):
    ok: bool = True
    accepted: bool = True
    duplicate: bool = False


class TelegramTopicCreateResult(BaseModel):
    topic_id: Optional[int] = None
    message_thread_id: Optional[int] = None
    title: str


class AIRouterInput(BaseModel):
    client: dict[str, Any]
    dialog: dict[str, Any]
    message: dict[str, Any]
    context: dict[str, Any]
    rules: dict[str, Any]


class AIRouterReply(BaseModel):
    split: bool = False
    messages: list[str] = Field(default_factory=list)


class AIRouterOutput(BaseModel):
    decision: str
    intent: str
    risk_level: str
    should_escalate: bool
    reply: AIRouterReply
    extracted_entities: dict[str, Any] = Field(default_factory=dict)
    next_action: str = "none"

