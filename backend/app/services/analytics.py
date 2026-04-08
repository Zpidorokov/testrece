from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import BookingStatus
from app.models import Booking, Client, Dialog, Lead, Message
from app.schemas.analytics import AnalyticsOverview, FunnelResponse, FunnelStep


def get_overview(db: Session) -> AnalyticsOverview:
    new_clients = db.scalar(select(func.count()).select_from(Client)) or 0
    dialogs_total = db.scalar(select(func.count()).select_from(Dialog)) or 0
    bookings_total = db.scalar(select(func.count()).select_from(Booking)) or 0
    canceled = db.scalar(
        select(func.count()).select_from(Booking).where(
            Booking.status.in_([BookingStatus.CANCELED_BY_CLIENT.value, BookingStatus.CANCELED_BY_STAFF.value])
        )
    ) or 0
    no_show = db.scalar(select(func.count()).select_from(Booking).where(Booking.status == BookingStatus.NO_SHOW.value)) or 0
    conversion = float(bookings_total / new_clients) if new_clients else 0.0
    cancel_rate = float(canceled / bookings_total) if bookings_total else 0.0
    no_show_rate = float(no_show / bookings_total) if bookings_total else 0.0

    dialogs = db.scalars(select(Dialog)).all()
    first_response_seconds = []
    for dialog in dialogs:
        messages = db.scalars(select(Message).where(Message.dialog_id == dialog.id).order_by(Message.created_at.asc())).all()
        inbound = next((msg for msg in messages if msg.direction == "in"), None)
        outbound = next((msg for msg in messages if msg.direction == "out"), None)
        if inbound and outbound:
            first_response_seconds.append((outbound.created_at - inbound.created_at).total_seconds())
    avg_first_response = sum(first_response_seconds) / len(first_response_seconds) if first_response_seconds else 0.0

    return AnalyticsOverview(
        new_clients=new_clients,
        dialogs_total=dialogs_total,
        bookings_total=bookings_total,
        conversion_to_booking=round(conversion, 2),
        avg_first_response_sec=round(avg_first_response, 2),
        cancel_rate=round(cancel_rate, 2),
        no_show_rate=round(no_show_rate, 2),
    )


def get_funnel(db: Session) -> FunnelResponse:
    counts = defaultdict(int)
    for stage in db.scalars(select(Lead.stage)).all():
        counts[stage] += 1
    ordered_stages = [
        "new",
        "qualified",
        "service_selected",
        "slot_selected",
        "booked",
        "returning",
        "lost",
    ]
    return FunnelResponse(steps=[FunnelStep(stage=stage, count=counts.get(stage, 0)) for stage in ordered_stages])

