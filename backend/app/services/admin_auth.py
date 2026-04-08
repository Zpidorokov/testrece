from __future__ import annotations

from typing import Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import AuthError, create_access_token, validate_telegram_init_data
from app.core.settings import Settings
from app.models import Role, User
from app.schemas.auth import AdminSessionInitResponse, AuthenticatedUser


def ensure_admin_session(db: Session, *, telegram_user_id: int, init_data: str, settings: Settings) -> AdminSessionInitResponse:
    if settings.allow_insecure_telegram_init_data:
        telegram_user = {"id": telegram_user_id, "first_name": "Dev", "last_name": "Admin"}
    else:
        telegram_user = validate_telegram_init_data(init_data, settings.bot_token)
    if telegram_user["id"] != telegram_user_id:
        raise AuthError("Telegram user mismatch")

    user = db.scalar(select(User).where(User.telegram_user_id == telegram_user_id))
    if not user:
        if telegram_user_id not in settings.allowed_admin_ids:
            raise AuthError("User is not in admin allowlist")
        role = db.scalar(select(Role).where(Role.code == "owner"))
        if not role:
            raise AuthError("Default roles are not initialized")
        user = User(
            telegram_user_id=telegram_user_id,
            full_name=" ".join(filter(None, [telegram_user.get("first_name"), telegram_user.get("last_name")])) or "Owner",
            username=telegram_user.get("username"),
            role_id=role.id,
            is_active=True,
        )
        db.add(user)
        db.flush()

    if not user.is_active:
        raise AuthError("Inactive user")

    token = create_access_token(str(user.id), settings)
    role_code = user.role.code if user.role else (db.scalar(select(Role.code).where(Role.id == user.role_id)) or "admin")
    return AdminSessionInitResponse(
        token=token,
        user=AuthenticatedUser(id=user.id, name=user.full_name, role=role_code),
    )
