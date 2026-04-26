from pydantic import BaseModel
from typing import Literal

class MonitorCreate(BaseModel):
    id: str
    timeout: int
    alert_email: str

class Monitor:
    def __init__(self, id, timeout, alert_email):
        self.id = id
        self.timeout = timeout
        self.alert_email = alert_email
        self.status: Literal["ACTIVE", "PAUSED", "DOWN"] = "ACTIVE"
        self.last_heartbeat = None