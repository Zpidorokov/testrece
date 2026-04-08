from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


TEST_DB_PATH = Path(__file__).resolve().parent / "test.db"
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["ALLOW_INSECURE_TELEGRAM_INIT_DATA"] = "true"
os.environ["ALLOWED_ADMIN_IDS"] = "1001,2002"
os.environ["TELEGRAM_WEBHOOK_SECRET"] = "test-secret"
os.environ["TELEGRAM_DRY_RUN"] = "true"
os.environ["OPENROUTER_DRY_RUN"] = "true"

from app.core.settings import get_settings

get_settings.cache_clear()

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.services.bootstrap import ensure_default_roles


@pytest.fixture(autouse=True)
def reset_db():
    engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        ensure_default_roles(db)
    yield
    engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture()
def auth_header(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/admin/session/init",
        json={"telegram_user_id": 1001, "init_data": "dev"},
    )
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}
