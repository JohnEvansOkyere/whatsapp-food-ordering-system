"""Persistent customer notification orchestration."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable

from app.database import get_supabase
from app.schemas.order import AdminOrderDetailSchema, OrderResponseSchema
from app.services.whatsapp import (
    send_order_receipt_to_customer,
    send_order_status_update_to_customer,
)

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _send_with_outbox(
    order: OrderResponseSchema,
    *,
    order_event_id: str | None,
    notification_type: str,
    send: Callable[[OrderResponseSchema], Awaitable[bool]],
) -> bool:
    supabase = get_supabase()
    notification_id: str | None = None
    now = _now_iso()

    payload = {
        "order_number": order.order_number,
        "status": order.status.value,
        "branch_name": order.branch_name,
        "tracking_url": order.tracking_url,
    }

    try:
        existing_result = (
            supabase.table("notification_events")
            .select("*")
            .eq("order_event_id", order_event_id)
            .eq("channel", "whatsapp")
            .eq("notification_type", notification_type)
            .limit(1)
            .execute()
        )
        if existing_result.data:
            existing = existing_result.data[0]
            if existing.get("status") in {"sent", "delivered", "read"}:
                return True
            notification_id = str(existing["id"])
            previous_attempts = int(existing.get("attempt_count") or 0)
        else:
            previous_attempts = 0
        result = (
            supabase.table("notification_events")
            .insert(
                {
                    "tenant_id": getattr(order, "tenant_id", None),
                    "branch_id": order.branch_id,
                    "order_id": order.id,
                    "order_event_id": order_event_id,
                    "channel": "whatsapp",
                    "notification_type": notification_type,
                    "recipient": order.customer_phone,
                    "status": "pending",
                    "attempt_count": 0,
                    "payload_json": payload,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            .execute()
            if not notification_id
            else None
        )
        if result and result.data:
            notification_id = str(result.data[0]["id"])
    except Exception as exc:
        logger.warning(
            "Could not persist WhatsApp notification attempt for order %s: %s",
            order.id,
            exc,
        )

        previous_attempts = 0

    sent = False
    attempts_this_run = 0
    for attempt in range(3):
        attempts_this_run += 1
        sent = await send(order)
        if sent:
            break
        if attempt < 2:
            await asyncio.sleep(0.25 * (2**attempt))

    if notification_id:
        update_payload = {
            "status": "sent" if sent else "failed",
            "attempt_count": previous_attempts + attempts_this_run,
            "last_attempt_at": _now_iso(),
            "updated_at": _now_iso(),
        }
        if sent:
            update_payload["sent_at"] = _now_iso()
        else:
            update_payload["error_message"] = "WhatsApp send failed"
        try:
            (
                supabase.table("notification_events")
                .update(update_payload)
                .eq("id", notification_id)
                .execute()
            )
        except Exception as exc:
            logger.warning(
                "Could not update notification result for order %s: %s",
                order.id,
                exc,
            )

    return sent


async def notify_order_created(
    order: OrderResponseSchema,
    *,
    order_event_id: str | None,
) -> bool:
    return await _send_with_outbox(
        order,
        order_event_id=order_event_id,
        notification_type="order_created_receipt",
        send=send_order_receipt_to_customer,
    )


async def notify_order_status_changed(
    order: AdminOrderDetailSchema,
    *,
    order_event_id: str | None,
) -> bool:
    return await _send_with_outbox(
        order,
        order_event_id=order_event_id,
        notification_type=f"order_{order.status.value}",
        send=send_order_status_update_to_customer,
    )
