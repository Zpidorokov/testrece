from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from urllib.parse import parse_qsl

from jose import JWTError, jwt

from app.core.settings import Settings


class AuthError(Exception):
    pass


def create_access_token(subject: str, settings: Settings) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> Dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise AuthError("Invalid access token") from exc


def validate_telegram_init_data(init_data: str, bot_token: str) -> Dict[str, Any]:
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise AuthError("Missing Telegram hash")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise AuthError("Invalid Telegram init data hash")

    user_raw = pairs.get("user")
    if not user_raw:
        raise AuthError("Missing Telegram user payload")

    user = json.loads(user_raw)
    auth_date = pairs.get("auth_date")
    if auth_date:
        age = datetime.now(timezone.utc) - datetime.fromtimestamp(int(auth_date), tz=timezone.utc)
        if age > timedelta(hours=24):
            raise AuthError("Telegram init data expired")

    return user

