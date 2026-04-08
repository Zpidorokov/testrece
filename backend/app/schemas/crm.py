from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ClientTagDTO(ORMModel):
    id: int
    tag: str


class ClientNoteDTO(ORMModel):
    id: int
    author_user_id: Optional[int] = None
    content: str
    created_at: datetime


class ClientSummary(ORMModel):
    id: int
    telegram_user_id: int
    username: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime


class ClientCard(BaseModel):
    id: int
    name: Optional[str] = None
    telegram_user_id: int
    username: Optional[str] = None
    phone: Optional[str] = None
    status: str
    preferred_staff: Optional[int] = None
    preferred_branch: Optional[int] = None
    tags: list[str] = Field(default_factory=list)
    notes: list[ClientNoteDTO] = Field(default_factory=list)
    last_dialog_at: Optional[datetime] = None
    topic_link: Optional[str] = None


class ClientUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None
    preferred_branch_id: Optional[int] = None
    preferred_staff_id: Optional[int] = None
    notes: Optional[str] = None


class ClientAddTagRequest(BaseModel):
    tags: list[str]


class ClientAddNoteRequest(BaseModel):
    content: str
    author_user_id: Optional[int] = None


class MessageDTO(ORMModel):
    id: int
    telegram_message_id: Optional[int] = None
    direction: str
    sender_type: str
    content_type: str
    text_content: Optional[str] = None
    payload_json: dict[str, Any]
    created_at: datetime


class DialogSummary(BaseModel):
    id: int
    client_id: int
    client_name: Optional[str] = None
    status: str
    mode: str
    assigned_user_id: Optional[int] = None
    risk_flag: Optional[str] = None
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None


class DialogDetail(BaseModel):
    id: int
    client_id: int
    mode: str
    status: str
    assigned_user_id: Optional[int] = None
    forum_thread_id: Optional[int] = None
    messages: list[MessageDTO]
    ai_flags: dict[str, Any] = Field(default_factory=dict)


class TakeoverRequest(BaseModel):
    assigned_user_id: int
    reason: str


class SendDialogMessageRequest(BaseModel):
    text: str
    split_mode: str = "single"

