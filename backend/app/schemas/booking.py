from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import ORMModel


class BookingCreateRequest(BaseModel):
    client_id: int
    service_id: int
    staff_id: Optional[int] = None
    branch_id: Optional[int] = None
    start_at: datetime
    comment: Optional[str] = None
    created_by_user_id: Optional[int] = None


class BookingUpdateRequest(BaseModel):
    staff_id: Optional[int] = None
    branch_id: Optional[int] = None
    comment: Optional[str] = None
    status: Optional[str] = None


class BookingRescheduleRequest(BaseModel):
    start_at: datetime
    actor: str = "staff"


class BookingCancelRequest(BaseModel):
    actor: str = "staff"
    reason: Optional[str] = None


class BookingDTO(ORMModel):
    id: int
    client_id: int
    service_id: int
    staff_id: Optional[int] = None
    branch_id: Optional[int] = None
    start_at: datetime
    end_at: datetime
    status: str
    source: str
    comment: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class BookingHistoryDTO(ORMModel):
    id: int
    old_status: Optional[str] = None
    new_status: str
    changed_by: Optional[str] = None
    changed_at: datetime


class SlotDTO(BaseModel):
    start_at: datetime
    end_at: datetime
    staff_id: Optional[int] = None


class StaffDayUpdateRequest(BaseModel):
    start_at: datetime
    end_at: datetime
    is_available: bool = True


class StaffBlockRequest(BaseModel):
    start_at: datetime
    end_at: datetime

