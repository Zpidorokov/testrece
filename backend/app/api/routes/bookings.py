from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.api.deps import DbSession, get_current_user
from app.models import Booking, BookingStatusHistory
from app.schemas.booking import (
    BookingCancelRequest,
    BookingCreateRequest,
    BookingDTO,
    BookingHistoryDTO,
    BookingRescheduleRequest,
    BookingUpdateRequest,
    SlotDTO,
    StaffBlockRequest,
    StaffDayUpdateRequest,
)
from app.services.scheduling import block_staff_interval, cancel_booking, create_booking, list_slots, reschedule_booking, update_booking, update_staff_day

router = APIRouter(dependencies=[Depends(get_current_user)])
schedule_router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[BookingDTO])
def get_bookings(
    db: DbSession,
    date: Optional[datetime] = Query(default=None),
    branch_id: Optional[int] = Query(default=None),
    staff_id: Optional[int] = Query(default=None),
    status: Optional[str] = Query(default=None),
) -> list[BookingDTO]:
    stmt = select(Booking).order_by(Booking.start_at.asc())
    if date:
        stmt = stmt.where(Booking.start_at >= date)
    if branch_id:
        stmt = stmt.where(Booking.branch_id == branch_id)
    if staff_id:
        stmt = stmt.where(Booking.staff_id == staff_id)
    if status:
        stmt = stmt.where(Booking.status == status)
    return [BookingDTO.model_validate(item) for item in db.scalars(stmt).all()]


@router.post("", response_model=BookingDTO)
def create_booking_endpoint(payload: BookingCreateRequest, db: DbSession) -> BookingDTO:
    try:
        booking = create_booking(db, payload)
        db.commit()
        db.refresh(booking)
        return BookingDTO.model_validate(booking)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/{booking_id}", response_model=BookingDTO)
def update_booking_endpoint(booking_id: int, payload: BookingUpdateRequest, db: DbSession) -> BookingDTO:
    try:
        booking = update_booking(db, booking_id, payload)
        db.commit()
        db.refresh(booking)
        return BookingDTO.model_validate(booking)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{booking_id}/cancel", response_model=BookingDTO)
def cancel_booking_endpoint(booking_id: int, payload: BookingCancelRequest, db: DbSession) -> BookingDTO:
    try:
        booking = cancel_booking(db, booking_id, payload)
        db.commit()
        db.refresh(booking)
        return BookingDTO.model_validate(booking)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{booking_id}/reschedule", response_model=BookingDTO)
def reschedule_booking_endpoint(booking_id: int, payload: BookingRescheduleRequest, db: DbSession) -> BookingDTO:
    try:
        booking = reschedule_booking(db, booking_id, payload)
        db.commit()
        db.refresh(booking)
        return BookingDTO.model_validate(booking)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{booking_id}/history", response_model=list[BookingHistoryDTO])
def booking_history(booking_id: int, db: DbSession) -> list[BookingHistoryDTO]:
    stmt = select(BookingStatusHistory).where(BookingStatusHistory.booking_id == booking_id).order_by(BookingStatusHistory.changed_at.asc())
    return [BookingHistoryDTO.model_validate(item) for item in db.scalars(stmt).all()]


@schedule_router.get("/slots", response_model=list[SlotDTO])
def get_slots(
    db: DbSession,
    service_id: int,
    date_from: datetime,
    date_to: datetime,
    branch_id: Optional[int] = None,
    staff_id: Optional[int] = None,
) -> list[SlotDTO]:
    try:
        return list_slots(
            db,
            service_id=service_id,
            branch_id=branch_id,
            staff_id=staff_id,
            date_from=date_from,
            date_to=date_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@schedule_router.post("/staff/{staff_id}/day")
def update_staff_day_endpoint(staff_id: int, payload: StaffDayUpdateRequest, db: DbSession) -> dict:
    item = update_staff_day(db, staff_id, payload)
    db.commit()
    return {"ok": True, "id": item.id}


@schedule_router.post("/staff/{staff_id}/block")
def block_staff_endpoint(staff_id: int, payload: StaffBlockRequest, db: DbSession) -> dict:
    item = block_staff_interval(db, staff_id, payload)
    db.commit()
    return {"ok": True, "id": item.id}
