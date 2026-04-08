from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.deps import DbSession, get_current_user
from app.models import Branch, Service, StaffMember
from app.schemas.catalog import (
    BranchCreateRequest,
    BranchUpdateRequest,
    ServiceCreateRequest,
    ServiceUpdateRequest,
    StaffCreateRequest,
    StaffUpdateRequest,
)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/services")
def get_services(db: DbSession) -> list[dict]:
    return [
        {
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "duration_min": item.duration_min,
            "price_from": float(item.price_from) if item.price_from is not None else None,
            "price_to": float(item.price_to) if item.price_to is not None else None,
            "is_active": item.is_active,
        }
        for item in db.scalars(select(Service).order_by(Service.name.asc())).all()
    ]


@router.post("/services")
def create_service(payload: ServiceCreateRequest, db: DbSession) -> dict:
    item = Service(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "duration_min": item.duration_min,
        "price_from": float(item.price_from) if item.price_from is not None else None,
        "price_to": float(item.price_to) if item.price_to is not None else None,
        "is_active": item.is_active,
    }


@router.patch("/services/{service_id}")
def update_service(service_id: int, payload: ServiceUpdateRequest, db: DbSession) -> dict:
    item = db.get(Service, service_id)
    if not item:
        return {"ok": False, "message": "Service not found"}
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(item, field, value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"ok": True, "id": item.id}


@router.get("/staff")
def get_staff(db: DbSession) -> list[dict]:
    return [
        {
            "id": item.id,
            "full_name": item.full_name,
            "specialization": item.specialization,
            "branch_id": item.branch_id,
            "is_active": item.is_active,
        }
        for item in db.scalars(select(StaffMember).order_by(StaffMember.full_name.asc())).all()
    ]


@router.post("/staff")
def create_staff(payload: StaffCreateRequest, db: DbSession) -> dict:
    item = StaffMember(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"ok": True, "id": item.id}


@router.patch("/staff/{staff_id}")
def update_staff(staff_id: int, payload: StaffUpdateRequest, db: DbSession) -> dict:
    item = db.get(StaffMember, staff_id)
    if not item:
        return {"ok": False, "message": "Staff member not found"}
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(item, field, value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"ok": True, "id": item.id}


@router.get("/branches")
def get_branches(db: DbSession) -> list[dict]:
    return [
        {
            "id": item.id,
            "name": item.name,
            "address": item.address,
            "timezone": item.timezone,
            "is_active": item.is_active,
        }
        for item in db.scalars(select(Branch).order_by(Branch.name.asc())).all()
    ]


@router.post("/branches")
def create_branch(payload: BranchCreateRequest, db: DbSession) -> dict:
    item = Branch(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"ok": True, "id": item.id}


@router.patch("/branches/{branch_id}")
def update_branch(branch_id: int, payload: BranchUpdateRequest, db: DbSession) -> dict:
    item = db.get(Branch, branch_id)
    if not item:
        return {"ok": False, "message": "Branch not found"}
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(item, field, value)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"ok": True, "id": item.id}
