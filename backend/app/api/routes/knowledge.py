from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.api.deps import DbSession, get_current_user
from app.models import KnowledgeItem
from app.schemas.common import StatusMessage
from app.schemas.knowledge import KnowledgeItemCreateRequest, KnowledgeItemDTO, KnowledgeItemUpdateRequest

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[KnowledgeItemDTO])
def get_knowledge(db: DbSession) -> list[KnowledgeItemDTO]:
    return [KnowledgeItemDTO.model_validate(item) for item in db.scalars(select(KnowledgeItem).order_by(KnowledgeItem.updated_at.desc())).all()]


@router.post("", response_model=KnowledgeItemDTO)
def create_knowledge(payload: KnowledgeItemCreateRequest, db: DbSession) -> KnowledgeItemDTO:
    item = KnowledgeItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return KnowledgeItemDTO.model_validate(item)


@router.patch("/{item_id}", response_model=KnowledgeItemDTO)
def update_knowledge(item_id: int, payload: KnowledgeItemUpdateRequest, db: DbSession) -> KnowledgeItemDTO:
    item = db.get(KnowledgeItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(item, field, value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return KnowledgeItemDTO.model_validate(item)


@router.delete("/{item_id}", response_model=StatusMessage)
def delete_knowledge(item_id: int, db: DbSession) -> StatusMessage:
    item = db.get(KnowledgeItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Knowledge item not found")
    db.delete(item)
    db.commit()
    return StatusMessage(message="Knowledge item deleted")
