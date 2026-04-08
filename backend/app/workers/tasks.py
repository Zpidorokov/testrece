from __future__ import annotations

from app.workers.celery_app import celery_app


@celery_app.task(name="send_staff_notification")
def send_staff_notification(payload: dict) -> dict:
    return {"ok": True, "payload": payload}


@celery_app.task(name="create_forum_topic")
def create_forum_topic(payload: dict) -> dict:
    return {"ok": True, "payload": payload}


@celery_app.task(name="sync_topic_messages")
def sync_topic_messages(payload: dict) -> dict:
    return {"ok": True, "payload": payload}


@celery_app.task(name="generate_ai_reply")
def generate_ai_reply(payload: dict) -> dict:
    return {"ok": True, "payload": payload}


@celery_app.task(name="send_booking_reminder")
def send_booking_reminder(payload: dict) -> dict:
    return {"ok": True, "payload": payload}


@celery_app.task(name="send_followup_after_cancel")
def send_followup_after_cancel(payload: dict) -> dict:
    return {"ok": True, "payload": payload}


@celery_app.task(name="rebuild_knowledge_embeddings")
def rebuild_knowledge_embeddings(payload: dict) -> dict:
    return {"ok": True, "payload": payload}


@celery_app.task(name="daily_analytics_snapshot")
def daily_analytics_snapshot(payload: dict) -> dict:
    return {"ok": True, "payload": payload}
