from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import AppSettings, DbSession, get_current_user
from app.core.security import AuthError
from app.models import User
from app.schemas.auth import AdminSessionInitRequest, AdminSessionInitResponse, AuthenticatedUser
from app.services.admin_auth import ensure_admin_session

router = APIRouter()


@router.post("/session/init", response_model=AdminSessionInitResponse)
def init_session(payload: AdminSessionInitRequest, db: DbSession, settings: AppSettings) -> AdminSessionInitResponse:
    try:
        response = ensure_admin_session(db, telegram_user_id=payload.telegram_user_id, init_data=payload.init_data, settings=settings)
        db.commit()
        return response
    except AuthError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.get("/me", response_model=AuthenticatedUser)
def me(current_user: User = Depends(get_current_user)) -> AuthenticatedUser:
    role_code = current_user.role.code if current_user.role else "admin"
    return AuthenticatedUser(id=current_user.id, name=current_user.full_name, role=role_code)
