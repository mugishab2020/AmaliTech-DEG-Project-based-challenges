import asyncio

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse

from models import PaymentRequest
from store import IdempotencyRecord, Status, compute_body_hash, generate_tx_id, store

import time

router = APIRouter()

# health check endpoint
@router.get("/health")
async def health():
    return {"status": "ok", "service": "Idempotency Gateway"}


# route to process payment with idempotency logic
@router.post("/process-payment", status_code=201)
async def process_payment(
    payment: PaymentRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
):
    payload = payment.model_dump()
    req_hash = compute_body_hash(payload)

    # Step 1: check if key exists in store
    if idempotency_key in store:
        record = store[idempotency_key]

        #  Step 2: check if request body hash matches
        if record.body_hash != req_hash:
            raise HTTPException(
                status_code=422,
                detail="Idempotency key already used for a different request body.",
            )

        #  Step 3: check if processing is still underway 
        if record.status == Status.PROCESSING:
            await asyncio.wait_for(record.ready.wait(), timeout=30.0)

        #  Step 4: COMPLETED — return cached response 
        return JSONResponse(
            content=record.response_body,
            status_code=record.status_code,
            headers={"X-Cache-Hit": "true"},
        )

    #  Step 5: for the new idemptancy key - register as PROCESSING 
    record = IdempotencyRecord(body_hash=req_hash)
    store[idempotency_key] = record

    try:
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
        record.ready.set()

        return JSONResponse(content=response_body, status_code=201)

    except Exception as exc:
        del store[idempotency_key]
        raise HTTPException(status_code=500, detail=str(exc)) from exc