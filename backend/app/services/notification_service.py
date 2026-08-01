"""Persistent customer notification orchestration."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable

from app.database import get_supabase
from app.schemas.order import AdminOrderDetailSchema, OrderResponseSchema
from app.services.sms import (
    send_order_receipt_sms,
    send_order_status_sms,
)
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
    channel: str = "whatsapp",
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
            .eq("channel", channel)
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
                    "channel": channel,
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
            "Could not persist %s notification attempt for order %s: %s",
            channel,
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
            update_payload["error_message"] = f"{channel} send failed"
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


async def _fan_out(
    order: OrderResponseSchema,
    *,
    order_event_id: str | None,
    notification_type: str,
    whatsapp_send: Callable[[OrderResponseSchema], Awaitable[bool]],
    sms_send: Callable[[OrderResponseSchema], Awaitable[bool]],
) -> bool:
    """
    Deliver the same event over WhatsApp and SMS.

    Each channel has its own outbox row (the unique index is on
    order_event_id + channel + notification_type), so they retry and dedupe
    independently and one channel failing never suppresses the other.
    Returns the WhatsApp result, which is what `whatsapp_receipt_sent` reports.
    """
    whatsapp_result, sms_result = await asyncio.gather(
        _send_with_outbox(
            order,
            order_event_id=order_event_id,
            notification_type=notification_type,
            send=whatsapp_send,
            channel="whatsapp",
        ),
        _send_with_outbox(
            order,
            order_event_id=order_event_id,
            notification_type=notification_type,
            send=sms_send,
            channel="sms",
        ),
        return_exceptions=True,
    )

    for channel, result in (("whatsapp", whatsapp_result), ("sms", sms_result)):
        if isinstance(result, BaseException):
            logger.error(
                "%s notification raised for order %s: %s", channel, order.id, result
            )

    return whatsapp_result is True


async def notify_order_created(
    order: OrderResponseSchema,
    *,
    order_event_id: str | None,
) -> bool:
    return await _fan_out(
        order,
        order_event_id=order_event_id,
        notification_type="order_created_receipt",
        whatsapp_send=send_order_receipt_to_customer,
        sms_send=send_order_receipt_sms,
    )


async def notify_order_status_changed(
    order: AdminOrderDetailSchema,
    *,
    order_event_id: str | None,
) -> bool:
    return await _fan_out(
        order,
        order_event_id=order_event_id,
        notification_type=f"order_{order.status.value}",
        whatsapp_send=send_order_status_update_to_customer,
        sms_send=send_order_status_sms,
    )
