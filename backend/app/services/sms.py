"""
Moolre SMS service.

Carries the order tracking link to the customer alongside the WhatsApp
receipt. SMS is charged per 160-character segment, so the message bodies here
are deliberately terse — the full itemised receipt stays on WhatsApp.
"""

from __future__ import annotations

import logging
import re

import httpx

from app.config import get_settings
from app.schemas.order import OrderResponseSchema
from app.services.logging_utils import mask_phone

logger = logging.getLogger(__name__)

GSM7_SEGMENT_LEN = 160
GSM7_MULTIPART_SEGMENT_LEN = 153

# Customer-facing labels for each order status, kept short for SMS.
_STATUS_LABELS = {
    "confirmed": "accepted by the kitchen",
    "preparing": "being prepared",
    "ready": "ready for dispatch",
    "out_for_delivery": "out for delivery",
    "delayed": "delayed - the branch is on it",
    "delivered": "delivered. Enjoy!",
    "cancel_requested": "cancellation requested",
    "cancelled": "cancelled",
    "rejected": "could not be accepted",
}

# Statuses that do not warrant spending an SMS segment.
_SILENT_STATUSES = {"new", "preparing", "ready"}


def normalise_ghana_msisdn(phone: str) -> str | None:
    """
    Normalise a Ghanaian number to bare international format: 233XXXXXXXXX.

    Accepts 0244123456, +233244123456, 233244123456 and spaced variants.
    Returns None when the input cannot be a Ghana mobile number.
    """
    if not phone:
        return None
    digits = re.sub(r"[^\d]", "", str(phone))
    if digits.startswith("00233"):
        digits = digits[2:]
    if digits.startswith("0") and len(digits) == 10:
        digits = "233" + digits[1:]
    if digits.startswith("233") and len(digits) == 12:
        return digits
    return None


def count_segments(body: str) -> int:
    """Number of SMS segments `body` will be billed as (GSM-7 assumed)."""
    length = len(body)
    if length == 0:
        return 0
    if length <= GSM7_SEGMENT_LEN:
        return 1
    return -(-length // GSM7_MULTIPART_SEGMENT_LEN)  # ceiling division


def _order_reference(order: OrderResponseSchema) -> str:
    return order.order_number or order.id[:8].upper()


def build_receipt_sms(order: OrderResponseSchema, restaurant_name: str) -> str:
    """Short order-confirmation SMS carrying the tracking link."""
    reference = _order_reference(order)
    branch = f" from {order.branch_name}" if order.branch_name else ""
    body = (
        f"{restaurant_name}: Order {reference}{branch} received. "
        f"Total GHS {order.total_amount:.2f}."
    )
    if order.tracking_url:
        body = f"{body} Track: {order.tracking_url}"
    return body


def build_status_sms(order: OrderResponseSchema, restaurant_name: str) -> str:
    """Short status-change SMS carrying the tracking link."""
    reference = _order_reference(order)
    status = order.status.value
    label = _STATUS_LABELS.get(status, status.replace("_", " "))
    body = f"{restaurant_name}: Order {reference} is {label}."
    if order.tracking_url:
        body = f"{body} Track: {order.tracking_url}"
    return body


async def _moolre_send_request(to: str, body: str) -> bool:
    """
    The single place the Moolre wire format lives.

    NOTE: Moolre's SMS API is documented behind the app.moolre.com dashboard
    and is not covered by their public payments docs, so the request shape
    below is provisional. Confirm the endpoint, auth header and body keys
    against the dashboard docs before enabling `SMS_ENABLED` in production —
    nothing else in this module needs to change.
    """
    settings = get_settings()

    payload = {
        "type": 1,
        "channel": settings.moolre_sender_id,
        "recipient": to,
        "message": body,
    }
    headers = {
        "X-API-USER": settings.moolre_api_user,
        "X-API-KEY": settings.moolre_api_key,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            settings.moolre_api_url, json=payload, headers=headers
        )
        response.raise_for_status()
        data = response.json()

    # Moolre returns a status flag in the body; a 2xx alone is not success.
    if isinstance(data, dict) and "status" in data:
        succeeded = str(data.get("status")) in {"1", "True", "true", "success"}
        if not succeeded:
            logger.error(
                "Moolre rejected SMS to %s: %s",
                mask_phone(to),
                data.get("message") or data,
            )
        return succeeded
    return True


async def send_sms(to: str, body: str) -> bool:
    """
    Send one SMS. Never raises — notification failures must not roll back or
    block a valid order (see AGENT.md).
    """
    settings = get_settings()

    if not settings.sms_enabled:
        logger.info(
            "SMS disabled; skipping send to %s (%d segment(s))",
            mask_phone(to),
            count_segments(body),
        )
        return False

    if not (settings.moolre_api_key and settings.moolre_api_user):
        logger.error("Moolre credentials missing; cannot send SMS")
        return False

    recipient = normalise_ghana_msisdn(to)
    if not recipient:
        logger.error("Not a valid Ghana number, skipping SMS: %s", mask_phone(to))
        return False

    try:
        return await _moolre_send_request(recipient, body)
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Moolre SMS failed to %s: %s — %s",
            mask_phone(recipient),
            exc,
            exc.response.text,
        )
        return False
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("Moolre SMS error to %s: %s", mask_phone(recipient), exc)
        return False


async def send_order_receipt_sms(order: OrderResponseSchema) -> bool:
    settings = get_settings()
    return await send_sms(
        order.customer_phone, build_receipt_sms(order, settings.restaurant_name)
    )


async def send_order_status_sms(order: OrderResponseSchema) -> bool:
    """Skip statuses that do not justify the per-segment cost."""
    if order.status.value in _SILENT_STATUSES:
        return False
    settings = get_settings()
    return await send_sms(
        order.customer_phone, build_status_sms(order, settings.restaurant_name)
    )
