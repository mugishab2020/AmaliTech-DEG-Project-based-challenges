"""
Tests for monitor registration and pause/resume endpoints.
"""
import pytest
from fastapi.testclient import TestClient

from main import app
from app import db


@pytest.fixture(autouse=True)
def clear_db():
    """Reset the in-memory store between tests."""
    db.monitors.clear()
    yield
    db.monitors.clear()


client = TestClient(app)


# ── Registration ──────────────────────────────────────────────────────────────

def test_register_monitor_returns_201():
    resp = client.post("/monitors/", json={"id": "solar-01", "timeout": 3600})
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == "solar-01"
    assert body["status"] == "ACTIVE"
    assert body["timeout"] == 3600


def test_register_duplicate_returns_409():
    client.post("/monitors/", json={"id": "solar-01", "timeout": 60})
    resp = client.post("/monitors/", json={"id": "solar-01", "timeout": 60})
    assert resp.status_code == 409


def test_register_with_webhook():
    resp = client.post("/monitors/", json={
        "id": "weather-01",
        "timeout": 120,
        "webhook_url": "https://hooks.example.com/alert",
    })
    assert resp.status_code == 201
    assert resp.json()["webhook_url"] == "https://hooks.example.com/alert"


def test_register_timeout_too_short_returns_422():
    resp = client.post("/monitors/", json={"id": "bad", "timeout": 5})
    assert resp.status_code == 422


# ── Pause / Resume ────────────────────────────────────────────────────────────

def test_pause_monitor():
    client.post("/monitors/", json={"id": "solar-01", "timeout": 60})
    resp = client.post("/monitors/solar-01/pause")
    assert resp.status_code == 200
    assert resp.json()["status"] == "PAUSED"


def test_pause_unknown_returns_404():
    resp = client.post("/monitors/ghost/pause")
    assert resp.status_code == 404


def test_resume_monitor():
    client.post("/monitors/", json={"id": "solar-01", "timeout": 60})
    client.post("/monitors/solar-01/pause")
    resp = client.post("/monitors/solar-01/resume")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACTIVE"


# ── Read / Delete ─────────────────────────────────────────────────────────────

def test_get_monitor():
    client.post("/monitors/", json={"id": "solar-01", "timeout": 60})
    resp = client.get("/monitors/solar-01")
    assert resp.status_code == 200
    assert resp.json()["id"] == "solar-01"


def test_list_monitors():
    client.post("/monitors/", json={"id": "a", "timeout": 60})
    client.post("/monitors/", json={"id": "b", "timeout": 120})
    resp = client.get("/monitors/")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_delete_monitor():
    client.post("/monitors/", json={"id": "solar-01", "timeout": 60})
    resp = client.delete("/monitors/solar-01")
    assert resp.status_code == 204
    assert client.get("/monitors/solar-01").status_code == 404
