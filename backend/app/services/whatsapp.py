"""
WhatsApp Cloud API service.
Handles sending messages and formatting the POS-style receipt.
"""

import httpx
import logging
from app.config import get_settings
from app.schemas.order import OrderResponseSchema

logger = logging.getLogger(__name__)
GRAPH_API = "https://graph.facebook.com/v19.0"


async def send_text_message(to: str, body: str) -> bool:
    """Send a plain text WhatsApp message."""
    settings = get_settings()
    url = f"{GRAPH_API}/{settings.meta_phone_number_id}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body, "preview_url": False},
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
        except httpx.HTTPError as e:
            logger.error(f"WhatsApp send failed to {to}: {e}")
            return False


def _build_receipt(order: OrderResponseSchema, restaurant_name: str) -> str:
    """Build a full POS-style receipt for the customer."""
    from datetime import datetime, timezone

    divider = "━━━━━━━━━━━━━━━━━━━━"
    short_id = order.id[:8].upper()
    now = datetime.now(timezone.utc).strftime("%d %b %Y, %I:%M %p")

    items_lines = []
    for item in order.items:
        line1 = f"  {item.quantity}x {item.name}"
        line2 = f"     GHS {item.unit_price:.2f} x {item.quantity} = GHS {item.total_price:.2f}"
        items_lines.append(f"{line1}\n{line2}")
    items_block = "\n".join(items_lines)

    payment_label = "Mobile Money (MoMo)" if order.payment_method == "momo" else "Cash on Delivery"

    return (
        f"{divider}\n"
        f"🧾 *{restaurant_name.upper()}*\n"
        f"   ORDER RECEIPT\n"
        f"{divider}\n"
        f"Order #*{short_id}*\n"
        f"Date: {now}\n"
        f"{divider}\n"
        f"*ITEMS*\n"
        f"{items_block}\n"
        f"{divider}\n"
        f"Subtotal       GHS {order.total_amount:.2f}\n"
        f"Delivery             FREE\n"
        f"{divider}\n"
        f"*TOTAL          GHS {order.total_amount:.2f}*\n"
        f"{divider}\n"
        f"📍 *Deliver to:*\n"
        f"  {order.delivery_address}\n"
        f"💳 *Payment:* {payment_label}\n"
        f"{divider}\n"
        f"✅ Thank you for your order!\n"
        f"We'll deliver within 45-60 mins.\n"
        f"Questions? Reply to this chat.\n"
        f"{divider}"
    )


def _build_owner_notification(order: OrderResponseSchema, restaurant_name: str) -> str:
    """Build the order alert sent to the restaurant owner."""
    divider = "━━━━━━━━━━━━━━━━━━━━"
    short_id = order.id[:8].upper()

    items_lines = "\n".join(
        [f"  • {item.quantity}x {item.name} — GHS {item.total_price:.2f}"
         for item in order.items]
    )

    payment_label = "MoMo" if order.payment_method == "momo" else "Cash on Delivery"
    customer = order.customer_name or order.customer_phone

    return (
        f"🔔 *NEW ORDER — {restaurant_name}*\n"
        f"{divider}\n"
        f"Order #*{short_id}*\n"
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
    return await send_text_message(order.customer_phone, receipt)


async def send_order_notification_to_owner(order: OrderResponseSchema) -> bool:
    """Send new order alert to the restaurant owner."""
    settings = get_settings()
    notification = _build_owner_notification(order, settings.restaurant_name)
    return await send_text_message(settings.owner_whatsapp, notification)
