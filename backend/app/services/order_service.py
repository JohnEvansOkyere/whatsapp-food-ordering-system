"""
Order service.
Creates orders in Supabase, then fires WhatsApp receipt + owner notification.
"""

import uuid
import logging
from datetime import datetime, timezone
from app.database import get_supabase
from app.schemas.order import (
    CreateOrderSchema,
    OrderResponseSchema,
    OrderItemSchema,
    OrderStatus,
)
from app.services.whatsapp import (
    send_order_receipt_to_customer,
    send_order_notification_to_owner,
)

logger = logging.getLogger(__name__)


async def create_order(data: CreateOrderSchema) -> OrderResponseSchema:
    """
    1. Save order to Supabase
    2. Send POS receipt to customer on WhatsApp
    3. Send order notification to owner on WhatsApp
    """
    supabase = get_supabase()
    order_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    items_json = [item.model_dump() for item in data.items]

    row = {
        "id": order_id,
        "customer_phone": data.customer_phone,
        "customer_name": data.customer_name,
        "delivery_address": data.delivery_address,
        "items": items_json,
        "total_amount": data.total_amount,
        "payment_method": data.payment_method,
        "status": OrderStatus.pending.value,
        "notes": data.notes,
        "created_at": now,
    }

    result = supabase.table("orders").insert(row).execute()

    if not result.data:
        raise Exception("Failed to insert order into Supabase")

    order = OrderResponseSchema(
        id=order_id,
        customer_phone=data.customer_phone,
        customer_name=data.customer_name,
        delivery_address=data.delivery_address,
        items=data.items,
        total_amount=data.total_amount,
        payment_method=data.payment_method,
        status=OrderStatus.pending,
        notes=data.notes,
        created_at=datetime.fromisoformat(now),
    )

    # Fire WhatsApp messages — don't block on failure
    try:
        await send_order_receipt_to_customer(order)
    except Exception as e:
        logger.error(f"Receipt send failed for order {order_id}: {e}")

    try:
        await send_order_notification_to_owner(order)
    except Exception as e:
        logger.error(f"Owner notification failed for order {order_id}: {e}")

    return order


async def get_order(order_id: str) -> OrderResponseSchema | None:
    """Fetch a single order by ID."""
    supabase = get_supabase()
    result = supabase.table("orders").select("*").eq("id", order_id).execute()

    if not result.data:
        return None

    row = result.data[0]
    items = [OrderItemSchema(**i) for i in row["items"]]

    return OrderResponseSchema(
        id=row["id"],
        customer_phone=row["customer_phone"],
        customer_name=row.get("customer_name"),
        delivery_address=row["delivery_address"],
        items=items,
        total_amount=row["total_amount"],
        payment_method=row["payment_method"],
        status=OrderStatus(row["status"]),
        notes=row.get("notes"),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


async def update_order_status(order_id: str, status: OrderStatus) -> bool:
    """Update order status."""
    supabase = get_supabase()
    result = (
        supabase.table("orders")
        .update({"status": status.value})
        .eq("id", order_id)
        .execute()
    )
    return bool(result.data)
