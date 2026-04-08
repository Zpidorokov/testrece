from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PaginatedResponse(BaseModel):
    items: list[Any]
    total: int
    page: int = 1
    limit: int = 20


class StatusMessage(BaseModel):
    ok: bool = True
    message: str = "ok"


class TimestampedModel(ORMModel):
    created_at: datetime
    updated_at: Optional[datetime] = None

