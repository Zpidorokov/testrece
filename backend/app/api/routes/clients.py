from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import DbSession, get_current_user
from app.models import Client
from app.schemas.common import StatusMessage
from app.schemas.crm import ClientAddNoteRequest, ClientAddTagRequest, ClientCard, ClientSummary, ClientUpdateRequest
from app.services.crm import add_client_note, add_client_tags, fetch_client_card, list_clients

router = APIRouter(dependencies=[Depends(get_current_user)])


def _to_client_card(client: Client) -> ClientCard:
    last_dialog = max(client.dialogs, key=lambda dialog: dialog.updated_at, default=None) if client.dialogs else None
    return ClientCard(
        id=client.id,
        name=client.full_name,
        telegram_user_id=client.telegram_user_id,
        username=client.username,
        phone=client.phone,
        status=client.status,
        preferred_staff=client.preferred_staff_id,
        preferred_branch=client.preferred_branch_id,
        tags=[tag.tag for tag in client.tags],
        notes=list(client.note_items),
        last_dialog_at=last_dialog.updated_at if last_dialog else None,
    )


@router.get("", response_model=list[ClientSummary])
def get_clients(
    db: DbSession,
    status: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
) -> list[ClientSummary]:
    return [ClientSummary.model_validate(client) for client in list_clients(db, status=status, search=search)]


@router.get("/{client_id}", response_model=ClientCard)
def get_client(client_id: int, db: DbSession) -> ClientCard:
    client = fetch_client_card(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return _to_client_card(client)


@router.patch("/{client_id}", response_model=ClientCard)
def update_client(client_id: int, payload: ClientUpdateRequest, db: DbSession) -> ClientCard:
    client = fetch_client_card(db, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(client, field, value)
    db.add(client)
    db.commit()
    db.refresh(client)
    return _to_client_card(client)


@router.post("/{client_id}/tags", response_model=StatusMessage)
def add_tags(client_id: int, payload: ClientAddTagRequest, db: DbSession) -> StatusMessage:
    try:
        add_client_tags(db, client_id, payload.tags)
        db.commit()
        return StatusMessage(message="Tags added")
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{client_id}/note", response_model=StatusMessage)
def add_note(client_id: int, payload: ClientAddNoteRequest, db: DbSession) -> StatusMessage:
    try:
        add_client_note(db, client_id, payload.content, payload.author_user_id)
        db.commit()
        return StatusMessage(message="Note added")
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
