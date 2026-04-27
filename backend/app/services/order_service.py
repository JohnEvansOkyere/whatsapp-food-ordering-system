"""
Production-style order service.

The service writes both compatibility JSON and normalized order tables while
enforcing deterministic pricing and backend-owned state transitions.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone

from app.database import get_supabase
from app.schemas.order import (
    AdminOrderDetailSchema,
    AdminOrderListItemSchema,
    CancelOrderSchema,
    CreateOrderSchema,
    OrderEventSchema,
    OrderItemInputSchema,
    OrderItemSchema,
    OrderResponseSchema,
    OrderStatus,
    OrderTrackingEventSchema,
    OrderTrackingResponseSchema,
    PaymentMethod,
    PaymentStatus,
)
from app.services.customer_service import upsert_customer
from app.services.menu_service import fetch_menu_items, normalize_price
from app.services.whatsapp import (
    send_order_notification_to_owner,
    send_order_receipt_to_customer,
)

logger = logging.getLogger(__name__)

STATUS_LABELS: dict[str, str] = {
    "pending": "Order received",
    "new": "Order received",
    "confirmed": "Confirmed",
    "preparing": "Being prepared",
    "ready": "Ready",
    "out_for_delivery": "Out for delivery",
    "delivered": "Delivered",
    "cancel_requested": "Cancellation requested",
    "cancelled": "Cancelled",
    "rejected": "Rejected",
}

ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "new": {"confirmed", "rejected", "cancel_requested", "cancelled"},
    "confirmed": {"preparing", "cancel_requested", "cancelled"},
    "preparing": {"ready", "cancel_requested"},
    "ready": {"out_for_delivery", "delivered", "cancel_requested"},
    "out_for_delivery": {"delivered", "cancel_requested"},
    "cancel_requested": {"cancelled", "confirmed", "preparing", "ready", "out_for_delivery"},
    "cancelled": set(),
    "rejected": set(),
    "delivered": set(),
}

STATUS_EVENT_TYPES: dict[str, str] = {
    "new": "order_created",
    "confirmed": "order_confirmed",
    "preparing": "order_preparing",
    "ready": "order_ready",
    "out_for_delivery": "order_dispatched",
    "delivered": "order_delivered",
    "cancel_requested": "cancellation_requested",
    "cancelled": "order_cancelled",
    "rejected": "order_rejected",
}


def _is_schema_compatibility_error(exc: Exception) -> bool:
    message = str(exc)
    markers = [
        "schema cache",
        "Could not find the",
        "column of 'orders'",
        "column of 'order_items'",
        "column of 'order_events'",
        "column of 'customers'",
    ]
    return any(marker in message for marker in markers)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_float(value: object) -> float:
    if value is None:
        return 0.0
    return float(value)


def _normalize_status(value: str | OrderStatus | None) -> OrderStatus:
    raw = value.value if isinstance(value, OrderStatus) else str(value or OrderStatus.new.value)
    if raw == OrderStatus.pending.value:
        raw = OrderStatus.new.value
    return OrderStatus(raw)


def get_allowed_next_statuses(status: str | OrderStatus) -> list[OrderStatus]:
    normalized = _normalize_status(status).value
    return [OrderStatus(next_status) for next_status in sorted(ALLOWED_STATUS_TRANSITIONS[normalized])]


def get_status_label(status: str | OrderStatus) -> str:
    normalized = _normalize_status(status).value
    return STATUS_LABELS.get(normalized, normalized.replace("_", " ").title())


def _initial_payment_status(method: PaymentMethod) -> PaymentStatus:
    if method == PaymentMethod.cash:
        return PaymentStatus.pending
    return PaymentStatus.unpaid


def _build_order_number() -> str:
    return f"ORD-{uuid.uuid4().hex[:8].upper()}"


def _build_tracking_code() -> str:
    return f"TRK-{uuid.uuid4().hex[:10].upper()}"


async def _resolve_priced_items(items: list[OrderItemInputSchema]) -> list[OrderItemSchema]:
    menu_items = await fetch_menu_items()
    menu_by_id = {str(item["id"]): item for item in menu_items if item.get("id")}

    resolved: list[OrderItemSchema] = []
    for item in items:
        menu_row = menu_by_id.get(item.item_id)
        if not menu_row:
            raise ValueError(f"Unknown menu item: {item.item_id}")

        quantity = max(1, int(item.quantity))
        unit_price = normalize_price(menu_row)
        total_price = round(unit_price * quantity, 2)

        resolved.append(
            OrderItemSchema(
                item_id=str(menu_row["id"]),
                name=str(menu_row["name"]),
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price,
            )
        )
    return resolved


def _build_legacy_items(items: list[OrderItemSchema]) -> list[dict[str, object]]:
    return [
        {
            "item_id": item.item_id,
            "name": item.name,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "total_price": item.total_price,
        }
        for item in items
    ]


def _map_order_item_rows(rows: list[dict]) -> list[OrderItemSchema]:
    return [
        OrderItemSchema(
            item_id=str(row.get("menu_item_id") or row.get("item_id") or ""),
            name=str(row.get("item_name_snapshot") or row.get("name") or "Unknown item"),
            quantity=int(row.get("quantity", 1)),
            unit_price=_to_float(row.get("unit_price")),
            total_price=_to_float(row.get("line_total") or row.get("total_price")),
        )
        for row in rows
    ]


def _map_legacy_order_items(rows: list[dict]) -> list[OrderItemSchema]:
    return [
        OrderItemSchema(
            item_id=str(row.get("item_id") or row.get("id") or ""),
            name=str(row.get("name") or "Unknown item"),
            quantity=int(row.get("quantity", 1)),
            unit_price=_to_float(row.get("unit_price")),
            total_price=_to_float(row.get("total_price")),
        )
        for row in rows
    ]


async def _fetch_order_items(order_id: str, legacy_items: list[dict] | None = None) -> list[OrderItemSchema]:
    supabase = get_supabase()
    result = (
        supabase.table("order_items")
        .select("*")
        .eq("order_id", order_id)
        .order("created_at")
        .execute()
    )
    if result.data:
        return _map_order_item_rows(result.data)
    return _map_legacy_order_items(legacy_items or [])


async def _fetch_order_events(order_id: str) -> list[OrderEventSchema]:
    supabase = get_supabase()
    result = (
        supabase.table("order_events")
        .select("*")
        .eq("order_id", order_id)
        .order("created_at")
        .execute()
    )
    rows = result.data or []
    return [
        OrderEventSchema(
            id=str(row["id"]),
            event_type=str(row["event_type"]),
            from_status=_normalize_status(row["from_status"]) if row.get("from_status") else None,
            to_status=_normalize_status(row["to_status"]) if row.get("to_status") else None,
            actor_type=str(row.get("actor_type") or "system"),
            actor_label=row.get("actor_label"),
            reason_code=row.get("reason_code"),
            reason_note=row.get("reason_note"),
            created_at=datetime.fromisoformat(str(row["created_at"])),
        )
        for row in rows
    ]


def _build_order_response(row: dict, items: list[OrderItemSchema]) -> OrderResponseSchema:
    created_at = row.get("placed_at") or row.get("created_at") or _now_iso()
    return OrderResponseSchema(
        id=str(row["id"]),
        order_number=row.get("order_number"),
        tracking_code=row.get("tracking_code"),
        customer_phone=str(row.get("customer_phone_snapshot") or row.get("customer_phone") or ""),
        customer_name=row.get("customer_name_snapshot") or row.get("customer_name"),
        delivery_address=str(
            row.get("delivery_address_snapshot") or row.get("delivery_address") or ""
        ),
        items=items,
        subtotal_amount=_to_float(row.get("subtotal_amount") or row.get("total_amount")),
        total_amount=_to_float(row.get("total_amount")),
        payment_method=PaymentMethod(str(row.get("payment_method") or PaymentMethod.cash.value)),
        payment_status=PaymentStatus(str(row.get("payment_status") or PaymentStatus.unpaid.value)),
        status=_normalize_status(row.get("status")),
        channel=str(row.get("channel") or "web"),
        fulfillment_type=str(row.get("fulfillment_type") or "delivery"),
        notes=row.get("notes"),
        created_at=datetime.fromisoformat(str(created_at)),
    )


async def _get_order_row_by_id(order_id: str) -> dict | None:
    supabase = get_supabase()
    result = supabase.table("orders").select("*").eq("id", order_id).limit(1).execute()
    if result.data:
        return result.data[0]
    return None


async def _get_order_row_by_tracking_code(tracking_code: str) -> dict | None:
    supabase = get_supabase()
    result = (
        supabase.table("orders")
        .select("*")
        .eq("tracking_code", tracking_code)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]
    return None


async def _get_order_row_by_order_number(order_number: str) -> dict | None:
    supabase = get_supabase()
    result = (
        supabase.table("orders")
        .select("*")
        .eq("order_number", order_number)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]
    return None


def _normalize_reference(reference: str) -> str:
    cleaned = reference.strip().upper()
    cleaned = re.sub(r"[^A-Z0-9\-]", "", cleaned)
    return cleaned


def _reference_candidates(reference: str) -> list[str]:
    normalized = _normalize_reference(reference)
    if not normalized:
        return []

    candidates = [normalized]
    if normalized.startswith("ORDER"):
        trimmed = normalized.replace("ORDER", "", 1).lstrip("-#")
        if trimmed:
            candidates.append(trimmed)
    if not normalized.startswith("ORD-"):
        candidates.append(f"ORD-{normalized}")
    if not normalized.startswith("TRK-"):
        candidates.append(f"TRK-{normalized}")

    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.add(candidate)
            deduped.append(candidate)
    return deduped


async def get_order_detail_by_reference(reference: str) -> AdminOrderDetailSchema | None:
    candidates = _reference_candidates(reference)
    if not candidates:
        return None

    for candidate in candidates:
        tracking_row = await _get_order_row_by_tracking_code(candidate)
        if tracking_row:
            return await get_order_detail(str(tracking_row["id"]))

        order_row = await _get_order_row_by_order_number(candidate)
        if order_row:
            return await get_order_detail(str(order_row["id"]))

        if re.fullmatch(r"[0-9A-F\-]{8,36}", candidate):
            by_id = await _get_order_row_by_id(candidate)
            if by_id:
                return await get_order_detail(str(by_id["id"]))

    short_ref = candidates[0].replace("ORD-", "").replace("TRK-", "")
    supabase = get_supabase()
    result = supabase.table("orders").select("*").order("created_at", desc=True).limit(200).execute()
    rows = result.data or []
    for row in rows:
        order_number = str(row.get("order_number") or "").upper()
        tracking_code = str(row.get("tracking_code") or "").upper()
        order_id = str(row.get("id") or "").upper()
        if (
            short_ref
            and (
                order_number.endswith(short_ref)
                or tracking_code.endswith(short_ref)
                or order_id.startswith(short_ref)
            )
        ):
            return await get_order_detail(str(row["id"]))
    return None


async def _create_order_event(
    *,
    order_row: dict,
    event_type: str,
    from_status: str | None,
    to_status: str | None,
    actor_type: str,
    actor_label: str | None = None,
    reason_code: str | None = None,
    reason_note: str | None = None,
    metadata_json: dict | None = None,
) -> None:
    supabase = get_supabase()
    supabase.table("order_events").insert(
        {
            "tenant_id": order_row.get("tenant_id"),
            "branch_id": order_row.get("branch_id"),
            "order_id": order_row["id"],
            "event_type": event_type,
            "from_status": from_status,
            "to_status": to_status,
            "actor_type": actor_type,
            "actor_label": actor_label,
            "reason_code": reason_code,
            "reason_note": reason_note,
            "metadata_json": metadata_json or {},
            "created_at": _now_iso(),
        }
    ).execute()


async def create_order(data: CreateOrderSchema) -> OrderResponseSchema:
    """
    Create an order using canonical menu pricing, then write normalized line items
    and an audit event. The legacy `orders.items` JSON remains populated for
    compatibility during migration.
    """
    supabase = get_supabase()
    order_id = str(uuid.uuid4())
    now = _now_iso()
    resolved_items = await _resolve_priced_items(data.items)
    subtotal = round(sum(item.total_price for item in resolved_items), 2)

    order_row = {
        "id": order_id,
        "order_number": _build_order_number(),
        "tracking_code": _build_tracking_code(),
        "customer_phone": data.customer_phone,
        "customer_name": data.customer_name,
        "delivery_address": data.delivery_address,
        "items": _build_legacy_items(resolved_items),
        "total_amount": subtotal,
        "payment_method": data.payment_method.value,
        "status": OrderStatus.new.value,
        "notes": data.notes,
        "channel": data.channel,
        "payment_status": _initial_payment_status(data.payment_method).value,
        "fulfillment_type": data.fulfillment_type.value,
        "subtotal_amount": subtotal,
        "delivery_fee": 0,
        "discount_amount": 0,
        "currency": "GHS",
        "customer_name_snapshot": data.customer_name,
        "customer_phone_snapshot": data.customer_phone,
        "delivery_address_snapshot": data.delivery_address,
        "placed_at": now,
        "created_at": now,
    }
    if data.branch_id:
        order_row["branch_id"] = data.branch_id

    compatibility_mode = False
    try:
        result = supabase.table("orders").insert(order_row).execute()
        if not result.data:
            raise RuntimeError("Failed to insert order into Supabase")
        inserted_row = result.data[0]
    except Exception as exc:
        if not _is_schema_compatibility_error(exc):
            raise

        compatibility_mode = True
        logger.warning(
            "Falling back to legacy order insert because the database schema is behind the app code: %s",
            exc,
        )
        legacy_row = {
            "id": order_id,
            "customer_phone": data.customer_phone,
            "customer_name": data.customer_name,
            "delivery_address": data.delivery_address,
            "items": _build_legacy_items(resolved_items),
            "total_amount": subtotal,
            "payment_method": data.payment_method.value,
            "status": OrderStatus.pending.value,
            "notes": data.notes,
            "created_at": now,
        }
        legacy_result = supabase.table("orders").insert(legacy_row).execute()
        if not legacy_result.data:
            raise RuntimeError("Failed to insert legacy order into Supabase")
        inserted_row = legacy_result.data[0]

    try:
        customer = await upsert_customer(
            phone=data.customer_phone,
            name=data.customer_name,
            tenant_id=None if compatibility_mode else inserted_row.get("tenant_id"),
            default_branch_id=None if compatibility_mode else inserted_row.get("branch_id"),
        )
        if customer and customer.get("id") and not compatibility_mode:
            update_result = (
                supabase.table("orders")
                .update({"customer_id": customer["id"]})
                .eq("id", order_id)
                .execute()
            )
            if update_result.data:
                inserted_row = update_result.data[0]
            else:
                inserted_row["customer_id"] = customer["id"]
    except Exception as exc:
        logger.error("Customer upsert failed for order %s: %s", order_id, exc)

    if not compatibility_mode:
        normalized_items = [
            {
                "tenant_id": inserted_row.get("tenant_id"),
                "branch_id": inserted_row.get("branch_id"),
                "order_id": order_id,
                "menu_item_id": item.item_id,
                "item_name_snapshot": item.name,
                "unit_price": item.unit_price,
                "quantity": item.quantity,
                "line_total": item.total_price,
                "created_at": now,
            }
            for item in resolved_items
        ]
        if normalized_items:
            try:
                supabase.table("order_items").insert(normalized_items).execute()
            except Exception as exc:
                if _is_schema_compatibility_error(exc):
                    logger.warning("Skipping normalized order_items insert for legacy schema: %s", exc)
                    compatibility_mode = True
                else:
                    raise

    if not compatibility_mode:
        try:
            await _create_order_event(
                order_row=inserted_row,
                event_type=STATUS_EVENT_TYPES[OrderStatus.new.value],
                from_status=None,
                to_status=OrderStatus.new.value,
                actor_type="customer",
                actor_label=data.channel,
                metadata_json={"source": data.channel},
            )
        except Exception as exc:
            if _is_schema_compatibility_error(exc):
                logger.warning("Skipping order event insert for legacy schema: %s", exc)
            else:
                raise

    order = _build_order_response(inserted_row, resolved_items)

    try:
        await send_order_receipt_to_customer(order)
    except Exception as exc:
        logger.error("Receipt send failed for order %s: %s", order_id, exc)

    try:
        await send_order_notification_to_owner(order)
    except Exception as exc:
        logger.error("Owner notification failed for order %s: %s", order_id, exc)

    return order


async def get_order(order_id: str) -> OrderResponseSchema | None:
    """Legacy-compatible fetch by internal order ID."""
    row = await _get_order_row_by_id(order_id)
    if not row:
        return None

    items = await _fetch_order_items(order_id, row.get("items"))
    return _build_order_response(row, items)


async def get_order_detail(order_id: str) -> AdminOrderDetailSchema | None:
    row = await _get_order_row_by_id(order_id)
    if not row:
        return None

    items = await _fetch_order_items(order_id, row.get("items"))
    events = await _fetch_order_events(order_id)
    order = _build_order_response(row, items)

    return AdminOrderDetailSchema(
        **order.model_dump(),
        branch_id=row.get("branch_id"),
        tenant_id=row.get("tenant_id"),
        customer_id=row.get("customer_id"),
        allowed_next_statuses=get_allowed_next_statuses(order.status),
        events=events,
    )


async def list_orders(
    *,
    status: OrderStatus | None = None,
    branch_id: str | None = None,
    limit: int = 50,
) -> list[AdminOrderListItemSchema]:
    supabase = get_supabase()
    query = supabase.table("orders").select("*").order("created_at", desc=True).limit(limit)
    if branch_id:
        query = query.eq("branch_id", branch_id)

    result = query.execute()
    rows = result.data or []
    if status:
        desired = _normalize_status(status).value
        rows = [
            row
            for row in rows
            if _normalize_status(row.get("status")).value == desired
        ]

    return [
        AdminOrderListItemSchema(
            id=str(row["id"]),
            order_number=row.get("order_number"),
            tracking_code=row.get("tracking_code"),
            customer_name=row.get("customer_name_snapshot") or row.get("customer_name"),
            customer_phone=str(row.get("customer_phone_snapshot") or row.get("customer_phone") or ""),
            branch_id=row.get("branch_id"),
            status=_normalize_status(row.get("status")),
            payment_status=PaymentStatus(str(row.get("payment_status") or PaymentStatus.unpaid.value)),
            total_amount=_to_float(row.get("total_amount")),
            channel=str(row.get("channel") or "web"),
            created_at=datetime.fromisoformat(str(row.get("placed_at") or row.get("created_at"))),
        )
        for row in rows
    ]


async def update_order_status(
    order_id: str,
    new_status: OrderStatus,
    *,
    actor_label: str | None = None,
    reason_code: str | None = None,
    reason_note: str | None = None,
) -> AdminOrderDetailSchema | None:
    """Update an order status after validating the transition."""
    supabase = get_supabase()
    row = await _get_order_row_by_id(order_id)
    if not row:
        return None

    current_status = _normalize_status(row.get("status"))
    target_status = _normalize_status(new_status)
    if current_status == target_status:
        return await get_order_detail(order_id)

    allowed = ALLOWED_STATUS_TRANSITIONS[current_status.value]
    if target_status.value not in allowed:
        raise ValueError(
            f"Invalid status transition: {current_status.value} -> {target_status.value}"
        )

    now = _now_iso()
    update_data: dict[str, object] = {
        "status": target_status.value,
        "updated_at": now,
    }
    if target_status == OrderStatus.confirmed:
        update_data["confirmed_at"] = now
    if target_status == OrderStatus.delivered:
        update_data["delivered_at"] = now
    if target_status == OrderStatus.cancelled:
        update_data["cancelled_at"] = now

    result = (
        supabase.table("orders")
        .update(update_data)
        .eq("id", order_id)
        .execute()
    )
    if not result.data:
        return None

    updated_row = result.data[0]
    await _create_order_event(
        order_row=updated_row,
        event_type=STATUS_EVENT_TYPES[target_status.value],
        from_status=current_status.value,
        to_status=target_status.value,
        actor_type="staff",
        actor_label=actor_label or "admin-api",
        reason_code=reason_code,
        reason_note=reason_note,
        metadata_json={"source": "admin"},
    )

    return await get_order_detail(order_id)


async def cancel_order(order_id: str, payload: CancelOrderSchema) -> AdminOrderDetailSchema | None:
    row = await _get_order_row_by_id(order_id)
    if not row:
        return None

    current_status = _normalize_status(row.get("status"))
    if current_status in {OrderStatus.delivered, OrderStatus.cancelled, OrderStatus.rejected}:
        raise ValueError(f"Cannot cancel an order in {current_status.value} state")

    if current_status in {OrderStatus.new, OrderStatus.confirmed}:
        target_status = OrderStatus.cancelled
    else:
        target_status = OrderStatus.cancel_requested

    return await update_order_status(
        order_id,
        target_status,
        actor_label=payload.actor_label or "admin-api",
        reason_code=payload.reason_code,
        reason_note=payload.reason_note,
    )


async def get_order_tracking(tracking_code: str) -> OrderTrackingResponseSchema | None:
    row = await _get_order_row_by_tracking_code(tracking_code)
    if not row:
        return None

    events = await _fetch_order_events(str(row["id"]))
    if not events:
        events = [
            OrderEventSchema(
                id=f"synthetic-{row['id']}",
                event_type=STATUS_EVENT_TYPES[_normalize_status(row.get("status")).value],
                from_status=None,
                to_status=_normalize_status(row.get("status")),
                actor_type="system",
                actor_label=None,
                reason_code=None,
                reason_note=None,
                created_at=datetime.fromisoformat(str(row.get("placed_at") or row.get("created_at"))),
            )
        ]

    timeline = [
        OrderTrackingEventSchema(
            event_type=event.event_type,
            status=event.to_status,
            status_label=get_status_label(event.to_status or row.get("status")),
            created_at=event.created_at,
        )
        for event in events
    ]

    return OrderTrackingResponseSchema(
        tracking_code=str(row["tracking_code"]),
        order_number=row.get("order_number"),
        status=_normalize_status(row.get("status")),
        status_label=get_status_label(row.get("status")),
        placed_at=datetime.fromisoformat(str(row.get("placed_at") or row.get("created_at"))),
        customer_name=row.get("customer_name_snapshot") or row.get("customer_name"),
        timeline=timeline,
    )
