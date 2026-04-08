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
        except httpx.HTTPStatusError as e:
            logger.error(f"WhatsApp send failed to {to}: {e}")
            logger.error(f"Response body: {e.response.text}")
            return False
        except httpx.HTTPError as e:
            logger.error(f"WhatsApp HTTP error to {to}: {e}")
            return False


async def send_template_message(
    to: str,
    template_name: str,
    language: str,
    body_params: list[str],
) -> bool:
    """Send a WhatsApp template message."""
    settings = get_settings()
    url = f"{GRAPH_API}/{settings.meta_phone_number_id}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": text}
                        for text in body_params
                    ],
                }
            ],
        },
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
            logger.error(f"WhatsApp template send failed to {to}: {e}")
            logger.error(f"Response body: {e.response.text}")
            return False
        except httpx.HTTPError as e:
            logger.error(f"WhatsApp HTTP error to {to}: {e}")
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


def _build_order_items_template_text(order: OrderResponseSchema) -> str:
    """Convert order items into a single template body string."""
    return "\n".join(
        [f"- {item.quantity}x {item.name} = GHS {item.total_price:.2f}" for item in order.items]
    )


async def send_order_receipt_to_customer(order: OrderResponseSchema) -> bool:
    """Send the order receipt to the customer's WhatsApp using a template."""
    settings = get_settings()
    template_name = "order_receipt"
    language = "en_US"
    body_params = [
        order.customer_name or "Customer",
        order.id[:8].upper(),
        order.created_at.strftime("%d %b %Y, %I:%M %p"),
        _build_order_items_template_text(order),
        f"{order.total_amount:.2f}",
        f"{order.total_amount:.2f}",
        order.delivery_address,
        "MoMo" if order.payment_method == "momo" else "Cash on Delivery",
        settings.restaurant_name,
    ]

    sent = await send_template_message(
        order.customer_phone,
        template_name,
        language,
        body_params,
    )

    if sent:
        return True

    # Fallback to plain text if template send fails for any reason.
    receipt = _build_receipt(order, settings.restaurant_name)
    return await send_text_message(order.customer_phone, receipt)


async def send_order_notification_to_owner(order: OrderResponseSchema) -> bool:
    """Send new order alert to the restaurant owner."""
    settings = get_settings()
    notification = _build_owner_notification(order, settings.restaurant_name)
    return await send_text_message(settings.owner_whatsapp, notification)
