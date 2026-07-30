"""
WhatsApp Cloud API service.
Handles sending messages and formatting the POS-style receipt.
"""

import httpx
import logging
from app.config import get_settings
from app.schemas.order import OrderResponseSchema
from app.services.logging_utils import mask_phone

logger = logging.getLogger(__name__)
GRAPH_API = "https://graph.facebook.com/v19.0"


async def send_text_message(
    to: str,
    body: str,
    *,
    preview_url: bool = False,
) -> bool:
    """Send a plain text WhatsApp message."""
    settings = get_settings()
    url = f"{GRAPH_API}/{settings.meta_phone_number_id}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body, "preview_url": preview_url},
    }

    headers = {
        "Authorization": f"Bearer {settings.meta_access_token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return True
        except httpx.HTTPStatusError as e:
            logger.error("WhatsApp send failed to %s: %s", mask_phone(to), e)
            logger.error(f"Response body: {e.response.text}")
            return False
        except httpx.HTTPError as e:
            logger.error("WhatsApp HTTP error to %s: %s", mask_phone(to), e)
            return False


def _build_receipt(order: OrderResponseSchema, restaurant_name: str) -> str:
    """Build a full POS-style receipt for the customer."""
    from datetime import datetime, timezone

    divider = "━━━━━━━━━━━━━━━━━━━━"
    order_reference = order.order_number or order.id[:8].upper()
    now = datetime.now(timezone.utc).strftime("%d %b %Y, %I:%M %p")
    tracking_line = f"Tracking: *{order.tracking_code}*\n" if order.tracking_code else ""
    tracking_url_line = (
        f"\n🔗 *Track your order live:*\n{order.tracking_url}\n"
        if order.tracking_url
        else ""
    )
    branch_line = f"Branch: *{order.branch_name}*\n" if order.branch_name else ""

    items_lines = []
    for item in order.items:
        line1 = f"  {item.quantity}x {item.name}"
        selections = ", ".join(
            selection.name or selection.option_id
            for selection in item.selections
        )
        if selections:
            line1 = f"{line1}\n     + {selections}"
        line2 = f"     GHS {item.unit_price:.2f} x {item.quantity} = GHS {item.total_price:.2f}"
        items_lines.append(f"{line1}\n{line2}")
    items_block = "\n".join(items_lines)

    payment_label = "Mobile Money (MoMo)" if order.payment_method == "momo" else "Cash on Delivery"

    return (
        f"{divider}\n"
        f"🧾 *{restaurant_name.upper()}*\n"
        f"   ORDER RECEIPT\n"
        f"{divider}\n"
        f"Order ID: *{order_reference}*\n"
        f"{branch_line}"
        f"{tracking_line}"
        f"Date: {now}\n"
        f"{divider}\n"
        f"*ITEMS*\n"
        f"{items_block}\n"
        f"{divider}\n"
        f"Subtotal       GHS {order.subtotal_amount:.2f}\n"
        f"Delivery       GHS {order.delivery_fee:.2f}\n"
        f"{divider}\n"
        f"*TOTAL          GHS {order.total_amount:.2f}*\n"
        f"{divider}\n"
        f"📍 *Deliver to:*\n"
        f"  {order.delivery_address}\n"
        f"💳 *Payment:* {payment_label}\n"
        f"{divider}\n"
        f"✅ Thank you for your order!\n"
        f"The kitchen will confirm your timing shortly.\n"
        f"Questions? Reply to this chat.\n"
        f"{tracking_url_line}"
        f"{divider}"
    )


def _build_owner_notification(order: OrderResponseSchema, restaurant_name: str) -> str:
    """Build the order alert sent to the restaurant owner."""
    divider = "━━━━━━━━━━━━━━━━━━━━"
    order_reference = order.order_number or order.id[:8].upper()

    items_lines = "\n".join(
        [f"  • {item.quantity}x {item.name} — GHS {item.total_price:.2f}"
         for item in order.items]
    )

    payment_label = "MoMo" if order.payment_method == "momo" else "Cash on Delivery"
    customer = order.customer_name or order.customer_phone
    branch_line = f"🏪 Branch: *{order.branch_name}*\n" if order.branch_name else ""

    return (
        f"🔔 *NEW ORDER — {restaurant_name}*\n"
        f"{divider}\n"
        f"Order ID: *{order_reference}*\n"
        f"{branch_line}"
        f"👤 Customer: {customer}\n"
        f"📱 Phone: {order.customer_phone}\n"
        f"{divider}\n"
        f"*ITEMS:*\n{items_lines}\n"
        f"{divider}\n"
        f"*TOTAL: GHS {order.total_amount:.2f}*\n"
        f"💳 Payment: {payment_label}\n"
        f"{divider}\n"
        f"📍 *Deliver to:*\n"
        f"  {order.delivery_address}\n"
        f"{divider}\n"
        f"Reply to contact customer directly."
    )
async def send_order_receipt_to_customer(order: OrderResponseSchema) -> bool:
    """Send the full POS receipt to the customer's WhatsApp."""
    settings = get_settings()
    receipt = _build_receipt(order, settings.restaurant_name)
    return await send_text_message(
        order.customer_phone,
        receipt,
        preview_url=bool(order.tracking_url),
    )


async def send_order_notification_to_owner(order: OrderResponseSchema) -> bool:
    """Send new order alert to the restaurant owner."""
    settings = get_settings()
    notification = _build_owner_notification(order, settings.restaurant_name)
    return await send_text_message(settings.owner_whatsapp, notification)


def _build_status_update(order: OrderResponseSchema, restaurant_name: str) -> str:
    order_reference = order.order_number or order.id[:8].upper()
    branch = f" at *{order.branch_name}*" if order.branch_name else ""

    messages = {
        "confirmed": (
            f"✅ *Order accepted{branch}*\n"
            "The kitchen has confirmed your order."
        ),
        "preparing": (
            f"👨🏾‍🍳 *Your food is being prepared{branch}*\n"
            "Fresh, hot and on the way to the next step."
        ),
        "ready": (
            f"🥡 *Your order is ready{branch}*\n"
            "It is being prepared for dispatch."
        ),
        "out_for_delivery": (
            "🛵 *Your food is out for delivery*\n"
            "Please keep your phone nearby for the rider."
        ),
        "delayed": (
            "⏳ *Your order is delayed*\n"
            "The branch is working on it. Reply here if you need help."
        ),
        "delivered": (
            "🎉 *Order delivered*\n"
            f"Thank you for ordering from {restaurant_name}."
        ),
        "cancel_requested": (
            "⚠️ *Cancellation request received*\n"
            "The restaurant is reviewing it and will contact you if needed."
        ),
        "cancelled": (
            "❌ *Order cancelled*\n"
            "Reply here if you need help with this order."
        ),
        "rejected": (
            "❌ *Order could not be accepted*\n"
            "Reply here so the restaurant can help you with another option."
        ),
    }
    body = messages.get(
        order.status.value,
        f"ℹ️ *Order update:* {order.status.value.replace('_', ' ').title()}",
    )
    tracking = (
        f"\n\nTrack order #{order_reference}:\n{order.tracking_url}"
        if order.tracking_url
        else f"\n\nOrder #{order_reference}"
    )
    return f"{body}{tracking}"


async def send_order_status_update_to_customer(order: OrderResponseSchema) -> bool:
    settings = get_settings()
    message = _build_status_update(order, settings.restaurant_name)
    return await send_text_message(
        order.customer_phone,
        message,
        preview_url=bool(order.tracking_url),
    )
