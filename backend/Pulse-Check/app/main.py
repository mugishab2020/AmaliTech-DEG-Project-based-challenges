
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routes import monitors, heartbeats
from app.tasks.heartbeat_checker import check_monitors

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    task = asyncio.create_task(check_monitors())
    yield
    # ── Shutdown ─────────────────────────────────────────────────────────────
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="CritMon – Dead Man's Switch API",
    description=(
        "Monitors for remote infrastructure devices. "
        "Each device must ping before its timer expires or an alert fires."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(monitors.router)
app.include_router(heartbeats.router)


@app.get("/health", tags=["Meta"])
def health():
    return {"status": "ok"}
