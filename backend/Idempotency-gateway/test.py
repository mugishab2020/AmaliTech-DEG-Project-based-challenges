"""
Tests for the Idempotency Gateway.
Run with: pytest tests.py -v
"""

import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from app import app
from store import store


@pytest.fixture(autouse=True)
def clear_store():
    store.clear()
    yield
    store.clear()


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# User Story 1: First Transaction (Happy Path)

@pytest.mark.asyncio
async def test_first_payment_returns_201(client):
    async with client as c:
        resp = await c.post(
            "/process-payment",
            json={"amount": 100, "currency": "GHS"},
            headers={"Idempotency-Key": "key-001"},
        )
    assert resp.status_code == 201
    body = resp.json()
    assert "Charged 100" in body["message"]
    assert "GHS" in body["message"]


# User Story 2: Duplicate Request (Idempotency Logic)

@pytest.mark.asyncio
async def test_duplicate_returns_same_response(client):
    async with client as c:
        r1 = await c.post(
            "/process-payment",
            json={"amount": 50, "currency": "USD"},
            headers={"Idempotency-Key": "key-002"},
        )
        r2 = await c.post(
            "/process-payment",
            json={"amount": 50, "currency": "USD"},
            headers={"Idempotency-Key": "key-002"},
        )

    assert r1.status_code == r2.status_code == 201
    assert r1.json()["message"] == r2.json()["message"]
    assert r1.json()["transaction_id"] == r2.json()["transaction_id"]
    assert r2.headers.get("x-cache-hit") == "true"


# User Story 3: Same Key, Different Body (Fraud/Error Check)

@pytest.mark.asyncio
async def test_different_body_same_key_returns_422(client):
    async with client as c:
        await c.post(
            "/process-payment",
            json={"amount": 100, "currency": "GHS"},
            headers={"Idempotency-Key": "key-003"},
        )
        r2 = await c.post(
            "/process-payment",
            json={"amount": 500, "currency": "GHS"},
            headers={"Idempotency-Key": "key-003"},
        )

    assert r2.status_code == 422
    assert "different request body" in r2.json()["detail"]


# Bonus: In-Flight Race Condition 

@pytest.mark.asyncio
async def test_in_flight_duplicate_waits_and_returns_same(client):
    async with client as c:
        task_a = asyncio.create_task(
            c.post(
                "/process-payment",
                json={"amount": 200, "currency": "EUR"},
                headers={"Idempotency-Key": "key-004"},
            )
        )
        await asyncio.sleep(0.1)
        task_b = asyncio.create_task(
            c.post(
                "/process-payment",
                json={"amount": 200, "currency": "EUR"},
                headers={"Idempotency-Key": "key-004"},
            )
        )
        r1, r2 = await asyncio.gather(task_a, task_b)

    assert r1.status_code == r2.status_code == 201
    assert r1.json()["transaction_id"] == r2.json()["transaction_id"]
    assert r2.headers.get("x-cache-hit") == "true"


# Health Check Endpoint 

@pytest.mark.asyncio
async def test_health(client):
    async with client as c:
        r = await c.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"