"""
Production-style order service.

The service writes both compatibility JSON and normalized order tables while
enforcing deterministic pricing and backend-owned state transitions.
"""

from __future__ import annotations

import logging
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from app.database import get_supabase
from app.config import get_settings
from app.schemas.order import (
    AdminOrderDetailSchema,
    AdminOrderListItemSchema,
    CancelOrderSchema,
    CreateOrderSchema,
    FulfillmentType,
    OrderEventSchema,
    OrderFeedbackSchema,
    OrderItemInputSchema,
    OrderItemSelectionSchema,
    OrderItemSchema,
    OrderResponseSchema,
    OrderListScope,
    OrderStatus,
    OrderTrackingEventSchema,
    OrderTrackingResponseSchema,
    PaymentMethod,
    PaymentStatus,
    UpdatePaymentSchema,
)
from app.services.customer_service import upsert_customer
from app.services.branch_service import get_public_branch
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
    "delayed": "Delayed",
    "delivered": "Delivered",
    "cancel_requested": "Cancellation requested",
    "cancelled": "Cancelled",
    "rejected": "Rejected",
}

ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "new": {"confirmed", "rejected", "cancel_requested", "cancelled", "delayed"},
    "confirmed": {"preparing", "cancel_requested", "cancelled", "delayed"},
    "preparing": {"ready", "cancel_requested", "delayed"},
    "ready": {"out_for_delivery", "delivered", "cancel_requested", "delayed"},
    "out_for_delivery": {"delivered", "cancel_requested", "delayed"},
    "delayed": {"confirmed", "preparing", "ready", "out_for_delivery", "cancel_requested", "cancelled"},
    "cancel_requested": {"cancelled", "confirmed", "preparing", "ready", "out_for_delivery"},
    "cancelled": set(),
    "rejected": set(),
    "delivered": set(),
}

ORDER_SCOPE_STATUSES: dict[OrderListScope, set[str]] = {
    OrderListScope.all: set(),
    OrderListScope.live: {
        "pending",
        "new",
        "confirmed",
        "preparing",
        "ready",
        "out_for_delivery",
    },
    OrderListScope.attention: {"delayed", "cancel_requested"},
    OrderListScope.closed: {"delivered", "cancelled", "rejected"},
}

STATUS_EVENT_TYPES: dict[str, str] = {
    "new": "order_created",
    "confirmed": "order_confirmed",
    "preparing": "order_preparing",
    "ready": "order_ready",
    "out_for_delivery": "order_dispatched",
    "delayed": "order_delayed",
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
        "Could not find the table 'public.payments'",
        'relation "public.payments" does not exist',
    ]
    return any(marker in message for marker in markers)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_float(value: object) -> float:
    if value is None:
        return 0.0
    return float(value)


def _to_optional_float(value: object) -> float | None:
    """Coordinates stay None when the address was typed rather than pinned."""
    if value is None or value == "":
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _normalize_status(value: str | OrderStatus | None) -> OrderStatus:
    raw = value.value if isinstance(value, OrderStatus) else str(value or OrderStatus.new.value)
    if raw == OrderStatus.pending.value:
        raw = OrderStatus.new.value
    return OrderStatus(raw)


def get_allowed_next_statuses(
    status: str | OrderStatus,
    *,
    fulfillment_type: str | FulfillmentType = FulfillmentType.delivery,
    resume_status: str | OrderStatus | None = None,
) -> list[OrderStatus]:
    normalized = _normalize_status(status).value
    allowed = set(ALLOWED_STATUS_TRANSITIONS[normalized])

    # Delivery orders must pass through dispatch. Pickup and dine-in orders have
    # no rider stage, so Ready can close directly instead.
    if normalized == OrderStatus.ready.value:
        fulfillment_value = (
            fulfillment_type.value
            if isinstance(fulfillment_type, FulfillmentType)
            else str(fulfillment_type)
        )
        fulfillment = FulfillmentType(fulfillment_value)
        if fulfillment == FulfillmentType.delivery:
            allowed.discard(OrderStatus.delivered.value)
        else:
            allowed.discard(OrderStatus.out_for_delivery.value)

    # Exceptions temporarily replace the visible status in the launch schema.
    # Only permit returning to the exact stage recorded on the exception event,
    # rather than asking staff to choose from every possible workflow stage.
    if normalized in {OrderStatus.delayed.value, OrderStatus.cancel_requested.value}:
        exception_actions = {OrderStatus.cancelled.value}
        if normalized == OrderStatus.delayed.value:
            exception_actions.add(OrderStatus.cancel_requested.value)
        allowed = exception_actions
        if resume_status is not None:
            allowed.add(_normalize_status(resume_status).value)

    return [OrderStatus(next_status) for next_status in sorted(allowed)]


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


def _build_public_tracking_token() -> str:
    return secrets.token_urlsafe(24)


def _build_tracking_url(row: dict) -> str | None:
    reference = row.get("public_tracking_token") or row.get("tracking_code")
    if not reference:
        return None
    base_url = get_settings().public_web_url.rstrip("/")
    return f"{base_url}/track/{reference}"


async def _resolve_priced_items(
    items: list[OrderItemInputSchema],
    *,
    branch_id: str | None = None,
) -> list[OrderItemSchema]:
    menu_items = await fetch_menu_items(branch_id=branch_id)
    menu_by_id = {str(item["id"]): item for item in menu_items if item.get("id")}

    resolved: list[OrderItemSchema] = []
    for item in items:
        menu_row = menu_by_id.get(item.item_id)
        if not menu_row:
            raise ValueError(f"Unknown menu item: {item.item_id}")

        quantity = max(1, int(item.quantity))
        unit_price = normalize_price(menu_row)
        option_groups = {
            str(group.get("id")): group
            for group in menu_row.get("option_groups", [])
        }
        resolved_selections: list[OrderItemSelectionSchema] = []
        group_counts: dict[str, int] = {}
        for selection in item.selections:
            group = option_groups.get(selection.group_id)
            if not group:
                raise ValueError(
                    f"Invalid option group for {menu_row['name']}: {selection.group_id}"
                )
            option = next(
                (
                    candidate
                    for candidate in group.get("options", [])
                    if str(candidate.get("id")) == selection.option_id
                ),
                None,
            )
            if not option:
                raise ValueError(
                    f"Invalid option for {menu_row['name']}: {selection.option_id}"
                )
            group_counts[selection.group_id] = group_counts.get(selection.group_id, 0) + 1
            max_selections = 1 if group.get("type") == "single" else int(
                group.get("max_selections") or 99
            )
            if group_counts[selection.group_id] > max_selections:
                raise ValueError(f"Too many selections for {group.get('name')}")
            option_price = normalize_price(option)
            unit_price += option_price
            resolved_selections.append(
                OrderItemSelectionSchema(
                    group_id=selection.group_id,
                    option_id=selection.option_id,
                    name=str(option.get("name") or selection.option_id),
                    price=option_price,
                )
            )
        total_price = round(unit_price * quantity, 2)

        resolved.append(
            OrderItemSchema(
                item_id=str(menu_row["id"]),
                name=str(menu_row["name"]),
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price,
                selections=resolved_selections,
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
            "selections": [selection.model_dump() for selection in item.selections],
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
            selections=[
                OrderItemSelectionSchema.model_validate(selection)
                for selection in (row.get("selections_json") or [])
            ],
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
            selections=[
                OrderItemSelectionSchema.model_validate(selection)
                for selection in (row.get("selections") or [])
            ],
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


def _build_order_response(
    row: dict,
    items: list[OrderItemSchema],
    *,
    branch_name: str | None = None,
) -> OrderResponseSchema:
    created_at = row.get("placed_at") or row.get("created_at") or _now_iso()
    return OrderResponseSchema(
        id=str(row["id"]),
        order_number=row.get("order_number"),
        tracking_code=row.get("tracking_code"),
        tracking_url=_build_tracking_url(row),
        branch_id=str(row["branch_id"]) if row.get("branch_id") else None,
        branch_name=branch_name,
        customer_phone=str(row.get("customer_phone_snapshot") or row.get("customer_phone") or ""),
        customer_name=row.get("customer_name_snapshot") or row.get("customer_name"),
        delivery_address=str(
            row.get("delivery_address_snapshot") or row.get("delivery_address") or ""
        ),
        delivery_latitude=_to_optional_float(row.get("delivery_latitude")),
        delivery_longitude=_to_optional_float(row.get("delivery_longitude")),
        items=items,
        subtotal_amount=_to_float(row.get("subtotal_amount") or row.get("total_amount")),
        delivery_fee=_to_float(row.get("delivery_fee")),
        total_amount=_to_float(row.get("total_amount")),
        payment_method=PaymentMethod(str(row.get("payment_method") or PaymentMethod.cash.value)),
        payment_status=PaymentStatus(str(row.get("payment_status") or PaymentStatus.unpaid.value)),
        status=_normalize_status(row.get("status")),
        channel=str(row.get("channel") or "web"),
        fulfillment_type=str(row.get("fulfillment_type") or "delivery"),
        notes=row.get("notes"),
        accepted_eta_minutes=(
            int(row["accepted_eta_minutes"])
            if row.get("accepted_eta_minutes") is not None
            else None
        ),
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


async def _get_order_row_by_tracking_reference(reference: str) -> dict | None:
    supabase = get_supabase()
    try:
        result = (
            supabase.table("orders")
            .select("*")
            .eq("public_tracking_token", reference)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None
    except Exception as exc:
        if not _is_schema_compatibility_error(exc):
            raise
        logger.warning("Public tracking token lookup unavailable: %s", exc)
        # Temporary compatibility for databases that have not yet applied the
        # opaque-token migration. Once the column exists, short tracking codes
        # are never accepted by the public endpoint.
        return await _get_order_row_by_tracking_code(reference.upper())


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
) -> str | None:
    supabase = get_supabase()
    result = supabase.table("order_events").insert(
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
    if result.data:
        return str(result.data[0]["id"])
    return None


async def create_order(data: CreateOrderSchema) -> OrderResponseSchema:
    """
    Create an order using canonical menu pricing, then write normalized line items
    and an audit event. The legacy `orders.items` JSON remains populated for
    compatibility during migration.
    """
    supabase = get_supabase()
    order_id = str(uuid.uuid4())
    now = _now_iso()
    if not data.branch_id:
        raise ValueError("Please select Ashesi University or Abelemkpe")
    branch = await get_public_branch(data.branch_id)
    if not branch:
        raise ValueError("Selected branch was not found")
    if branch and not branch.accepting_orders:
        raise ValueError(f"{branch.name} is not accepting orders right now")

    if data.idempotency_key:
        try:
            duplicate_result = (
                supabase.table("orders")
                .select("*")
                .eq("branch_id", branch.id)
                .eq("idempotency_key", data.idempotency_key)
                .limit(1)
                .execute()
            )
            if duplicate_result.data:
                duplicate_row = duplicate_result.data[0]
                duplicate_items = await _fetch_order_items(
                    str(duplicate_row["id"]),
                    duplicate_row.get("items"),
                )
                return _build_order_response(
                    duplicate_row,
                    duplicate_items,
                    branch_name=branch.name,
                )
        except Exception as exc:
            if not _is_schema_compatibility_error(exc):
                raise
            logger.warning("Order idempotency lookup unavailable: %s", exc)

    resolved_items = await _resolve_priced_items(
        data.items,
        branch_id=branch.id,
    )
    subtotal = round(sum(item.total_price for item in resolved_items), 2)
    delivery_fee = round(branch.delivery_fee, 2)
    if branch.minimum_order and subtotal < branch.minimum_order:
        raise ValueError(
            f"Minimum order for {branch.name} is GHS {branch.minimum_order:.2f}"
        )
    total = round(subtotal + delivery_fee, 2)

    order_row = {
        "id": order_id,
        "order_number": _build_order_number(),
        "tracking_code": _build_tracking_code(),
        "public_tracking_token": _build_public_tracking_token(),
        "idempotency_key": data.idempotency_key,
        "whatsapp_consent": data.whatsapp_consent,
        "tracking_expires_at": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
        "customer_phone": data.customer_phone,
        "customer_name": data.customer_name,
        "delivery_address": data.delivery_address,
        "delivery_latitude": data.delivery_latitude,
        "delivery_longitude": data.delivery_longitude,
        "delivery_place_id": data.delivery_place_id,
        "items": _build_legacy_items(resolved_items),
        "total_amount": total,
        "payment_method": data.payment_method.value,
        "status": OrderStatus.new.value,
        "notes": data.notes,
        "channel": data.channel,
        "payment_status": _initial_payment_status(data.payment_method).value,
        "fulfillment_type": data.fulfillment_type.value,
        "subtotal_amount": subtotal,
        "delivery_fee": delivery_fee,
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
        try:
            supabase.table("payments").insert(
                {
                    "order_id": order_id,
                    "provider": (
                        "cash"
                        if data.payment_method == PaymentMethod.cash
                        else "unconfigured_momo"
                    ),
                    "method": data.payment_method.value,
                    "status": _initial_payment_status(data.payment_method).value,
                    "amount": total,
                    "currency": "GHS",
                    "metadata_json": {"source": data.channel},
                    "created_at": now,
                    "updated_at": now,
                }
            ).execute()
        except Exception as exc:
            if _is_schema_compatibility_error(exc):
                logger.warning("Skipping payment record for legacy schema: %s", exc)
            else:
                raise

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
                "selections_json": [
                    selection.model_dump() for selection in item.selections
                ],
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

    creation_event_id: str | None = None
    if not compatibility_mode:
        try:
            creation_event_id = await _create_order_event(
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

    order = _build_order_response(
        inserted_row,
        resolved_items,
        branch_name=branch.name if branch else None,
    )

    try:
        if creation_event_id:
            from app.services.notification_service import notify_order_created

            order.whatsapp_receipt_sent = await notify_order_created(
                order,
                order_event_id=creation_event_id,
            )
        else:
            order.whatsapp_receipt_sent = await send_order_receipt_to_customer(order)
    except Exception as exc:
        order.whatsapp_receipt_sent = False
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
    branch = await get_public_branch(str(row["branch_id"])) if row.get("branch_id") else None
    return _build_order_response(
        row,
        items,
        branch_name=branch.name if branch else None,
    )


async def get_order_detail(order_id: str) -> AdminOrderDetailSchema | None:
    row = await _get_order_row_by_id(order_id)
    if not row:
        return None

    items = await _fetch_order_items(order_id, row.get("items"))
    events = await _fetch_order_events(order_id)
    branch = await get_public_branch(str(row["branch_id"])) if row.get("branch_id") else None
    order = _build_order_response(
        row,
        items,
        branch_name=branch.name if branch else None,
    )
    exception_event = next(
        (
            event
            for event in reversed(events)
            if event.to_status == order.status and event.from_status is not None
        ),
        None,
    )

    return AdminOrderDetailSchema(
        **order.model_dump(),
        tenant_id=row.get("tenant_id"),
        customer_id=row.get("customer_id"),
        allowed_next_statuses=get_allowed_next_statuses(
            order.status,
            fulfillment_type=order.fulfillment_type,
            resume_status=exception_event.from_status if exception_event else None,
        ),
        events=events,
    )


async def list_orders(
    *,
    status: OrderStatus | None = None,
    scope: OrderListScope = OrderListScope.all,
    branch_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    search: str | None = None,
) -> tuple[list[AdminOrderListItemSchema], int]:
    supabase = get_supabase()
    query = supabase.table("orders").select("*", count="exact")
    if branch_id:
        query = query.eq("branch_id", branch_id)

    if status:
        desired = _normalize_status(status).value
        statuses = [desired, OrderStatus.pending.value] if desired == OrderStatus.new.value else [desired]
        query = query.in_("status", statuses)
    elif ORDER_SCOPE_STATUSES[scope]:
        query = query.in_("status", sorted(ORDER_SCOPE_STATUSES[scope]))

    normalized_search = re.sub(r"[,()]", " ", search or "").strip()
    if normalized_search:
        pattern = f"%{normalized_search}%"
        query = query.or_(
            ",".join(
                [
                    f"order_number.ilike.{pattern}",
                    f"tracking_code.ilike.{pattern}",
                    f"customer_name_snapshot.ilike.{pattern}",
                    f"customer_phone_snapshot.ilike.{pattern}",
                ]
            )
        )

    result = (
        query
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    rows = result.data or []
    items = [
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
    return items, int(result.count if result.count is not None else len(items))


async def update_order_status(
    order_id: str,
    new_status: OrderStatus,
    *,
    actor_label: str | None = None,
    reason_code: str | None = None,
    reason_note: str | None = None,
    eta_minutes: int | None = None,
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

    resume_status: OrderStatus | None = None
    if current_status in {OrderStatus.delayed, OrderStatus.cancel_requested}:
        events = await _fetch_order_events(order_id)
        exception_event = next(
            (
                event
                for event in reversed(events)
                if event.to_status == current_status and event.from_status is not None
            ),
            None,
        )
        resume_status = exception_event.from_status if exception_event else None

    allowed = get_allowed_next_statuses(
        current_status,
        fulfillment_type=str(row.get("fulfillment_type") or FulfillmentType.delivery.value),
        resume_status=resume_status,
    )
    if target_status not in allowed:
        raise ValueError(
            f"Invalid status transition: {current_status.value} -> {target_status.value}"
        )
    if target_status in {
        OrderStatus.rejected,
        OrderStatus.cancel_requested,
        OrderStatus.cancelled,
        OrderStatus.delayed,
    } and not reason_code:
        raise ValueError(f"A reason is required for {target_status.value}")

    now = _now_iso()
    update_data: dict[str, object] = {
        "status": target_status.value,
        "updated_at": now,
    }
    if target_status == OrderStatus.confirmed:
        update_data["confirmed_at"] = now
        if eta_minutes is not None:
            update_data["accepted_eta_minutes"] = eta_minutes
    if target_status == OrderStatus.delivered:
        update_data["delivered_at"] = now
    if target_status == OrderStatus.out_for_delivery:
        update_data["dispatched_at"] = now
    if target_status == OrderStatus.cancelled:
        update_data["cancelled_at"] = now

    result = (
        supabase.table("orders")
        .update(update_data)
        .eq("id", order_id)
        .eq("status", row.get("status"))
        .execute()
    )
    if not result.data:
        raise ValueError(
            "This order changed on another staff screen. Refresh before trying again."
        )

    updated_row = result.data[0]
    order_event_id = await _create_order_event(
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

    order = await get_order_detail(order_id)
    if order:
        try:
            from app.services.notification_service import notify_order_status_changed

            await notify_order_status_changed(
                order,
                order_event_id=order_event_id,
            )
        except Exception as exc:
            logger.error(
                "Status notification failed for order %s: %s",
                order_id,
                exc,
            )
    return order


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


async def update_order_payment(
    order_id: str,
    payload: UpdatePaymentSchema,
    *,
    actor_label: str,
) -> AdminOrderDetailSchema | None:
    supabase = get_supabase()
    row = await _get_order_row_by_id(order_id)
    if not row:
        return None

    if (
        str(row.get("payment_method") or "") == PaymentMethod.momo.value
        and payload.status == PaymentStatus.paid
        and payload.provider == "manual"
        and not payload.provider_reference
    ):
        raise ValueError("A Mobile Money reference is required before marking paid")

    result = (
        supabase.table("orders")
        .update({"payment_status": payload.status.value, "updated_at": _now_iso()})
        .eq("id", order_id)
        .eq("payment_status", row.get("payment_status"))
        .execute()
    )
    if not result.data:
        raise ValueError("Payment state changed elsewhere. Refresh and try again.")

    supabase.table("payments").insert(
        {
            "order_id": order_id,
            "provider": payload.provider,
            "provider_reference": payload.provider_reference,
            "method": str(row.get("payment_method") or PaymentMethod.cash.value),
            "status": payload.status.value,
            "amount": _to_float(row.get("total_amount")),
            "currency": str(row.get("currency") or "GHS"),
            "metadata_json": {"actor": actor_label},
            "created_at": _now_iso(),
            "updated_at": _now_iso(),
        }
    ).execute()

    await _create_order_event(
        order_row=result.data[0],
        event_type="payment_updated",
        from_status=_normalize_status(row.get("status")).value,
        to_status=_normalize_status(row.get("status")).value,
        actor_type="staff",
        actor_label=actor_label,
        metadata_json={
            "payment_status": payload.status.value,
            "provider": payload.provider,
        },
    )
    return await get_order_detail(order_id)


async def get_order_tracking(tracking_reference: str) -> OrderTrackingResponseSchema | None:
    row = await _get_order_row_by_tracking_reference(tracking_reference)
    if not row:
        return None
    if row.get("tracking_expires_at"):
        expires_at = datetime.fromisoformat(str(row["tracking_expires_at"]))
        if expires_at <= datetime.now(timezone.utc):
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

    items = await _fetch_order_items(str(row["id"]), row.get("items"))
    branch = await get_public_branch(str(row["branch_id"])) if row.get("branch_id") else None

    return OrderTrackingResponseSchema(
        tracking_code=str(row["tracking_code"]),
        order_number=row.get("order_number"),
        status=_normalize_status(row.get("status")),
        status_label=get_status_label(row.get("status")),
        placed_at=datetime.fromisoformat(str(row.get("placed_at") or row.get("created_at"))),
        customer_name=row.get("customer_name_snapshot") or row.get("customer_name"),
        branch_name=branch.name if branch else None,
        branch_slug=branch.slug if branch else None,
        branch_phone=branch.phone if branch else None,
        eta_min_minutes=branch.eta_min_minutes if branch else None,
        eta_max_minutes=branch.eta_max_minutes if branch else None,
        accepted_eta_minutes=(
            int(row["accepted_eta_minutes"])
            if row.get("accepted_eta_minutes") is not None
            else None
        ),
        items=items,
        subtotal_amount=_to_float(row.get("subtotal_amount") or row.get("total_amount")),
        delivery_fee=_to_float(row.get("delivery_fee")),
        total_amount=_to_float(row.get("total_amount")),
        payment_status=PaymentStatus(
            str(row.get("payment_status") or PaymentStatus.unpaid.value)
        ),
        timeline=timeline,
    )


async def submit_order_feedback(
    tracking_reference: str,
    feedback: OrderFeedbackSchema,
) -> bool:
    row = await _get_order_row_by_tracking_reference(tracking_reference)
    if not row:
        raise ValueError("Tracking link not found")
    if _normalize_status(row.get("status")) != OrderStatus.delivered:
        raise ValueError("Feedback is available after delivery")

    supabase = get_supabase()
    existing = (
        supabase.table("order_feedback")
        .select("*")
        .eq("order_id", row["id"])
        .limit(1)
        .execute()
    )
    payload = {
        "rating": feedback.rating,
        "comment": feedback.comment,
        "updated_at": _now_iso(),
    }
    if existing.data:
        result = (
            supabase.table("order_feedback")
            .update(payload)
            .eq("id", existing.data[0]["id"])
            .execute()
        )
    else:
        result = (
            supabase.table("order_feedback")
            .insert({"order_id": row["id"], **payload, "created_at": _now_iso()})
            .execute()
        )
    return bool(result.data)
