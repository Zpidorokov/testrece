from __future__ import annotations


def test_admin_session_provisions_owner(client):
    response = client.post(
        "/api/admin/session/init",
        json={"telegram_user_id": 1001, "init_data": "dev"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["user"]["role"] == "owner"


def test_admin_session_rejects_unknown_user(client):
    response = client.post(
        "/api/admin/session/init",
        json={"telegram_user_id": 5555, "init_data": "dev"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "User is not in admin allowlist"

