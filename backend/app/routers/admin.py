from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.schemas.order import (
    AdminOrderDetailSchema,
    AdminOrderListResponseSchema,
    CancelOrderSchema,
    OrderStatus,
    UpdateOrderStatusSchema,
)
from app.services.menu_service import fetch_menu_items, update_menu_item_availability
from app.services.order_service import cancel_order, get_order_detail, list_orders, update_order_status

router = APIRouter(prefix="/admin", tags=["admin"])


class UpdateMenuAvailabilitySchema(BaseModel):
    sold_out: bool | None = None
    active: bool | None = None


@router.get("/orders", response_model=AdminOrderListResponseSchema)
async def get_admin_orders(
    status: OrderStatus | None = None,
    branch_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
):
    items = await list_orders(status=status, branch_id=branch_id, limit=limit)
    return AdminOrderListResponseSchema(items=items, total=len(items))


@router.get("/orders/{order_id}", response_model=AdminOrderDetailSchema)
async def get_admin_order(order_id: str):
    order = await get_order_detail(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/orders/{order_id}/status", response_model=AdminOrderDetailSchema)
async def patch_admin_order_status(order_id: str, payload: UpdateOrderStatusSchema):
    try:
        order = await update_order_status(
            order_id,
            payload.status,
            actor_label=payload.actor_label,
            reason_code=payload.reason_code,
            reason_note=payload.reason_note,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/orders/{order_id}/cancel", response_model=AdminOrderDetailSchema)
async def post_admin_order_cancel(order_id: str, payload: CancelOrderSchema):
    try:
        order = await cancel_order(order_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.get("/menu")
async def get_admin_menu():
    items = await fetch_menu_items(include_inactive=True, include_sold_out=True)
    return {"items": items}


@router.patch("/menu/{item_id}")
async def patch_admin_menu_item(item_id: str, payload: UpdateMenuAvailabilitySchema):
    try:
        item = await update_menu_item_availability(
            item_id,
            sold_out=payload.sold_out,
            active=payload.active,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return item
