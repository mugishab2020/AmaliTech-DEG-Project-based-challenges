# Idempotency Gateway — Pay-Once Protocol

A FastAPI service that guarantees every payment request is processed **exactly once**, no matter how many times it is retried.

### Flowchart /Aechtecture diagram

The flowchat is included in the file of this forder

## Setup Instructions

### Prerequisites

- Python 3.11+

### 1. Clone & install

```bash
git clone https://github.com/YOUR_USERNAME/idempotency-gateway.git
cd idempotency-gateway
pip install -r requirements.txt
```

### 2. Start the server

#### Local Python setup

```bash
uvicorn app:app --reload
```

#### Docker setup

```bash
docker compose build
docker compose up -d
```

Server runs at **http://localhost:8001** (Docker) or **http://localhost:8000** (local)

Interactive docs: **http://localhost:8001/docs** (Docker) or **http://localhost:8000/docs** (local)

### 3. Run the tests

```bash
pytest tests.py -v


## API Documentation

### POST /process-payment`

Process a payment. Supply a unique `Idempotency-Key` header on every request.

#### Headers

| Header            | Required | Description                        |
|-------------------|----------|------------------------------------|
| `Idempotency-Key` |  Yes   | Unique string per payment attempt  |
| `Content-Type`    |  Yes   | `application/json`                 |

#### Request body
""json
{
  "amount": 100,
  "currency": "GHS"
}
""

#### Responses
[
  {
    "scenario": "New request — processed",
    "status": 201,
    "x_cache_hit": null,
    "body": {
      "message": "Charged 100 GHS"
    }
  },
  {
    "scenario": "Duplicate request — same body",
    "status": 201,
    "x_cache_hit": true,
    "body": "Exact same body as first response"
  },
  {
    "scenario": "In-flight duplicate",
    "status": 201,
    "x_cache_hit": true,
    "body": "Waits, then returns first response"
  },
  {
    "scenario": "Same key, different body",
    "status": 422,
    "x_cache_hit": null,
    "body": {
      "detail": "Idempotency key already used..."
    }
  },
  {
    "scenario": "Missing Idempotency-Key header",
    "status": 422,
    "x_cache_hit": null,
    "body": "FastAPI validation error"
  }
]                      |

#### Example — Happy path

~~~bash
curl -X POST http://localhost:8000/process-payment \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: order-abc-001" \
  -d '{"amount": 100, "currency": "GHS"}'
```

json
{
"message": "Charged 100.0 GHS",
"amount": 100.0,
"currency": "GHS",
"transaction_id": "TX-5F3A9B1C2E4D",
"processed_at": 1718000000.123
}

#### Example — Replay (duplicate)

Send the exact same request again:

~~Bash
curl -X POST http://localhost:8000/process-payment \
 -H "Content-Type: application/json" \
 -H "Idempotency-Key: order-abc-001" \
 -d '{"amount": 100, "currency": "GHS"}'

Response headers include `X-Cache-Hit: true`. Body is identical to the first call.

#### Example — Conflict (different body, same key)

bash
curl -X POST http://localhost:8000/process-payment \
 -H "Content-Type: application/json" \
 -H "Idempotency-Key: order-abc-001" \
 -d '{"amount": 500, "currency": "GHS"}'

## response

json
{ "detail": "Idempotency key already used for a different request body." }

### `GET /health`

~~bash
curl http://localhost:8000/health
~~

~~json
{ "status": "ok", "service": "Idempotency Gateway" }
~~

### `GET /admin/keys`

List all active idempotency keys, their status, and age. Expired keys (> 24 h) are pruned automatically.

~~bash
curl http://localhost:8000/admin/keys
~~

~~json
{
"total": 2,
"keys": [
{ "key": "order-abc-001", "status": "COMPLETED", "age_seconds": 42.3 },
{ "key": "order-abc-002", "status": "PROCESSING", "age_seconds": 1.1 }
]
}~~

## Design Decisions

### 1. In-memory store with `asyncio.Event`

The store is a plain Python `dict`. Each record holds an `asyncio.Event` that is `.set()` when the first request completes. Any concurrent duplicate (the in-flight race condition) simply calls `await record.ready.wait()` — it blocks cheaply without spinning, and wakes up the instant the original finishes.

For production, We may need to replace it with the database

### 2. Body hashing (SHA-256)

The request body is canonicalised (`json.dumps` with `sort_keys=True`) and hashed with SHA-256. Storing the hash — not the raw body — keeps memory usage constant regardless of payload size, and makes the comparison O(1).

### 3. Deterministic `transaction_id`

The `transaction_id` is derived from the `Idempotency-Key` via MD5. This means the same key always yields the same TX ID, which clients can use for auditing without storing anything themselves.

### 4. No `Idempotency-Key` → pass-through

Per the flowchart, if the header is absent FastAPI's built-in validation returns `422` immediately, which is consistent with the spec.

---

## Developer's Choice — Key Expiry & Ops Visibility (`GET /admin/keys`)

**Why:** In a real Fintech system, idempotency keys should not live forever. Holding them indefinitely wastes memory and can block legitimate re-use of the same payment reference after a business day. Stripe, for example, expires keys after **24 hours**.

**What was added:**

- Every `IdempotencyRecord` stores a `created_at` timestamp.
- A configurable `KEY_TTL_SECONDS` constant (default 86 400 s / 24 h) controls expiry.
- The `GET /admin/keys` endpoint lists all active keys with their status and age, and **prunes expired keys** on every call — a lightweight lazy-expiry strategy that avoids background threads.

This gives ops teams real-time visibility into in-flight vs. completed payments and prevents unbounded memory growth in long-running processes.

---

## Project Structure

idempotency-gateway/
├── main.py # FastAPI application
├── test.py # pytest test suite
├── requirements.txt # Python dependencies
└── README.md # This file
