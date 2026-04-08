from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Booking, Client, Dialog, ForumTopic, Lead, Message, Notification
from app.schemas.telegram import AIRouterOutput, AIRouterReply
from app.services.ai_dispatcher import _render_outbound_parts


def test_business_webhook_creates_client_dialog_and_ai_reply(client):
    response = client.post(
        "/webhooks/telegram",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json={
            "update_id": 1,
            "business_message": {
                "message_id": 10,
                "business_connection_id": "bc-1",
                "chat": {"id": 9001},
                "from": {"id": 777, "first_name": "Мария", "username": "mariax"},
                "text": "Здравствуйте, хочу записаться на маникюр",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["duplicate"] is False

    with SessionLocal() as db:
        client_row = db.scalar(select(Client).where(Client.telegram_user_id == 777))
        dialog = db.scalar(select(Dialog).where(Dialog.client_id == client_row.id))
        topic = db.scalar(select(ForumTopic).where(ForumTopic.client_id == client_row.id))
        messages = db.scalars(select(Message).where(Message.dialog_id == dialog.id).order_by(Message.id.asc())).all()
        notification = db.scalar(select(Notification).where(Notification.dialog_id == dialog.id))

        assert client_row is not None
        assert dialog is not None
        assert topic is not None
        assert len(messages) >= 2
        assert messages[0].direction == "in"
        assert messages[1].direction == "out"
        assert notification is not None


def test_voice_payload_is_logged_and_processed(client):
    response = client.post(
        "/webhooks/telegram",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json={
            "update_id": 2,
            "business_message": {
                "message_id": 11,
                "business_connection_id": "bc-1",
                "chat": {"id": 9002},
                "from": {"id": 778, "first_name": "Ольга", "username": "olga"},
                "voice": {"file_id": "voice-1", "transcript": "Сколько стоит маникюр и есть ли окно завтра"},
            },
        },
    )

    assert response.status_code == 200
    with SessionLocal() as db:
        client_row = db.scalar(select(Client).where(Client.telegram_user_id == 778))
        dialog = db.scalar(select(Dialog).where(Dialog.client_id == client_row.id))
        messages = db.scalars(select(Message).where(Message.dialog_id == dialog.id).order_by(Message.id.asc())).all()
        assert messages[0].content_type == "voice"
        assert "маникюр" in (messages[0].text_content or "").lower()
        assert any(message.direction == "out" for message in messages)


def test_service_question_uses_catalog_instead_of_location_dump(client):
    response = client.post(
        "/webhooks/telegram",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json={
            "update_id": 3,
            "business_message": {
                "message_id": 12,
                "business_connection_id": "bc-1",
                "chat": {"id": 9003},
                "from": {"id": 779, "first_name": "Ирина", "username": "irina"},
                "text": "Привет, какие услуги есть?",
            },
        },
    )

    assert response.status_code == 200
    with SessionLocal() as db:
        client_row = db.scalar(select(Client).where(Client.telegram_user_id == 779))
        dialog = db.scalar(select(Dialog).where(Dialog.client_id == client_row.id))
        outbound = db.scalars(
            select(Message).where(Message.dialog_id == dialog.id, Message.direction == "out").order_by(Message.id.asc())
        ).all()

        assert outbound
        reply_text = "\n".join(filter(None, (message.text_content for message in outbound))).lower()
        assert "маникюр" in reply_text
        assert "педикюр" in reply_text
        assert "аптекарск" not in reply_text
        assert "хочешь" not in reply_text


def test_service_question_with_swearing_still_returns_catalog(client):
    response = client.post(
        "/webhooks/telegram",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json={
            "update_id": 4,
            "business_message": {
                "message_id": 13,
                "business_connection_id": "bc-1",
                "chat": {"id": 9004},
                "from": {"id": 782, "first_name": "Лена", "username": "lena"},
                "text": "какие есть услуги блять",
            },
        },
    )

    assert response.status_code == 200
    with SessionLocal() as db:
        client_row = db.scalar(select(Client).where(Client.telegram_user_id == 782))
        dialog = db.scalar(select(Dialog).where(Dialog.client_id == client_row.id))
        outbound = db.scalars(
            select(Message).where(Message.dialog_id == dialog.id, Message.direction == "out").order_by(Message.id.asc())
        ).all()

        assert outbound
        reply_text = "\n".join(filter(None, (message.text_content for message in outbound))).lower()
        assert "маникюр" in reply_text
        assert "педикюр" in reply_text
        assert "буду общаться на вы" not in reply_text


def test_booking_flow_offers_slots_and_creates_booking(client):
    updates = [
        {
            "update_id": 10,
            "business_message": {
                "message_id": 20,
                "business_connection_id": "bc-2",
                "chat": {"id": 9100},
                "from": {"id": 780, "first_name": "Анна", "username": "anna"},
                "text": "Маникюр",
            },
        },
        {
            "update_id": 11,
            "business_message": {
                "message_id": 21,
                "business_connection_id": "bc-2",
                "chat": {"id": 9100},
                "from": {"id": 780, "first_name": "Анна", "username": "anna"},
                "text": "давайте",
            },
        },
        {
            "update_id": 12,
            "business_message": {
                "message_id": 22,
                "business_connection_id": "bc-2",
                "chat": {"id": 9100},
                "from": {"id": 780, "first_name": "Анна", "username": "anna"},
                "text": "да",
            },
        },
    ]

    for update in updates:
        response = client.post("/webhooks/telegram", headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"}, json=update)
        assert response.status_code == 200

    with SessionLocal() as db:
        client_row = db.scalar(select(Client).where(Client.telegram_user_id == 780))
        dialog = db.scalar(select(Dialog).where(Dialog.client_id == client_row.id))
        lead = db.scalar(select(Lead).where(Lead.client_id == client_row.id))
        booking = db.scalar(select(Booking).where(Booking.client_id == client_row.id))
        outbound = db.scalars(
            select(Message).where(Message.dialog_id == dialog.id, Message.direction == "out").order_by(Message.id.asc())
        ).all()

        assert booking is not None
        assert client_row.status == "booked"
        assert dialog.status == "booked"
        assert lead is not None and lead.stage == "booked"
        assert any("запись зафиксировала" in (message.text_content or "").lower() for message in outbound)


def test_rude_client_message_does_not_break_tone(client):
    first = client.post(
        "/webhooks/telegram",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json={
            "update_id": 40,
            "business_message": {
                "message_id": 40,
                "business_connection_id": "bc-4",
                "chat": {"id": 9300},
                "from": {"id": 781, "first_name": "Нина", "username": "nina"},
                "text": "какие услуги есть",
            },
        },
    )
    second = client.post(
        "/webhooks/telegram",
        headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
        json={
            "update_id": 41,
            "business_message": {
                "message_id": 41,
                "business_connection_id": "bc-4",
                "chat": {"id": 9300},
                "from": {"id": 781, "first_name": "Нина", "username": "nina"},
                "text": "ты че сука так общаешься",
            },
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200

    with SessionLocal() as db:
        client_row = db.scalar(select(Client).where(Client.telegram_user_id == 781))
        dialog = db.scalar(select(Dialog).where(Dialog.client_id == client_row.id))
        outbound = db.scalars(
            select(Message).where(Message.dialog_id == dialog.id, Message.direction == "out").order_by(Message.id.asc())
        ).all()
        reply_text = "\n".join(filter(None, (message.text_content for message in outbound))).lower()

        assert "сука" not in reply_text
        assert "на вы" in reply_text or "буду общаться на вы" in reply_text


def test_outbound_messages_are_joined_and_html_safe():
    ai_output = AIRouterOutput(
        decision="reply",
        intent="service_info",
        risk_level="low",
        should_escalate=False,
        reply=AIRouterReply(
            split=False,
            messages=[
                '<tg-emoji emoji-id="5870764288364252592">🙂</tg-emoji> Подберу услугу',
                "Цена < 5000 & можно сегодня",
            ],
        ),
        extracted_entities={},
        next_action="offer_booking",
    )

    parts = _render_outbound_parts(ai_output)

    assert len(parts) == 1
    assert '<tg-emoji emoji-id="5870764288364252592">🙂</tg-emoji>' in parts[0]
    assert "&lt; 5000 &amp; можно сегодня" in parts[0]
