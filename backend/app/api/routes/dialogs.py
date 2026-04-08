from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import AppSettings, DbSession, get_current_user
from app.models import Dialog
from app.schemas.crm import DialogDetail, DialogSummary, SendDialogMessageRequest, TakeoverRequest
from app.services.ai_router import route_ai
from app.services.crm import get_dialog_detail, list_dialogs
from app.services.dialogs import return_dialog_to_auto, send_manual_message, takeover_dialog

router = APIRouter(dependencies=[Depends(get_current_user)])


def _summary(dialog: Dialog) -> DialogSummary:
    last_message = dialog.messages[-1] if dialog.messages else None
    return DialogSummary(
        id=dialog.id,
        client_id=dialog.client_id,
        client_name=dialog.client.full_name if dialog.client else None,
        status=dialog.status,
        mode=dialog.mode,
        assigned_user_id=dialog.assigned_user_id,
        risk_flag="manual" if dialog.mode == "manual" else None,
        last_message=last_message.text_content if last_message else None,
        last_message_at=last_message.created_at if last_message else None,
    )


def _detail(dialog: Dialog) -> DialogDetail:
    return DialogDetail(
        id=dialog.id,
        client_id=dialog.client_id,
        mode=dialog.mode,
        status=dialog.status,
        assigned_user_id=dialog.assigned_user_id,
        forum_thread_id=dialog.forum_thread_id,
        messages=list(dialog.messages),
        ai_flags={"can_auto_reply": dialog.mode == "auto"},
    )


@router.get("", response_model=list[DialogSummary])
def get_dialogs(db: DbSession) -> list[DialogSummary]:
    return [_summary(dialog) for dialog in list_dialogs(db)]


@router.get("/{dialog_id}", response_model=DialogDetail)
def get_dialog(dialog_id: int, db: DbSession) -> DialogDetail:
    dialog = get_dialog_detail(db, dialog_id)
    if not dialog:
        raise HTTPException(status_code=404, detail="Dialog not found")
    return _detail(dialog)


@router.post("/{dialog_id}/takeover", response_model=DialogDetail)
async def takeover(dialog_id: int, payload: TakeoverRequest, db: DbSession) -> DialogDetail:
    try:
        dialog = await takeover_dialog(db, dialog_id, payload)
        db.commit()
        return _detail(get_dialog_detail(db, dialog.id))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{dialog_id}/return-to-auto", response_model=DialogDetail)
def return_to_auto(dialog_id: int, db: DbSession) -> DialogDetail:
    try:
        dialog = return_dialog_to_auto(db, dialog_id)
        db.commit()
        return _detail(get_dialog_detail(db, dialog.id))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{dialog_id}/send-message", response_model=DialogDetail)
async def send_message(dialog_id: int, payload: SendDialogMessageRequest, db: DbSession, settings: AppSettings) -> DialogDetail:
    try:
        dialog = await send_manual_message(db, settings=settings, dialog_id=dialog_id, payload=payload)
        db.commit()
        return _detail(get_dialog_detail(db, dialog.id))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{dialog_id}/ai-draft")
async def ai_draft(dialog_id: int, db: DbSession, settings: AppSettings) -> dict:
    dialog = get_dialog_detail(db, dialog_id)
    if not dialog or not dialog.messages:
        raise HTTPException(status_code=404, detail="Dialog not found")
    inbound = next((message for message in reversed(dialog.messages) if message.direction == "in"), None)
    if not inbound:
        raise HTTPException(status_code=400, detail="No inbound messages for draft")
    ai_output = await route_ai(
        db,
        settings=settings,
        client=dialog.client,
        dialog=dialog,
        message_text=inbound.text_content or "",
        content_type=inbound.content_type,
        context={"draft_only": True},
    )
    return ai_output.model_dump()
