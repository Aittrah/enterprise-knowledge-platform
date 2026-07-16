from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.core.config import Settings
from app.core.security import decode_access_token

HR_TEXT = "Employees accrue twenty two annual leave days per year, earned monthly."


@pytest.fixture
def app_client(tmp_path: Path) -> TestClient:
    app = create_app(
        Settings(data_dir=tmp_path / "data", jwt_secret="test-secret-" + "x" * 24)
    )
    return TestClient(app)


@pytest.fixture
def auth_client(app_client: TestClient) -> TestClient:
    token = app_client.post(
        "/api/auth/register",
        json={"email": "owner@ekip.dev", "password": "longenough", "name": "Owner"},
    ).json()["access_token"]
    app_client.headers["Authorization"] = f"Bearer {token}"
    return app_client


def _upload(client: TestClient) -> None:
    response = client.post(
        "/api/documents/upload",
        files={"file": ("leave.txt", HR_TEXT.encode(), "text/plain")},
    )
    assert response.status_code == 202, response.text


# --- key lifecycle ------------------------------------------------------------------


def test_create_widget_key_returns_token_once(auth_client: TestClient):
    body = auth_client.post("/api/widget-keys", json={"label": "Marketing site"}).json()
    assert body["label"] == "Marketing site"
    assert body["revoked"] is False
    assert body["token"]  # shown once

    payload = decode_access_token(body["token"], "test-secret-" + "x" * 24)
    assert payload["scope"] == "widget"
    assert payload["kid"] == body["kid"]


def test_list_widget_keys_never_exposes_the_token(auth_client: TestClient):
    auth_client.post("/api/widget-keys", json={"label": "Docs site"})
    keys = auth_client.get("/api/widget-keys").json()
    assert len(keys) == 1
    assert "token" not in keys[0]
    assert keys[0]["label"] == "Docs site"


def test_default_label_when_none_given(auth_client: TestClient):
    body = auth_client.post("/api/widget-keys", json={}).json()
    assert body["label"] == "Website widget"


def test_revoke_widget_key(auth_client: TestClient):
    created = auth_client.post("/api/widget-keys", json={"label": "x"}).json()
    delete = auth_client.delete(f"/api/widget-keys/{created['kid']}")
    assert delete.status_code == 204
    keys = auth_client.get("/api/widget-keys").json()
    assert keys[0]["revoked"] is True


def test_revoking_unknown_key_404s(auth_client: TestClient):
    assert auth_client.delete("/api/widget-keys/does-not-exist").status_code == 404


def test_widget_key_endpoints_require_dashboard_auth(app_client: TestClient):
    assert app_client.post("/api/widget-keys", json={}).status_code == 401
    assert app_client.get("/api/widget-keys").status_code == 401


def test_widget_keys_are_isolated_per_account(app_client: TestClient):
    token_a = app_client.post(
        "/api/auth/register",
        json={"email": "a@ekip.dev", "password": "longenough", "name": "A"},
    ).json()["access_token"]
    token_b = app_client.post(
        "/api/auth/register",
        json={"email": "b@ekip.dev", "password": "longenough", "name": "B"},
    ).json()["access_token"]

    app_client.headers["Authorization"] = f"Bearer {token_a}"
    key = app_client.post("/api/widget-keys", json={"label": "A's site"}).json()

    app_client.headers["Authorization"] = f"Bearer {token_b}"
    assert app_client.get("/api/widget-keys").json() == []
    # B cannot revoke A's key
    assert app_client.delete(f"/api/widget-keys/{key['kid']}").status_code == 404


# --- the critical security boundary --------------------------------------------------


def test_widget_token_cannot_access_dashboard_endpoints(auth_client: TestClient):
    widget_token = auth_client.post("/api/widget-keys", json={}).json()["token"]
    hijacked = TestClient(auth_client.app)
    hijacked.headers["Authorization"] = f"Bearer {widget_token}"

    assert hijacked.get("/api/auth/me").status_code == 401
    assert hijacked.get("/api/documents").status_code == 401
    assert hijacked.post("/api/chat", json={"question": "hi"}).status_code == 401


# --- widget websocket -----------------------------------------------------------------


def test_widget_websocket_answers_with_citations(auth_client: TestClient):
    _upload(auth_client)
    token = auth_client.post("/api/widget-keys", json={}).json()["token"]

    with auth_client.websocket_connect(f"/api/widget/chat/ws?key={token}") as ws:
        ws.send_json({"question": "How many annual leave days do employees get?"})
        first = ws.receive_json()
        assert first["type"] == "start"

        message = ws.receive_json()
        while message["type"] == "token":
            message = ws.receive_json()

        assert message["type"] == "done"
        assert message["citations"][0]["source"] == "leave.txt"
        assert message["grounded"] is True


def test_widget_websocket_rejects_revoked_key(auth_client: TestClient):
    created = auth_client.post("/api/widget-keys", json={}).json()
    auth_client.delete(f"/api/widget-keys/{created['kid']}")

    with pytest.raises(Exception):
        with auth_client.websocket_connect(
            f"/api/widget/chat/ws?key={created['token']}"
        ) as ws:
            ws.receive_json()


def test_widget_websocket_rejects_dashboard_token(auth_client: TestClient):
    dashboard_token = auth_client.headers["Authorization"].split(" ", 1)[1]
    with pytest.raises(Exception):
        with auth_client.websocket_connect(
            f"/api/widget/chat/ws?key={dashboard_token}"
        ) as ws:
            ws.receive_json()


def test_widget_websocket_rejects_garbage_key(auth_client: TestClient):
    with pytest.raises(Exception):
        with auth_client.websocket_connect("/api/widget/chat/ws?key=not-a-jwt") as ws:
            ws.receive_json()
