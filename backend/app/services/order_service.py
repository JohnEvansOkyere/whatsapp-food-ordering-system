import uuid
from datetime import datetime, timezone
from app.database import get_supabase
from app.schemas.order import CreateOrderSchema, OrderResponseSchema, OrderStatus, OrderSummary
from app.services.whatsapp import notify_owner_new_order, send_order_confirmation_to_customer
import logging

logger = logging.getLogger(__name__)


async def create_order(data: CreateOrderSchema) -> OrderResponseSchema:
    """Create a new order in Supabase and notify owner + customer."""
    supabase = get_supabase()
    order_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Serialize items for storage
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
        raise Exception("Failed to insert order into database")

    created = result.data[0]

    # Build summary for notifications
    summary = OrderSummary(
        order_id=order_id,
        customer_phone=data.customer_phone,
        customer_name=data.customer_name,
        delivery_address=data.delivery_address,
        items=data.items,
        total_amount=data.total_amount,
        payment_method=data.payment_method,
    )

    # Fire notifications (don't block on failure)
    try:
        await notify_owner_new_order(summary)
    except Exception as e:
        logger.error(f"Owner notification failed: {e}")

    try:
        await send_order_confirmation_to_customer(data.customer_phone, summary)
    except Exception as e:
        logger.error(f"Customer confirmation failed: {e}")

    return OrderResponseSchema(
        id=created["id"],
        customer_phone=created["customer_phone"],
        customer_name=created.get("customer_name"),
        delivery_address=created["delivery_address"],
        items=data.items,
        total_amount=created["total_amount"],
        payment_method=created["payment_method"],
        status=OrderStatus(created["status"]),
        notes=created.get("notes"),
        created_at=datetime.fromisoformat(created["created_at"]),
    )


async def get_order(order_id: str) -> OrderResponseSchema | None:
    """Fetch a single order by ID."""
    supabase = get_supabase()
    result = supabase.table("orders").select("*").eq("id", order_id).execute()

    if not result.data:
        return None

    row = result.data[0]
    from app.schemas.order import OrderItemSchema
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
    """Update order status (called from admin or webhook)."""
    supabase = get_supabase()
    result = (
        supabase.table("orders")
        .update({"status": status.value})
        .eq("id", order_id)
        .execute()
    )
    return bool(result.data)
