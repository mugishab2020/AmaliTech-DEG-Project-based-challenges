import time

from fastapi import APIRouter

from store import KEY_TTL_SECONDS, store

router = APIRouter(prefix="/admin")


@router.get("/keys")
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