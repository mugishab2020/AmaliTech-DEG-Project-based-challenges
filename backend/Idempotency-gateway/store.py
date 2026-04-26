import asyncio
import hashlib
import json
import time
from enum import Enum


class Status(str, Enum):
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"


class IdempotencyRecord:
    def __init__(self, body_hash: str):
        self.body_hash: str = body_hash
        self.status: Status = Status.PROCESSING
        self.response_body: dict | None = None
        self.status_code: int | None = None
        self.created_at: float = time.time()
        self.ready: asyncio.Event = asyncio.Event()


# sore of the IdempotencyRecord
store: dict[str, IdempotencyRecord] = {}

KEY_TTL_SECONDS = 86_400 # 24 hours


def compute_body_hash(payload: dict) -> str:
    """SHA-256 hashing of the request body."""
    canonical = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def generate_tx_id(idempotency_key: str) -> str:
    return "TX-" + hashlib.md5(idempotency_key.encode()).hexdigest()[:12].upper()