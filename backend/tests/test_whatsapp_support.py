import asyncio
from types import SimpleNamespace

import pytest

from app.schemas.order import OrderStatus
from app.services import session_store as store
import app.services.groq_service as groq_service


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def clear_sessions():
    store._store.clear()
    store._processed_message_ids.clear()


def test_status_flow_requests_reference_then_returns_deterministic_status(monkeypatch):
    async def fake_lookup(reference: str):
        assert reference == "40901989"
        return SimpleNamespace(
            id="abc12345-order",
            order_number="ORD-40901989",
            tracking_code="TRK-40901989",
            status=OrderStatus.preparing,
            total_amount=45.0,
        )

    monkeypatch.setattr(groq_service, "get_order_detail_by_reference", fake_lookup)

    sender = "233244123456"
    first_reply = run(groq_service.handle_incoming_message(sender, "What's the status of my order?"))

    assert "Please send your *order number* or *tracking code*" in first_reply
    assert store.get_state(sender) == "awaiting_support_reference"

    second_reply = run(groq_service.handle_incoming_message(sender, "This is my order id 40901989"))

    assert "ORD-40901989" in second_reply
    assert "being prepared" in second_reply
    assert "TRK-40901989" in second_reply
    assert store.get_state(sender) == "asked_intent"


def test_cancel_flow_requests_reference_and_confirms(monkeypatch):
    async def fake_lookup(reference: str):
        assert reference == "TRK-DEMO1001"
        return SimpleNamespace(
            id="cancel-order-1",
            order_number="ORD-DEMO1001",
            tracking_code="TRK-DEMO1001",
            status=OrderStatus.confirmed,
            total_amount=85.0,
        )

    async def fake_cancel(order_id, payload):
        assert order_id == "cancel-order-1"
        assert payload.reason_code == "customer_changed_mind"
        return SimpleNamespace(
            id="cancel-order-1",
            order_number="ORD-DEMO1001",
            tracking_code="TRK-DEMO1001",
            status=OrderStatus.cancelled,
            total_amount=85.0,
        )

    monkeypatch.setattr(groq_service, "get_order_detail_by_reference", fake_lookup)
    monkeypatch.setattr(groq_service, "cancel_order", fake_cancel)

    sender = "233244123457"
    first_reply = run(groq_service.handle_incoming_message(sender, "Please cancel my order"))
    assert "Please send your *order number* or *tracking code* first" in first_reply
    assert store.get_state(sender) == "awaiting_support_reference"

    second_reply = run(groq_service.handle_incoming_message(sender, "TRK-DEMO1001"))
    assert "Reply *Yes* to cancel this order" in second_reply
    assert store.get_state(sender) == "confirming_cancellation"

    third_reply = run(groq_service.handle_incoming_message(sender, "Yes"))
    assert "now *cancelled*" in third_reply
    assert store.get_state(sender) == "asked_intent"
