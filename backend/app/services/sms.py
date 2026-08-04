"""
SMS service — Arkesel and Moolre, tried in SMS_PROVIDERS order.

Carries the order tracking link to the customer alongside the WhatsApp
receipt, and the verification codes for phone sign-in. SMS is charged per
160-character segment, so the message bodies here are deliberately terse — the
full itemised receipt stays on WhatsApp.

Verification codes have no second channel, so an unreachable provider locks a
customer out of their account entirely. That is why `send_sms` fails over to
the next configured provider rather than giving up on the first error.
"""

from __future__ import annotations

import logging
import re
import uuid

import httpx

from app.config import get_settings
from app.schemas.order import OrderResponseSchema
from app.services.logging_utils import mask_phone, redact_credentials

logger = logging.getLogger(__name__)

GSM7_SEGMENT_LEN = 160
GSM7_MULTIPART_SEGMENT_LEN = 153
UCS2_SEGMENT_LEN = 70
UCS2_MULTIPART_SEGMENT_LEN = 67

# GSM 03.38. Anything outside these two sets forces the message into UCS-2.
_GSM7_BASIC = set(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)
# These cost two septets each.
_GSM7_EXTENDED = set("^{}\\[~]|€")

# Arkesel V1 response codes. "ok" is the only success value; the rest are errors.
_ARKESEL_ERRORS = {
    "100": "Bad gateway request",
    "101": "Wrong action",
    "102": "Authentication failed (check ARKESEL_API_KEY)",
    "103": "Invalid phone number",
    "104": "Invalid sender ID (max 11 characters, must be telco-approved)",
    "105": "Insufficient SMS balance",
    "106": "Invalid message",
    "107": "Empty message",
}

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


def is_gsm7(text: str) -> bool:
    """Whether `text` encodes as GSM-7 rather than falling back to UCS-2."""
    return all(char in _GSM7_BASIC or char in _GSM7_EXTENDED for char in text)


def count_segments(body: str) -> int:
    """
    Number of SMS segments `body` will be billed as.

    A single character outside GSM-7 — an em dash, a curly quote, the ɛ and ɔ
    of Twi orthography — forces the whole message into UCS-2, where a segment
    holds 70 characters instead of 160. Assuming GSM-7 would undercount those
    by a factor of two, which is real money on a prepaid balance.
    """
    if not body:
        return 0

    if is_gsm7(body):
        # Extended characters occupy two septets each.
        length = sum(2 if char in _GSM7_EXTENDED else 1 for char in body)
        single, multi = GSM7_SEGMENT_LEN, GSM7_MULTIPART_SEGMENT_LEN
    else:
        length = len(body)
        single, multi = UCS2_SEGMENT_LEN, UCS2_MULTIPART_SEGMENT_LEN

    if length <= single:
        return 1
    return -(-length // multi)  # ceiling division


def _order_reference(order: OrderResponseSchema) -> str:
    return order.order_number or order.id[:8].upper()


def _first_name(order: OrderResponseSchema) -> str:
    """First name only — surnames cost characters and buy no warmth."""
    parts = (order.customer_name or "").strip().split()
    return parts[0] if parts else ""


def build_receipt_sms(order: OrderResponseSchema, restaurant_name: str) -> str:
    """
    Warm order-confirmation SMS carrying the tracking link.

    The customer's name is theirs, not ours: it can be long, and it can carry
    characters outside GSM-7 (the ɛ and ɔ of Twi, accented vowels) that would
    force the whole message into 70-character UCS-2 segments. Either way the
    greeting is what gets dropped — never the thanks or the tracking link — so
    a name can never turn a one-unit message into three.
    """
    reference = _order_reference(order)
    tail = f" Track: {order.tracking_url}" if order.tracking_url else ""

    def compose(name: str) -> str:
        greeting = f"Hi {name}! Thank you," if name else "Thank you!"
        return (
            f"{greeting} {restaurant_name} is happy to see you. "
            f"Order {reference} is in, GHS {order.total_amount:.2f}.{tail}"
        )

    body = compose(_first_name(order))
    if count_segments(body) > 1:
        body = compose("")
        if count_segments(body) > 1:
            logger.warning(
                "Receipt SMS for order %s costs %d segments even without a name",
                reference,
                count_segments(body),
            )
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


def _redact(text: str) -> str:
    """Strip provider credentials out of anything headed for the logs.

    Arkesel V1 carries its api-key in the query string, so URLs surface in
    exception messages and error bodies — never let one reach a log line.
    """
    settings = get_settings()
    for secret in (
        getattr(settings, "arkesel_api_key", ""),
        getattr(settings, "moolre_vas_key", ""),
    ):
        if secret:
            text = text.replace(secret, "***")
    return redact_credentials(text)


def _parse_arkesel_response(response: httpx.Response) -> tuple[str, str]:
    """Parse a V1 response into (code, human-readable message)."""
    try:
        data = response.json()
    except ValueError:
        code = response.text.strip().lower()
        return code, _ARKESEL_ERRORS.get(code, response.text.strip())
    code = str(data.get("code", "")).lower()
    return code, str(data.get("message") or _ARKESEL_ERRORS.get(code, "") or data)


async def _arkesel_send_request(to: str, body: str) -> bool:
    """
    The single place the Arkesel wire format lives.

    V1 is a GET with everything in the query string; the api-key authenticates
    and `from` is the approved alphanumeric sender ID.
    """
    settings = get_settings()

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            settings.arkesel_api_url,
            params={
                "action": "send-sms",
                "api_key": settings.arkesel_api_key,
                "to": to,
                "from": settings.arkesel_sender_id,
                "sms": body,
            },
        )
        response.raise_for_status()

    # Arkesel returns a result code in the body; a 200 alone is not success.
    code, message = _parse_arkesel_response(response)
    if code == "ok":
        return True
    logger.error(
        "Arkesel rejected SMS to %s: code=%s %s",
        mask_phone(to),
        code,
        _redact(message),
    )
    return False


async def _moolre_send_request(to: str, body: str) -> bool:
    """
    The single place the Moolre wire format lives.

    Moolre's SMS API authenticates with the X-API-VASKEY header and takes a
    `messages` array — each entry needs a unique `ref` for idempotency.
    """
    settings = get_settings()

    payload = {
        "type": 1,
        "senderid": settings.moolre_sender_id,
        "messages": [
            {"recipient": to, "message": body, "ref": f"veloxa-{uuid.uuid4()}"}
        ],
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            settings.moolre_api_url,
            headers={"X-API-VASKEY": settings.moolre_vas_key},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    # Moolre returns a status flag in the body; a 2xx alone is not success.
    if str(data.get("status")) == "1":
        return True
    message = data.get("message")
    if isinstance(message, list):
        message = " ".join(str(item) for item in message)
    logger.error(
        "Moolre rejected SMS to %s: code=%s %s",
        mask_phone(to),
        data.get("code"),
        _redact(str(message or data)),
    )
    return False


def _arkesel_configured(settings) -> bool:
    return bool(settings.arkesel_api_key and settings.arkesel_sender_id)


def _moolre_configured(settings) -> bool:
    return bool(settings.moolre_vas_key and settings.moolre_sender_id)


def _providers() -> dict[str, tuple]:
    """Provider name -> (is-configured predicate, send function).

    Built per call so the functions resolve at call time; the order actually
    used at runtime comes from SMS_PROVIDERS, not from this dict.
    """
    return {
        "arkesel": (_arkesel_configured, _arkesel_send_request),
        "moolre": (_moolre_configured, _moolre_send_request),
    }


async def send_sms(to: str, body: str) -> bool:
    """
    Send one SMS, trying each configured provider in SMS_PROVIDERS order until
    one accepts it.

    A provider with no credentials is skipped rather than treated as a failure,
    so a single-provider deployment needs no extra configuration. Never raises —
    notification failures must not roll back or block a valid order (AGENT.md).
    """
    settings = get_settings()

    if not settings.sms_enabled:
        logger.info(
            "SMS disabled; skipping send to %s (%d segment(s))",
            mask_phone(to),
            count_segments(body),
        )
        return False

    recipient = normalise_ghana_msisdn(to)
    if not recipient:
        logger.error("Not a valid Ghana number, skipping SMS: %s", mask_phone(to))
        return False

    registry = _providers()
    chain: list[tuple[str, object]] = []
    for name in settings.sms_providers_list:
        provider = registry.get(name)
        if provider is None:
            logger.error("Unknown SMS provider in SMS_PROVIDERS: %s", name)
            continue
        is_configured, send_request = provider
        if not is_configured(settings):
            logger.debug("SMS provider %s has no credentials; skipping", name)
            continue
        chain.append((name, send_request))

    if not chain:
        logger.error("No SMS provider is configured; cannot send SMS")
        return False

    for position, (name, send_request) in enumerate(chain):
        try:
            if await send_request(recipient, body):
                return True
        except httpx.HTTPStatusError as exc:
            logger.error(
                "%s SMS failed to %s: HTTP %s — %s",
                name,
                mask_phone(recipient),
                exc.response.status_code,
                _redact(exc.response.text),
            )
        except (httpx.HTTPError, ValueError) as exc:
            logger.error(
                "%s SMS error to %s: %s",
                name,
                mask_phone(recipient),
                _redact(str(exc)),
            )
        if position + 1 < len(chain):
            logger.warning("SMS provider %s could not deliver; trying the next", name)
        else:
            logger.error(
                "SMS provider %s could not deliver and no fallback is left", name
            )

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
