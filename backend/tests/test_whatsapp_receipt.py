from datetime import datetime

from app.schemas.order import (
    FulfillmentType,
    OrderItemSchema,
    OrderResponseSchema,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
)
from app.services.whatsapp import _build_receipt


def _sample_order(order_number: str | None, tracking_code: str | None) -> OrderResponseSchema:
    return OrderResponseSchema(
        id="8a8e1807-1234-5678-9999-abcdef123456",
        order_number=order_number,
        tracking_code=tracking_code,
        customer_phone="233245540271",
        customer_name="Ama",
        delivery_address="Osu, Accra",
        items=[
            OrderItemSchema(
                item_id="jollof-chicken",
                name="Jollof Rice + Chicken",
                quantity=2,
                unit_price=45.0,
                total_price=90.0,
            )
        ],
        subtotal_amount=90.0,
        total_amount=90.0,
        payment_method=PaymentMethod.momo,
        payment_status=PaymentStatus.unpaid,
        status=OrderStatus.new,
        channel="whatsapp",
        fulfillment_type=FulfillmentType.delivery,
        notes=None,
        created_at=datetime(2026, 4, 27, 12, 0, 0),
    )


def test_receipt_uses_order_number_and_tracking_code():
    receipt = _build_receipt(_sample_order("ORD-8A8E1807", "TRK-8A8E1807"), "HallMark Cafe")

    assert "Order ID: *ORD-8A8E1807*" in receipt
    assert "Tracking: *TRK-8A8E1807*" in receipt
    assert "Order ID: *8A8E1807*" not in receipt


def test_receipt_falls_back_to_short_uuid_when_order_number_is_missing():
    receipt = _build_receipt(_sample_order(None, None), "HallMark Cafe")

    assert "Order ID: *8A8E1807*" in receipt
    assert "Tracking:" not in receipt
