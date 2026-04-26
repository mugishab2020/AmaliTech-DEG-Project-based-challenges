from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Status(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    DOWN = "DOWN"


@dataclass
class Monitor:
    id: str
    timeout: int        
    webhook_url: str | None = None
    status: Status = Status.ACTIVE
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
