from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.schemas.branch import PublicBranchListSchema
from app.schemas.order import (
    CreateOrderSchema,
    OrderFeedbackResponseSchema,
    OrderFeedbackSchema,
    OrderResponseSchema,
    OrderTrackingResponseSchema,
)
from app.services.branch_service import fetch_public_branches, get_public_branch
from app.services.menu_service import fetch_menu_items
from app.services.order_service import create_order, get_order_tracking, submit_order_feedback

router = APIRouter(prefix="/public", tags=["public"])


class AnalyticsEventSchema(BaseModel):
    event_name: str = Field(..., min_length=2, max_length=60)
    branch_id: str | None = Field(default=None, max_length=100)
    anonymous_session_id: str | None = Field(default=None, max_length=100)
    metadata: dict = Field(default_factory=dict)


@router.get("/branches", response_model=PublicBranchListSchema)
async def get_public_branches():
    return PublicBranchListSchema(items=await fetch_public_branches())


@router.get("/menu")
async def get_public_menu(branch_id: str | None = Query(default=None)):
    if branch_id:
        branch = await get_public_branch(branch_id)
        if not branch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Branch not found",
            )
        if not branch.accepting_orders:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This branch is not accepting orders right now",
            )
        branch_id = branch.id

    items = (
        await fetch_menu_items(branch_id=branch_id, include_sold_out=True)
        if branch_id
        else await fetch_menu_items(include_sold_out=True)
    )
    return {"items": items}


@router.post(
    "/orders",
    response_model=OrderResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_public_order(data: CreateOrderSchema):
    try:
        if not data.branch_id:
            raise ValueError("Please select Ashesi University or Abelemkpe")
        branch = await get_public_branch(data.branch_id)
        if not branch:
            raise ValueError("Selected branch was not found")
        if not branch.accepting_orders:
            raise ValueError(f"{branch.name} is not accepting orders right now")
        data.branch_id = branch.id
        return await create_order(data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get(
    "/orders/{tracking_reference}",
    response_model=OrderTrackingResponseSchema,
)
async def get_public_order_tracking(tracking_reference: str):
    order = await get_order_tracking(tracking_reference)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tracking link not found",
        )
    return order


@router.post(
    "/orders/{tracking_reference}/feedback",
    response_model=OrderFeedbackResponseSchema,
)
async def post_public_order_feedback(
    tracking_reference: str,
    payload: OrderFeedbackSchema,
):
    try:
        accepted = await submit_order_feedback(tracking_reference, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return OrderFeedbackResponseSchema(accepted=accepted)


@router.post("/analytics", status_code=status.HTTP_202_ACCEPTED)
async def post_public_analytics(payload: AnalyticsEventSchema):
    allowed_events = {
        "branch_selected",
        "menu_item_added",
        "checkout_completed",
        "tracking_opened",
    }
    if payload.event_name not in allowed_events:
        raise HTTPException(status_code=400, detail="Unknown analytics event")
    if payload.branch_id:
        branch = await get_public_branch(payload.branch_id)
        if not branch:
            raise HTTPException(status_code=400, detail="Unknown analytics branch")
        payload.branch_id = branch.id

    allowed_metadata = {
        "branch",
        "item_id",
        "item_name",
        "order_total",
        "payment_method",
        "order_status",
    }
    safe_metadata = {
        key: value
        for key, value in payload.metadata.items()
        if key in allowed_metadata
        and isinstance(value, (str, int, float, bool))
        and (not isinstance(value, str) or len(value) <= 120)
    }

    from app.database import get_supabase

    try:
        get_supabase().table("analytics_events").insert(
            {
                "event_name": payload.event_name,
                "branch_id": payload.branch_id,
                "anonymous_session_id": payload.anonymous_session_id,
                "metadata_json": safe_metadata,
            }
        ).execute()
    except Exception:
        # Analytics must never block ordering or tracking.
        pass
    return {"accepted": True}
