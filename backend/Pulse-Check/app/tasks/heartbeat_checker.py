"""
Background task: Dead Man's Switch checker.

Runs every POLL_INTERVAL seconds. For every ACTIVE monitor whose
last_heartbeat is older than its timeout, we:
  1. Set status = DOWN
  2. Fire a webhook (if configured) OR log a CRITICAL alert.
"""
import asyncio
import logging
from datetime import datetime

import httpx

from app import db
from app.models.monitor import Status

logger = logging.getLogger("critmon.checker")

POLL_INTERVAL = 10  # seconds between scans


async def check_monitors() -> None:
    logger.info("Heartbeat checker started (poll interval: %ds)", POLL_INTERVAL)
    while True:
        await asyncio.sleep(POLL_INTERVAL)
        _run_checks()


def _run_checks() -> None:
    now = datetime.utcnow()
    for monitor in list(db.monitors.values()):
        if monitor.status != Status.ACTIVE:
            continue  # skip PAUSED and already-DOWN monitors

        elapsed = (now - monitor.last_heartbeat).total_seconds()
        if elapsed > monitor.timeout:
            monitor.status = Status.DOWN
            logger.critical(
                "ALERT  monitor=%s  elapsed=%.1fs  timeout=%ds  -> DOWN",
                monitor.id,
                elapsed,
                monitor.timeout,
            )
            _fire_alert(monitor)


def _fire_alert(monitor) -> None:
    if not monitor.webhook_url:
        return

    payload = {
        "monitor_id": monitor.id,
        "status": "DOWN",
        "message": f"No heartbeat received within {monitor.timeout}s.",
    }
    try:
        # Fire-and-forget synchronous call inside the async loop.
        # For production, replace with a proper task queue (Celery/ARQ).
        with httpx.Client(timeout=5) as client:
            resp = client.post(monitor.webhook_url, json=payload)
            logger.info("Webhook sent to %s -> HTTP %d", monitor.webhook_url, resp.status_code)
    except Exception as exc:
        logger.error("Webhook delivery failed for %s: %s", monitor.id, exc)
