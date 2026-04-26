from fastapi import APIRouter, HTTPException
from app import db
from app.models.monitor import Monitor, Status
from app.models.schemas import MonitorCreate, MonitorOut

router = APIRouter(prefix="/monitors", tags=["Monitors"])


@router.post("/", status_code=201, response_model=MonitorOut)
def register_monitor(payload: MonitorCreate):
    """
    Register a new monitor (Dead Man's Switch).
    Returns 409 if a monitor with the same id already exists.
    """
    if payload.id in db.monitors:
        raise HTTPException(status_code=409, detail=f"Monitor '{payload.id}' already exists.")

    monitor = Monitor(
        id=payload.id,
        timeout=payload.timeout,
        webhook_url=payload.webhook_url,
    )
    db.monitors[payload.id] = monitor
    return _to_out(monitor)


@router.post("/{monitor_id}/pause", response_model=MonitorOut)
def pause_monitor(monitor_id: str):
    """
    Pauses a monitor. The background checker will skip PAUSED monitors.
    Returns 404 if not found.
    """
    monitor = _get_or_404(monitor_id)
    monitor.status = Status.PAUSED
    return _to_out(monitor)


@router.post("/{monitor_id}/resume", response_model=MonitorOut)
def resume_monitor(monitor_id: str):

    """Resume a previously paused or downed monitor and reset its heartbeat clock."""
    
    from datetime import datetime
    monitor = _get_or_404(monitor_id)
    monitor.status = Status.ACTIVE
    monitor.last_heartbeat = datetime.utcnow()
    return _to_out(monitor)


@router.get("/{monitor_id}", response_model=MonitorOut)
def get_monitor(monitor_id: str):
    """Inspect the current state of a monitor."""
    return _to_out(_get_or_404(monitor_id))


@router.get("/", response_model=list[MonitorOut])
def list_monitors():
    """List all registered monitors."""
    return [_to_out(m) for m in db.monitors.values()]


@router.delete("/{monitor_id}", status_code=204)
def delete_monitor(monitor_id: str):
    """Remove a monitor entirely."""
    _get_or_404(monitor_id)
    del db.monitors[monitor_id]


def _get_or_404(monitor_id: str):
    monitor = db.monitors.get(monitor_id)
    if not monitor:
        raise HTTPException(status_code=404, detail=f"Monitor '{monitor_id}' not found.")
    return monitor


def _to_out(m) -> MonitorOut:
    return MonitorOut(
        id=m.id,
        status=m.status,
        timeout=m.timeout,
        last_heartbeat=m.last_heartbeat,
        webhook_url=m.webhook_url,
    )
