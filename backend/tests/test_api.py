from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.core.config import Settings

HR_TEXT = (
    "Ms. Sara Khan works in the Finance department. Employees accrue twenty "
    "two annual leave days per year. Unused annual leave days carry over."
)


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    app = create_app(
        Settings(data_dir=tmp_path / "data", jwt_secret="test-secret-" + "x" * 24)
    )
    return TestClient(app)


@pytest.fixture
def auth_client(client: TestClient) -> TestClient:
    response = client.post(
        "/api/auth/register",
        json={"email": "admin@ekip.dev", "password": "s3cure-pass", "name": "Admin"},
    )
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


def _upload(client: TestClient, name: str = "leave.txt", text: str = HR_TEXT) -> dict:
    response = client.post(
        "/api/documents/upload",
        files={"file": (name, text.encode(), "text/plain")},
    )
    assert response.status_code == 202, response.text
    return response.json()


# --- health & auth -----------------------------------------------------------------


def test_health(client: TestClient):
    body = client.get("/health").json()
    assert body["status"] == "ok"


def test_register_login_me_flow(client: TestClient):
    register = client.post(
        "/api/auth/register",
        json={"email": "a@b.co", "password": "longenough", "name": "Aittrah"},
    )
    assert register.status_code == 201
    assert register.json()["user"]["role"] == "admin"  # first account bootstraps admin

    login = client.post(
        "/api/auth/login", json={"email": "a@b.co", "password": "longenough"}
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["email"] == "a@b.co"


def test_wrong_password_and_duplicate_email(client: TestClient):
    client.post(
        "/api/auth/register",
        json={"email": "a@b.co", "password": "longenough", "name": "A"},
    )
    assert (
        client.post(
            "/api/auth/login", json={"email": "a@b.co", "password": "wrong-pass"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/auth/register",
            json={"email": "a@b.co", "password": "longenough", "name": "A"},
        ).status_code
        == 409
    )


def test_protected_routes_require_token(client: TestClient):
    assert client.get("/api/documents").status_code == 401
    assert client.post("/api/chat", json={"question": "hi"}).status_code == 401
    assert client.get("/api/analytics/summary").status_code == 401


def test_second_user_is_not_admin_and_cannot_list_users(client: TestClient):
    client.post(
        "/api/auth/register",
        json={"email": "first@ekip.dev", "password": "longenough", "name": "First"},
    )
    second = client.post(
        "/api/auth/register",
        json={"email": "second@ekip.dev", "password": "longenough", "name": "Second"},
    ).json()
    assert second["user"]["role"] == "user"
    headers = {"Authorization": f"Bearer {second['access_token']}"}
    assert client.get("/api/auth/users", headers=headers).status_code == 403


# --- documents ------------------------------------------------------------------------


def test_upload_ingests_and_indexes(auth_client: TestClient):
    job = _upload(auth_client)
    status = auth_client.get(f"/api/documents/jobs/{job['job_id']}").json()
    assert status["status"] == "completed", status
    assert status["document"]["chunks"] >= 1
    assert status["document"]["entities"] >= 2  # Sara Khan, Finance

    docs = auth_client.get("/api/documents").json()
    assert docs[0]["filename"] == "leave.txt"
    assert docs[0]["version"] == 1


def test_upload_rejects_unsupported_extension(auth_client: TestClient):
    response = auth_client.post(
        "/api/documents/upload",
        files={"file": ("malware.exe", b"MZ", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_unknown_job_404(auth_client: TestClient):
    assert auth_client.get("/api/documents/jobs/nope").status_code == 404


# --- chat -------------------------------------------------------------------------------


def test_chat_returns_cited_grounded_answer(auth_client: TestClient):
    _upload(auth_client)
    response = auth_client.post(
        "/api/chat", json={"question": "How many annual leave days do employees get?"}
    )
    body = response.json()
    assert response.status_code == 200, body
    assert body["agent_id"] == "hr"
    assert body["citations"] and body["citations"][0]["source"] == "leave.txt"
    assert body["grounded"] is True
    assert body["conversation_id"]

    history = auth_client.get(
        f"/api/chat/conversations/{body['conversation_id']}"
    ).json()
    assert [m["role"] for m in history] == ["user", "assistant"]


def test_chat_unknown_agent_400(auth_client: TestClient):
    response = auth_client.post(
        "/api/chat", json={"question": "hi", "agent_id": "astrologer"}
    )
    assert response.status_code == 400


def test_agents_endpoint_lists_roster(auth_client: TestClient):
    agents = auth_client.get("/api/chat/agents").json()
    assert {a["id"] for a in agents} == {
        "hr", "finance", "research", "developer", "legal", "operations",
    }


def test_websocket_chat_streams_tokens_then_citations(auth_client: TestClient):
    _upload(auth_client)
    token = auth_client.headers["Authorization"].split(" ", 1)[1]
    with auth_client.websocket_connect(f"/api/chat/ws?token={token}") as ws:
        ws.send_json({"question": "How many annual leave days do employees get?"})
        first = ws.receive_json()
        assert first["type"] == "start" and first["agent_id"] == "hr"

        streamed, message = "", ws.receive_json()
        while message["type"] == "token":
            streamed += message["text"]
            message = ws.receive_json()

        assert message["type"] == "done"
        assert message["citations"][0]["source"] == "leave.txt"
        assert "[1]" in streamed  # citation markers survive streaming


def test_websocket_rejects_bad_token(auth_client: TestClient):
    with pytest.raises(Exception):
        with auth_client.websocket_connect("/api/chat/ws?token=garbage") as ws:
            ws.receive_json()


# --- search / graph / analytics -------------------------------------------------------------


def test_search_endpoint(auth_client: TestClient):
    _upload(auth_client)
    body = auth_client.post(
        "/api/search", json={"query": "annual leave days", "top_k": 3}
    ).json()
    assert body["strategy"] == "graphrag"
    assert body["hits"] and body["hits"][0]["source"] == "leave.txt"


def test_graph_endpoints(auth_client: TestClient):
    _upload(auth_client)
    viz = auth_client.get("/api/graph/viz").json()
    labels = {n["label"] for n in viz["nodes"]}
    assert "Sara Khan" in labels and "Finance" in labels

    hits = auth_client.get("/api/graph/search", params={"q": "sara"}).json()
    assert hits[0]["label"] == "Sara Khan"

    neighborhood = auth_client.get(
        "/api/graph/neighbors", params={"key": hits[0]["key"], "depth": 1}
    ).json()
    assert any(e["type"] == "WORKS_IN" for e in neighborhood["edges"])


def test_analytics_summary_tracks_activity(auth_client: TestClient):
    _upload(auth_client)
    auth_client.post("/api/chat", json={"question": "annual leave days?"})
    summary = auth_client.get("/api/analytics/summary").json()
    assert summary["documents"] == 1
    assert summary["chunks"] >= 1
    assert summary["queries"] == 1
    assert summary["queries_by_agent"].get("hr") == 1
    assert summary["providers"]["llm"] == "extractive-fallback"


# --- profile editing (Module 21) --------------------------------------------------


def test_update_profile_email_and_name(auth_client: TestClient):
    body = auth_client.patch(
        "/api/auth/me", json={"email": "new@ekip.dev", "name": "New Name"}
    ).json()
    assert body["email"] == "new@ekip.dev"
    assert body["name"] == "New Name"
    # old token still works; email change reflected in /me
    assert auth_client.get("/api/auth/me").json()["email"] == "new@ekip.dev"


def test_update_email_conflict_409(auth_client: TestClient, client: TestClient):
    client.post(
        "/api/auth/register",
        json={"email": "taken@ekip.dev", "password": "longenough", "name": "B"},
    )
    response = auth_client.patch("/api/auth/me", json={"email": "taken@ekip.dev"})
    assert response.status_code == 409


def test_change_password_requires_correct_current(auth_client: TestClient):
    bad = auth_client.patch(
        "/api/auth/me",
        json={"current_password": "wrong", "new_password": "brand-new-pass"},
    )
    assert bad.status_code == 400

    ok = auth_client.patch(
        "/api/auth/me",
        json={"current_password": "s3cure-pass", "new_password": "brand-new-pass"},
    )
    assert ok.status_code == 200
    login = auth_client.post(
        "/api/auth/login", json={"email": "admin@ekip.dev", "password": "brand-new-pass"}
    )
    assert login.status_code == 200
