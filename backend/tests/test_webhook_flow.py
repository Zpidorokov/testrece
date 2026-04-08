from __future__ import annotations

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models import Client, Dialog, ForumTopic, Message, Notification


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
