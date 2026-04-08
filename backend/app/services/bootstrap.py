from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Role


DEFAULT_ROLES = [
    ("owner", "Owner"),
    ("admin", "Admin"),
    ("manager", "Manager"),
    ("observer", "Observer"),
]


def ensure_default_roles(db: Session) -> None:
    existing_codes = set(db.scalars(select(Role.code)).all())
    created = False
    for code, name in DEFAULT_ROLES:
        if code not in existing_codes:
            db.add(Role(code=code, name=name, permissions_json={"scope": code}))
            created = True
    if created:
        db.commit()

