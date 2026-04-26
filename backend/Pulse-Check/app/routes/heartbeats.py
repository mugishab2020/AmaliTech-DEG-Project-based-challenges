from fastapi import APIRouter, HTTPException
from datetime import datetime
from app import db
from app.models.monitor import Status
from app.models.schemas import HeartbeatOut

router = APIRouter(prefix="/heartbeat", tags=["Heartbeat"])


@router.post("/{monitor_id}", response_model=HeartbeatOut)
def ping(monitor_id: str):
    """
    Reset the countdown for a monitor.
    The device calls this endpoint before its timer runs out.
    Returns 404 if the monitor does not exist.
    """
    monitor = db.monitors.get(monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail=f"Monitor '{monitor_id}' not found.")

    monitor.status = Status.ACTIVE
    monitor.last_heartbeat = datetime.utcnow()

    return HeartbeatOut(
        id=monitor.id,
        status=monitor.status,
        last_heartbeat=monitor.last_heartbeat,
    )
