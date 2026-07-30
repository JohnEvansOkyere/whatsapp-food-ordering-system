from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.schemas.auth import StaffPrincipalSchema
from app.schemas.branch import PublicBranchListSchema, PublicBranchSchema
from app.schemas.order import (
    AdminOrderDetailSchema,
    AdminOrderListResponseSchema,
    CancelOrderSchema,
    OrderStatus,
    UpdateOrderStatusSchema,
    UpdatePaymentSchema,
)
from app.services.menu_service import fetch_menu_items, update_menu_item_availability
from app.services.order_service import (
    cancel_order,
    get_order_detail,
    list_orders,
    update_order_payment,
    update_order_status,
)
from app.services.auth_service import ensure_branch_access, ensure_role, require_staff
from app.services.branch_service import fetch_public_branches, update_branch_ordering

router = APIRouter(prefix="/admin", tags=["admin"])


class UpdateMenuAvailabilitySchema(BaseModel):
    sold_out: bool | None = None
    active: bool | None = None


class UpdateBranchOrderingSchema(BaseModel):
    accepting_orders: bool


class NotificationRetrySchema(BaseModel):
    sent: bool


@router.get("/branches", response_model=PublicBranchListSchema)
async def get_staff_branches(
    staff: StaffPrincipalSchema = Depends(require_staff),
):
    branches = [
        branch
        for branch in await fetch_public_branches()
        if branch.id in staff.branch_ids
    ]
    return PublicBranchListSchema(items=branches)


@router.patch("/branches/{branch_id}", response_model=PublicBranchSchema)
async def patch_staff_branch(
    branch_id: str,
    payload: UpdateBranchOrderingSchema,
    staff: StaffPrincipalSchema = Depends(require_staff),
):
    ensure_branch_access(staff, branch_id)
    ensure_role(staff, "tenant_owner", "manager")
    branch = await update_branch_ordering(
        branch_id,
        accepting_orders=payload.accepting_orders,
    )
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    return branch


@router.get("/orders", response_model=AdminOrderListResponseSchema)
async def get_admin_orders(
    status: OrderStatus | None = None,
    branch_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    staff: StaffPrincipalSchema = Depends(require_staff),
):
    if branch_id:
        ensure_branch_access(staff, branch_id)
    elif len(staff.branch_ids) == 1:
        branch_id = staff.branch_ids[0]
    items = await list_orders(status=status, branch_id=branch_id, limit=limit)
    return AdminOrderListResponseSchema(items=items, total=len(items))


@router.get("/orders/{order_id}", response_model=AdminOrderDetailSchema)
async def get_admin_order(
    order_id: str,
    staff: StaffPrincipalSchema = Depends(require_staff),
):
    order = await get_order_detail(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    ensure_branch_access(staff, order.branch_id)
    return order


@router.patch("/orders/{order_id}/status", response_model=AdminOrderDetailSchema)
async def patch_admin_order_status(
    order_id: str,
    payload: UpdateOrderStatusSchema,
    staff: StaffPrincipalSchema = Depends(require_staff),
):
    existing = await get_order_detail(order_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Order not found")
    ensure_branch_access(staff, existing.branch_id)
    role_targets = {
        "tenant_owner": set(OrderStatus),
        "manager": set(OrderStatus),
        "kitchen": {
            OrderStatus.confirmed,
            OrderStatus.preparing,
            OrderStatus.ready,
            OrderStatus.rejected,
            OrderStatus.delayed,
        },
        "dispatch": {
            OrderStatus.out_for_delivery,
            OrderStatus.delivered,
            OrderStatus.delayed,
        },
        "support": {
            OrderStatus.cancel_requested,
            OrderStatus.cancelled,
            OrderStatus.delayed,
        },
    }
    if payload.status not in role_targets.get(staff.role, set()):
        raise HTTPException(
            status_code=403,
            detail="Your staff role cannot move an order to this status",
        )
    try:
        order = await update_order_status(
            order_id,
            payload.status,
            actor_label=f"{staff.display_name} ({staff.role})",
            reason_code=payload.reason_code,
            reason_note=payload.reason_note,
            eta_minutes=payload.eta_minutes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/orders/{order_id}/cancel", response_model=AdminOrderDetailSchema)
async def post_admin_order_cancel(
    order_id: str,
    payload: CancelOrderSchema,
    staff: StaffPrincipalSchema = Depends(require_staff),
):
    existing = await get_order_detail(order_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Order not found")
    ensure_branch_access(staff, existing.branch_id)
    ensure_role(staff, "tenant_owner", "manager", "support")
    try:
        payload.actor_label = f"{staff.display_name} ({staff.role})"
        order = await cancel_order(order_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/orders/{order_id}/payment", response_model=AdminOrderDetailSchema)
async def patch_admin_order_payment(
    order_id: str,
    payload: UpdatePaymentSchema,
    staff: StaffPrincipalSchema = Depends(require_staff),
):
    existing = await get_order_detail(order_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Order not found")
    ensure_branch_access(staff, existing.branch_id)
    ensure_role(staff, "tenant_owner", "manager", "cashier")
    try:
        order = await update_order_payment(
            order_id,
            payload,
            actor_label=f"{staff.display_name} ({staff.role})",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post(
    "/orders/{order_id}/notifications/retry",
    response_model=NotificationRetrySchema,
)
async def retry_admin_order_notification(
    order_id: str,
    staff: StaffPrincipalSchema = Depends(require_staff),
):
    order = await get_order_detail(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    ensure_branch_access(staff, order.branch_id)
    ensure_role(staff, "tenant_owner", "manager", "support")

    status_event_types = {
        "order_created",
        "order_confirmed",
        "order_preparing",
        "order_ready",
        "order_dispatched",
        "order_delayed",
        "order_delivered",
        "cancellation_requested",
        "order_cancelled",
        "order_rejected",
    }
    event = next(
        (
            item
            for item in reversed(order.events)
            if item.event_type in status_event_types
        ),
        None,
    )
    from app.services.notification_service import notify_order_status_changed

    sent = await notify_order_status_changed(
        order,
        order_event_id=event.id if event else None,
    )
    return NotificationRetrySchema(sent=sent)


@router.get("/menu")
async def get_admin_menu(
    branch_id: str | None = None,
    staff: StaffPrincipalSchema = Depends(require_staff),
):
    if branch_id:
        ensure_branch_access(staff, branch_id)
    elif len(staff.branch_ids) == 1:
        branch_id = staff.branch_ids[0]
    items = await fetch_menu_items(
        include_inactive=True,
        include_sold_out=True,
        branch_id=branch_id,
    )
    return {"items": items}


@router.patch("/menu/{item_id}")
async def patch_admin_menu_item(
    item_id: str,
    payload: UpdateMenuAvailabilitySchema,
    branch_id: str = Query(...),
    staff: StaffPrincipalSchema = Depends(require_staff),
):
    ensure_branch_access(staff, branch_id)
    ensure_role(staff, "tenant_owner", "manager", "kitchen")
    try:
        item = await update_menu_item_availability(
            item_id,
            sold_out=payload.sold_out,
            active=payload.active,
            branch_id=branch_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return item
