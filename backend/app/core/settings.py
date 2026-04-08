from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "BotReceptionist"
    environment: str = "development"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./botreceptionist.db"
    redis_url: str = "redis://localhost:6379/0"
    bot_token: str = "dev-bot-token"
    telegram_webhook_secret: str = "dev-secret"
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "openai/gpt-4.1-mini"
    staff_group_chat_id: int = -1001234567890
    admin_web_url: str = "http://localhost:3000"
    jwt_secret: str = "dev-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 12
    allowed_admin_ids_raw: str = Field(default="", alias="ALLOWED_ADMIN_IDS")
    allow_insecure_telegram_init_data: bool = False
    celery_task_always_eager: bool = True
    telegram_dry_run: bool = True
    openrouter_dry_run: bool = True
    max_ai_message_len: int = 350
    ai_reply_debounce_seconds: int = 4
    telegram_api_base_url: str = "https://api.telegram.org"

    @computed_field  # type: ignore[misc]
    @property
    def allowed_admin_ids(self) -> List[int]:
        if not self.allowed_admin_ids_raw.strip():
            return []
        values = []
        for chunk in self.allowed_admin_ids_raw.split(","):
            chunk = chunk.strip()
            if chunk:
                values.append(int(chunk))
        return values

    @computed_field  # type: ignore[misc]
    @property
    def telegram_bot_api_url(self) -> str:
        return f"{self.telegram_api_base_url}/bot{self.bot_token}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
