"""
Orders router.

POST /orders        — Place a new order (called by the menu web app checkout)
GET  /orders/{id}   — Fetch order by ID
PATCH /orders/{id}/status — Update order status (for restaurant staff)
"""

import logging
from fastapi import APIRouter, HTTPException, status
from app.schemas.order import CreateOrderSchema, OrderResponseSchema, OrderStatus
from app.services.order_service import create_order, get_order, update_order_status

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orders", tags=["orders"])


@router.post(
    "/",
    response_model=OrderResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Place a new order",
    description="Called by the menu web app when the customer confirms their cart. "
                "Saves to DB and fires WhatsApp receipt + owner notification automatically.",
)
async def place_order(data: CreateOrderSchema):
    try:
        order = await create_order(data)
        return order
    except Exception as e:
        logger.error(f"Order creation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to place order. Please try again.",
        )


@router.get(
    "/{order_id}",
    response_model=OrderResponseSchema,
    summary="Get order by ID",
)
async def fetch_order(order_id: str):
    order = await get_order(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )
    return order


@router.patch(
    "/{order_id}/status",
    summary="Update order status",
    description="Used by restaurant staff to update order progress.",
)
async def patch_order_status(order_id: str, new_status: OrderStatus):
    success = await update_order_status(order_id, new_status)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or update failed",
        )
    return {"message": f"Status updated to {new_status.value}"}
