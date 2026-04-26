"""
Tests for the heartbeat (ping) endpoint.
"""
import pytest
from fastapi.testclient import TestClient

from main import app
from app import db

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_db():
    db.monitors.clear()
    yield
    db.monitors.clear()


def test_heartbeat_resets_clock():
    client.post("/monitors/", json={"id": "solar-01", "timeout": 60})
    resp = client.post("/heartbeat/solar-01")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ACTIVE"
    assert "last_heartbeat" in body


def test_heartbeat_unknown_monitor_returns_404():
    resp = client.post("/heartbeat/ghost")
    assert resp.status_code == 404


def test_heartbeat_revives_down_monitor():
    """
    A DOWN monitor should become ACTIVE again after receiving a ping.
    (Simulated by manually setting status to DOWN.)
    """
    from app.models.monitor import Status
    client.post("/monitors/", json={"id": "solar-01", "timeout": 60})
    db.monitors["solar-01"].status = Status.DOWN

    resp = client.post("/heartbeat/solar-01")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACTIVE"
