import asyncio
import hashlib
import json
import time
from enum import Enum
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ─────────────────────────────────────────────
# App setup
# ─────────────────────────────────────────────

app = FastAPI(
    title="Idempotency Gateway",
    description="Pay-Once Protocol — FinSafe Transactions Ltd.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store  (to be replaced with Redis or real database in prod)


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


# key → IdempotencyRecord
store: dict[str, IdempotencyRecord] = {}

#

class PaymentRequest(BaseModel):
    amount: float
    currency: str

class PaymentResponse(BaseModel):
    message: str
    amount: float
    currency: str
    transaction_id: str
    processed_at: float

# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def body_hash(payload: dict) -> str:
    """Deterministic SHA-256 hash of the request body."""
    canonical = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def generate_tx_id(idempotency_key: str) -> str:
    return "TX-" + hashlib.md5(idempotency_key.encode()).hexdigest()[:12].upper()


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "Idempotency Gateway"}


@app.post("/process-payment", status_code=201)
async def process_payment(
    payment: PaymentRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    payload = payment.model_dump()
    req_hash = body_hash(payload)

    # ── Step 1: Key exists in store? ──────────────────────────────────────
    if idempotency_key in store:
        record = store[idempotency_key]

        # ── Step 2: Same request body? ────────────────────────────────────
        if record.body_hash != req_hash:
            raise HTTPException(
                status_code=422,
                detail="Idempotency key already used for a different request body.",
            )

        # ── Step 3: Still PROCESSING (race condition / in-flight) ─────────
        if record.status == Status.PROCESSING:
            # Block until the first request finishes (bonus story)
            await asyncio.wait_for(record.ready.wait(), timeout=30.0)

        # ── Step 4: COMPLETED — return cached response ────────────────────
        response = JSONResponse(
            content=record.response_body,
            status_code=record.status_code,
            headers={"X-Cache-Hit": "true"},
        )
        return response

    # ── Step 5: Brand-new key — register as PROCESSING ───────────────────
    record = IdempotencyRecord(body_hash=req_hash)
    store[idempotency_key] = record

    try:
        # Simulate payment processing (2-second delay)
        await asyncio.sleep(2)

        response_body = {
            "message": f"Charged {payment.amount} {payment.currency}",
            "amount": payment.amount,
            "currency": payment.currency,
            "transaction_id": generate_tx_id(idempotency_key),
            "processed_at": time.time(),
        }

        record.response_body = response_body
        record.status_code = 201
        record.status = Status.COMPLETED
        record.ready.set()  # wake up any waiting duplicate requests

        return JSONResponse(content=response_body, status_code=201)

    except Exception as exc:
        # Clean up on failure so the client can retry
        del store[idempotency_key]
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ─────────────────────────────────────────────
# Developer's Choice: Key expiry / TTL listing
# ─────────────────────────────────────────────

KEY_TTL_SECONDS = 86_400  # 24 hours


@app.get("/admin/keys")
async def list_keys():
    """
    Developer's Choice feature: surface all stored idempotency keys
    with their status and age, so ops teams can monitor & debug.
    Also prunes keys older than TTL (24 h).
    """
    now = time.time()
    expired = [k for k, v in store.items() if now - v.created_at > KEY_TTL_SECONDS]
    for k in expired:
        del store[k]

    return {
        "total": len(store),
        "keys": [
            {
                "key": k,
                "status": v.status,
                "age_seconds": round(now - v.created_at, 1),
            }
            for k, v in store.items()
        ],
    }