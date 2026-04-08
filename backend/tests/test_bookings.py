from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.db.session import SessionLocal
from app.models import Branch, Client, Service, StaffMember


def seed_catalog():
    with SessionLocal() as db:
        branch = Branch(name="Центр", timezone="Europe/Moscow", is_active=True)
        service = Service(name="Маникюр", duration_min=60, is_active=True)
        db.add_all([branch, service])
        db.flush()
        staff = StaffMember(full_name="Анна", branch_id=branch.id, is_active=True)
        client_one = Client(telegram_user_id=5001, full_name="Мария", status="new")
        client_two = Client(telegram_user_id=5002, full_name="Ольга", status="new")
        db.add_all([staff, client_one, client_two])
        db.commit()
        return {
            "branch_id": branch.id,
            "service_id": service.id,
            "staff_id": staff.id,
            "client_one_id": client_one.id,
            "client_two_id": client_two.id,
        }


def test_booking_conflict_returns_400(client, auth_header):
    ids = seed_catalog()
    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) + timedelta(days=1)

    day_response = client.post(
        f"/api/schedule/staff/{ids['staff_id']}/day",
        headers=auth_header,
        json={
            "start_at": start.isoformat(),
            "end_at": (start + timedelta(hours=8)).isoformat(),
            "is_available": True,
        },
    )
    assert day_response.status_code == 200

    first_booking = client.post(
        "/api/bookings",
        headers=auth_header,
        json={
            "client_id": ids["client_one_id"],
            "service_id": ids["service_id"],
            "staff_id": ids["staff_id"],
            "branch_id": ids["branch_id"],
            "start_at": start.isoformat(),
            "comment": "Первичная запись",
        },
    )
    assert first_booking.status_code == 200

    second_booking = client.post(
        "/api/bookings",
        headers=auth_header,
        json={
            "client_id": ids["client_two_id"],
            "service_id": ids["service_id"],
            "staff_id": ids["staff_id"],
            "branch_id": ids["branch_id"],
            "start_at": start.isoformat(),
            "comment": "Конфликт",
        },
    )
    assert second_booking.status_code == 400
    assert second_booking.json()["detail"] == "Selected slot is already busy"
