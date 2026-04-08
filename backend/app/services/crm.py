from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import ClientStatus, ContentType, DialogMode, DialogStatus, LeadStage, MessageDirection, SenderType
from app.models import Client, ClientNote, ClientTag, Dialog, ForumTopic, Lead, Message
from app.services.audit import log_audit_event


def get_or_create_client_from_telegram(db: Session, tg_user: Dict[str, Any]) -> Tuple[Client, bool]:
    telegram_user_id = tg_user["id"]
    client = db.scalar(select(Client).where(Client.telegram_user_id == telegram_user_id))
    created = False
    if not client:
        client = Client(
            telegram_user_id=telegram_user_id,
            username=tg_user.get("username"),
            full_name=" ".join(filter(None, [tg_user.get("first_name"), tg_user.get("last_name")])) or tg_user.get("username"),
            status=ClientStatus.NEW.value,
            source="telegram_business",
        )
        db.add(client)
        db.flush()
        db.add(Lead(client_id=client.id, source="telegram_business", stage=LeadStage.NEW.value))
        log_audit_event(
            db,
            actor_type="system",
            actor_id=None,
            action="client_created",
            entity_type="client",
            entity_id=str(client.id),
            payload={"telegram_user_id": telegram_user_id},
        )
        created = True
    else:
        client.username = tg_user.get("username") or client.username
        if not client.full_name:
            client.full_name = " ".join(filter(None, [tg_user.get("first_name"), tg_user.get("last_name")]))
    db.add(client)
    db.flush()
    return client, created


def get_or_create_dialog(
    db: Session,
    *,
    client: Client,
    chat_id: int,
    business_connection_id: Optional[str],
) -> Tuple[Dialog, bool]:
    stmt = (
        select(Dialog)
        .where(Dialog.client_id == client.id, Dialog.telegram_chat_id == chat_id)
        .order_by(desc(Dialog.created_at))
    )
    dialog = db.scalar(stmt)
    created = False
    if not dialog:
        dialog = Dialog(
            client_id=client.id,
            telegram_chat_id=chat_id,
            business_connection_id=business_connection_id,
            mode=DialogMode.AUTO.value,
            status=DialogStatus.NEW.value,
        )
        db.add(dialog)
        db.flush()
        log_audit_event(
            db,
            actor_type="system",
            actor_id=None,
            action="dialog_created",
            entity_type="dialog",
            entity_id=str(dialog.id),
            payload={"client_id": client.id},
        )
        created = True
    else:
        dialog.business_connection_id = business_connection_id or dialog.business_connection_id
        if dialog.status == DialogStatus.NEW.value:
            dialog.status = DialogStatus.ACTIVE.value
    db.add(dialog)
    db.flush()
    return dialog, created


def record_message(
    db: Session,
    *,
    dialog: Dialog,
    telegram_message_id: Optional[int],
    business_connection_id: Optional[str],
    direction: str,
    sender_type: str,
    content_type: str,
    text_content: Optional[str],
    payload_json: Optional[Dict[str, Any]] = None,
) -> Message:
    message = Message(
        dialog_id=dialog.id,
        telegram_message_id=telegram_message_id,
        business_connection_id=business_connection_id,
        direction=direction,
        sender_type=sender_type,
        content_type=content_type,
        text_content=text_content,
        payload_json=payload_json or {},
    )
    db.add(message)
    if dialog.mode == DialogMode.MANUAL.value:
        dialog.status = DialogStatus.MANUAL.value
    elif dialog.status not in {DialogStatus.WAITING_SLOT_SELECTION.value, DialogStatus.BOOKED.value}:
        dialog.status = DialogStatus.ACTIVE.value
    db.add(dialog)
    db.flush()
    return message


def add_client_tags(db: Session, client_id: int, tags: List[str]) -> List[ClientTag]:
    client = db.get(Client, client_id)
    if not client:
        raise ValueError("Client not found")
    created_tags = []
    existing = {tag.tag for tag in client.tags}
    for raw_tag in tags:
        tag = raw_tag.strip()
        if tag and tag not in existing:
            item = ClientTag(client_id=client_id, tag=tag)
            db.add(item)
            created_tags.append(item)
            existing.add(tag)
    db.flush()
    return created_tags


def add_client_note(db: Session, client_id: int, content: str, author_user_id: Optional[int]) -> ClientNote:
    note = ClientNote(client_id=client_id, content=content, author_user_id=author_user_id)
    db.add(note)
    db.flush()
    return note


def fetch_client_card(db: Session, client_id: int) -> Optional[Client]:
    stmt = (
        select(Client)
        .options(selectinload(Client.tags), selectinload(Client.note_items), selectinload(Client.dialogs))
        .where(Client.id == client_id)
    )
    return db.scalar(stmt)


def list_clients(db: Session, *, status: Optional[str] = None, search: Optional[str] = None) -> List[Client]:
    stmt = select(Client).order_by(desc(Client.updated_at))
    if status:
        stmt = stmt.where(Client.status == status)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where((Client.full_name.ilike(pattern)) | (Client.username.ilike(pattern)))
    return list(db.scalars(stmt).all())


def list_dialogs(db: Session) -> List[Dialog]:
    stmt = select(Dialog).options(selectinload(Dialog.messages), selectinload(Dialog.client)).order_by(desc(Dialog.updated_at))
    return list(db.scalars(stmt).all())


def get_dialog_detail(db: Session, dialog_id: int) -> Optional[Dialog]:
    stmt = (
        select(Dialog)
        .options(selectinload(Dialog.messages), selectinload(Dialog.client))
        .where(Dialog.id == dialog_id)
    )
    return db.scalar(stmt)


def get_or_create_topic_link(db: Session, client_id: int, title: str, chat_id: int, message_thread_id: int) -> ForumTopic:
    topic = db.scalar(select(ForumTopic).where(ForumTopic.client_id == client_id))
    if not topic:
        topic = ForumTopic(
            client_id=client_id,
            chat_id=chat_id,
            topic_id=message_thread_id,
            message_thread_id=message_thread_id,
            title=title,
        )
        db.add(topic)
        db.flush()
    return topic
