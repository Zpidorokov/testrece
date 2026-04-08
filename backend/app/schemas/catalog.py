from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ServiceCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    duration_min: int
    price_from: Optional[float] = None
    price_to: Optional[float] = None
    is_active: bool = True


class ServiceUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration_min: Optional[int] = None
    price_from: Optional[float] = None
    price_to: Optional[float] = None
    is_active: Optional[bool] = None


class StaffCreateRequest(BaseModel):
    full_name: str
    specialization: Optional[str] = None
    branch_id: Optional[int] = None
    is_active: bool = True


class StaffUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    specialization: Optional[str] = None
    branch_id: Optional[int] = None
    is_active: Optional[bool] = None


class BranchCreateRequest(BaseModel):
    name: str
    address: Optional[str] = None
    timezone: str = "Europe/Moscow"
    is_active: bool = True


class BranchUpdateRequest(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None
