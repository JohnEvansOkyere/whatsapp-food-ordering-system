"""
Legacy order routes kept for compatibility during the public/admin API cutover.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.order import CreateOrderSchema, OrderResponseSchema, OrderStatus
from app.services.order_service import create_order, get_order, update_order_status

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orders", tags=["legacy-orders"])


@router.post(
    "/",
    response_model=OrderResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Place a new order",
)
async def place_order(data: CreateOrderSchema):
    try:
        return await create_order(data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.error("Order creation error: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to place order. Please try again.",
        ) from exc


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
)
async def patch_order_status(order_id: str, new_status: OrderStatus):
    try:
        order = await update_order_status(order_id, new_status, actor_label="legacy-route")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found or update failed",
        )
    return {"message": f"Status updated to {order.status.value}"}
