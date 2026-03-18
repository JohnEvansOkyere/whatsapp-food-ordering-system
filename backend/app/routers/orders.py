from fastapi import APIRouter, HTTPException, status
from app.schemas.order import CreateOrderSchema, OrderResponseSchema, OrderStatus
from app.services.order_service import create_order, get_order, update_order_status
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=OrderResponseSchema, status_code=status.HTTP_201_CREATED)
async def place_order(data: CreateOrderSchema):
    """
    Place a new food order.
    Called by the WhatsApp bot after collecting customer details.
    """
    try:
        order = await create_order(data)
        return order
    except Exception as e:
        logger.error(f"Order creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to place order. Please try again.",
        )


@router.get("/{order_id}", response_model=OrderResponseSchema)
async def fetch_order(order_id: str):
    """Get order details by ID."""
    order = await get_order(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    return order


@router.patch("/{order_id}/status")
async def patch_order_status(order_id: str, status_value: OrderStatus):
    """
    Update order status.
    Used by restaurant staff to update order progress.
    """
    success = await update_order_status(order_id, status_value)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or update failed",
        )
    return {"message": f"Order status updated to {status_value.value}"}
