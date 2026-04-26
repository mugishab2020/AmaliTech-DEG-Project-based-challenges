"""
Unit tests for the background heartbeat checker logic.
"""
import pytest
from datetime import datetime, timedelta

from app import db
from app.models.monitor import Monitor, Status
from app.tasks.heartbeat_checker import _run_checks


@pytest.fixture(autouse=True)
def clear_db():
    db.monitors.clear()
    yield
    db.monitors.clear()


def _add(monitor_id: str, timeout: int, seconds_since_last_ping: int, status=Status.ACTIVE):
    m = Monitor(
        id=monitor_id,
        timeout=timeout,
        last_heartbeat=datetime.utcnow() - timedelta(seconds=seconds_since_last_ping),
        status=status,
    )
    db.monitors[monitor_id] = m
    return m


def test_expired_monitor_becomes_down():
    _add("solar-01", timeout=60, seconds_since_last_ping=120)
    _run_checks()
    assert db.monitors["solar-01"].status == Status.DOWN


def test_healthy_monitor_stays_active():
    _add("solar-01", timeout=60, seconds_since_last_ping=30)
    _run_checks()
    assert db.monitors["solar-01"].status == Status.ACTIVE


def test_paused_monitor_is_ignored():
    _add("solar-01", timeout=60, seconds_since_last_ping=300, status=Status.PAUSED)
    _run_checks()
    assert db.monitors["solar-01"].status == Status.PAUSED


def test_already_down_monitor_is_not_rechecked():
    _add("solar-01", timeout=60, seconds_since_last_ping=300, status=Status.DOWN)
    _run_checks()
    assert db.monitors["solar-01"].status == Status.DOWN


def test_multiple_monitors_checked_independently():
    _add("solar-01", timeout=60, seconds_since_last_ping=120)   # should go DOWN
    _add("weather-01", timeout=60, seconds_since_last_ping=10)  # should stay ACTIVE
    _run_checks()
    assert db.monitors["solar-01"].status == Status.DOWN
    assert db.monitors["weather-01"].status == Status.ACTIVE
