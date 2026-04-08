from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, status

from app.api.deps import AppSettings, DbSession
from app.schemas.telegram import TelegramWebhookResponse
from app.services.webhook_handler import process_telegram_update

router = APIRouter()


@router.post("/telegram", response_model=TelegramWebhookResponse)
async def telegram_webhook(
    payload: Dict[str, Any],
    db: DbSession,
    settings: AppSettings,
    x_telegram_bot_api_secret_token: Optional[str] = Header(default=None),
) -> TelegramWebhookResponse:
    if x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Telegram secret")
    accepted = await process_telegram_update(db, settings=settings, update=payload)
    db.commit()
    return TelegramWebhookResponse(accepted=True, duplicate=not accepted)

