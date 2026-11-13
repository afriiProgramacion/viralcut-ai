import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_settings(client):
    r = client.get("/api/settings")
    assert r.status_code == 200
    assert "ai_provider" in r.json()


def test_project_crud(client):
    r = client.post("/api/projects", json={"name": "t"})
    assert r.status_code == 200
    pid = r.json()["id"]
    r = client.get(f"/api/projects/{pid}")
    assert r.status_code == 200
    r = client.delete(f"/api/projects/{pid}")
    assert r.status_code == 200