from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class KnowledgeItemCreateRequest(BaseModel):
    kind: str
    title: str
    content: str
    metadata_json: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class KnowledgeItemUpdateRequest(BaseModel):
    kind: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class KnowledgeItemDTO(ORMModel):
    id: int
    kind: str
    title: str
    content: str
    metadata_json: dict[str, Any]
    is_active: bool
