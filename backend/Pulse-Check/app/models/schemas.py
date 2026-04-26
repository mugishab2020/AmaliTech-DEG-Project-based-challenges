from pydantic import BaseModel, Field
from datetime import datetime


class MonitorCreate(BaseModel):
    id: str = Field(..., examples=["solar-farm-01"])
    timeout: int = Field(3600, ge=10, description="Seconds before alert fires")
    webhook_url: str | None = Field(None, examples=["https://hooks.com/alert"])


class MonitorOut(BaseModel):
    id: str
    status: str
    timeout: int
    last_heartbeat: datetime
    webhook_url: str | None


class HeartbeatOut(BaseModel):
    id: str
    status: str
    last_heartbeat: datetime
