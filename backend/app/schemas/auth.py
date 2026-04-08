from __future__ import annotations

from pydantic import BaseModel


class AdminSessionInitRequest(BaseModel):
    telegram_user_id: int
    init_data: str


class AuthenticatedUser(BaseModel):
    id: int
    name: str
    role: str


class AdminSessionInitResponse(BaseModel):
    ok: bool = True
    token: str
    user: AuthenticatedUser

