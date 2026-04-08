from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.enums import BookingStatus
from app.models import Booking, BookingStatusHistory, Service, StaffMember, StaffSchedule
from app.schemas.booking import BookingCancelRequest, BookingCreateRequest, BookingRescheduleRequest, BookingUpdateRequest, SlotDTO, StaffBlockRequest, StaffDayUpdateRequest
from app.services.audit import log_audit_event


BOOKING_BUFFER_MINUTES = 15


def _booking_end(start_at: datetime, duration_min: int) -> datetime:
    return start_at + timedelta(minutes=duration_min)


def _booking_conflict_query(staff_id: Optional[int], start_at: datetime, end_at: datetime):
    conditions = [
        Booking.status.in_(
            [
                BookingStatus.PENDING.value,
                BookingStatus.CONFIRMED.value,
                BookingStatus.RESCHEDULED.value,
            ]
        ),
        Booking.start_at < end_at,
        Booking.end_at > start_at,
    ]
    if staff_id is not None:
        conditions.append(Booking.staff_id == staff_id)
    return select(Booking).where(and_(*conditions))


def list_slots(
    db: Session,
    *,
    service_id: int,
    date_from: datetime,
    date_to: datetime,
    branch_id: Optional[int] = None,
    staff_id: Optional[int] = None,
) -> List[SlotDTO]:
    service = db.get(Service, service_id)
    if not service:
        raise ValueError("Service not found")

    stmt = select(StaffSchedule).where(
        StaffSchedule.start_at <= date_to,
        StaffSchedule.end_at >= date_from,
        StaffSchedule.is_available.is_(True),
    )
    if staff_id is not None:
        stmt = stmt.where(StaffSchedule.staff_id == staff_id)
    schedules = list(db.scalars(stmt).all())
    slots: List[SlotDTO] = []
    for schedule in schedules:
        if branch_id is not None:
            staff = db.get(StaffMember, schedule.staff_id)
            if not staff or staff.branch_id != branch_id:
                continue

        cursor = max(schedule.start_at, date_from)
        end_boundary = min(schedule.end_at, date_to)
        while cursor + timedelta(minutes=service.duration_min) <= end_boundary:
            slot_end = _booking_end(cursor, service.duration_min)
            padded_start = cursor - timedelta(minutes=BOOKING_BUFFER_MINUTES)
            padded_end = slot_end + timedelta(minutes=BOOKING_BUFFER_MINUTES)
            conflict = db.scalar(_booking_conflict_query(schedule.staff_id, padded_start, padded_end))
            if not conflict:
                slots.append(SlotDTO(start_at=cursor, end_at=slot_end, staff_id=schedule.staff_id))
            cursor += timedelta(minutes=30)
    return slots


def create_booking(db: Session, payload: BookingCreateRequest) -> Booking:
    service = db.get(Service, payload.service_id)
    if not service:
        raise ValueError("Service not found")

    selected_staff_id = payload.staff_id
    if selected_staff_id is None:
        candidate_slots = list_slots(
            db,
            service_id=payload.service_id,
            branch_id=payload.branch_id,
            staff_id=None,
            date_from=payload.start_at,
            date_to=payload.start_at + timedelta(minutes=service.duration_min),
        )
        for slot in candidate_slots:
            if slot.start_at == payload.start_at:
                selected_staff_id = slot.staff_id
                break
    end_at = _booking_end(payload.start_at, service.duration_min)
    conflict = db.scalar(
        _booking_conflict_query(selected_staff_id, payload.start_at - timedelta(minutes=BOOKING_BUFFER_MINUTES), end_at + timedelta(minutes=BOOKING_BUFFER_MINUTES))
    )
    if conflict:
        raise ValueError("Selected slot is already busy")

    booking = Booking(
        client_id=payload.client_id,
        service_id=payload.service_id,
        staff_id=selected_staff_id,
        branch_id=payload.branch_id,
        start_at=payload.start_at,
        end_at=end_at,
        comment=payload.comment,
        created_by_user_id=payload.created_by_user_id,
        status=BookingStatus.PENDING.value,
        source="telegram",
    )
    db.add(booking)
    db.flush()
    db.add(
        BookingStatusHistory(
            booking_id=booking.id,
            old_status=None,
            new_status=BookingStatus.PENDING.value,
            changed_by="system",
        )
    )
    log_audit_event(
        db,
        actor_type="system",
        actor_id=None,
        action="booking_created",
        entity_type="booking",
        entity_id=str(booking.id),
        payload={"client_id": booking.client_id},
    )
    db.flush()
    return booking


def update_booking(db: Session, booking_id: int, payload: BookingUpdateRequest) -> Booking:
    booking = db.get(Booking, booking_id)
    if not booking:
        raise ValueError("Booking not found")
    for field in ("staff_id", "branch_id", "comment", "status"):
        value = getattr(payload, field)
        if value is not None:
            setattr(booking, field, value)
    db.add(booking)
    db.flush()
    return booking


def cancel_booking(db: Session, booking_id: int, payload: BookingCancelRequest) -> Booking:
    booking = db.get(Booking, booking_id)
    if not booking:
        raise ValueError("Booking not found")
    old_status = booking.status
    booking.status = BookingStatus.CANCELED_BY_CLIENT.value if payload.actor == "client" else BookingStatus.CANCELED_BY_STAFF.value
    db.add(booking)
    db.add(
        BookingStatusHistory(
            booking_id=booking.id,
            old_status=old_status,
            new_status=booking.status,
            changed_by=payload.actor,
        )
    )
    db.flush()
    return booking


def reschedule_booking(db: Session, booking_id: int, payload: BookingRescheduleRequest) -> Booking:
    booking = db.get(Booking, booking_id)
    if not booking:
        raise ValueError("Booking not found")
    service = db.get(Service, booking.service_id)
    if not service:
        raise ValueError("Service not found")

    new_end = _booking_end(payload.start_at, service.duration_min)
    conflict = db.scalar(
        select(Booking).where(
            Booking.id != booking.id,
            Booking.staff_id == booking.staff_id,
            Booking.status.in_(
                [
                    BookingStatus.PENDING.value,
                    BookingStatus.CONFIRMED.value,
                    BookingStatus.RESCHEDULED.value,
                ]
            ),
            Booking.start_at < new_end + timedelta(minutes=BOOKING_BUFFER_MINUTES),
            Booking.end_at > payload.start_at - timedelta(minutes=BOOKING_BUFFER_MINUTES),
        )
    )
    if conflict:
        raise ValueError("Selected slot is already busy")

    old_status = booking.status
    booking.start_at = payload.start_at
    booking.end_at = new_end
    booking.status = BookingStatus.RESCHEDULED.value
    db.add(booking)
    db.add(
        BookingStatusHistory(
            booking_id=booking.id,
            old_status=old_status,
            new_status=booking.status,
            changed_by=payload.actor,
        )
    )
    db.flush()
    return booking


def update_staff_day(db: Session, staff_id: int, payload: StaffDayUpdateRequest) -> StaffSchedule:
    item = StaffSchedule(
        staff_id=staff_id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        is_available=payload.is_available,
    )
    db.add(item)
    db.flush()
    return item


def block_staff_interval(db: Session, staff_id: int, payload: StaffBlockRequest) -> StaffSchedule:
    item = StaffSchedule(
        staff_id=staff_id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        is_available=False,
    )
    db.add(item)
    db.flush()
    return item

