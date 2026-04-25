from fastapi import APIRouter, HTTPException, status

from app.schemas.order import CreateOrderSchema, OrderResponseSchema, OrderTrackingResponseSchema
from app.services.menu_service import fetch_menu_items
from app.services.order_service import create_order, get_order_tracking

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/menu")
async def get_public_menu():
    items = await fetch_menu_items()
    return {"items": items}


@router.post(
    "/orders",
    response_model=OrderResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_public_order(data: CreateOrderSchema):
    try:
        return await create_order(data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/orders/{tracking_code}",
    response_model=OrderTrackingResponseSchema,
)
async def get_public_order_tracking(tracking_code: str):
    order = await get_order_tracking(tracking_code)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tracking code not found",
        )
    return order
