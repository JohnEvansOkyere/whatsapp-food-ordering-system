import httpx
from app.config import get_settings
from app.schemas.order import OrderSummary
import logging

logger = logging.getLogger(__name__)

WHATSAPP_API_URL = "https://graph.facebook.com/v19.0"


async def send_whatsapp_message(to: str, message: str) -> bool:
    """Send a plain text WhatsApp message."""
    settings = get_settings()
    url = f"{WHATSAPP_API_URL}/{settings.meta_phone_number_id}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message},
    }

    headers = {
        "Authorization": f"Bearer {settings.meta_access_token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            logger.info(f"WhatsApp message sent to {to}")
            return True
        except httpx.HTTPError as e:
            logger.error(f"Failed to send WhatsApp message to {to}: {e}")
            return False


async def notify_owner_new_order(order: OrderSummary) -> bool:
    """Send order notification to restaurant owner."""
    settings = get_settings()

    items_text = "\n".join(
        [f"  • {item.quantity}x {item.name} — GHS {item.total_price:.2f}"
         for item in order.items]
    )

    customer_label = order.customer_name or order.customer_phone
    payment_label = "MoMo" if order.payment_method == "momo" else "Cash on Delivery"

    message = (
        f"🔔 *NEW ORDER — {settings.restaurant_name}*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📦 Order ID: #{order.order_id[:8].upper()}\n"
        f"👤 Customer: {customer_label}\n"
        f"📱 Phone: {order.customer_phone}\n"
        f"📍 Deliver to: {order.delivery_address}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"*Items:*\n{items_text}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 *Total: GHS {order.total_amount:.2f}*\n"
        f"💳 Payment: {payment_label}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Reply to this chat to contact the customer."
    )

    return await send_whatsapp_message(settings.owner_whatsapp, message)


async def send_order_confirmation_to_customer(customer_phone: str, order: OrderSummary) -> bool:
    """Send order confirmation to the customer."""
    settings = get_settings()

    items_text = "\n".join(
        [f"  • {item.quantity}x {item.name}" for item in order.items]
    )

    message = (
        f"✅ *Order Confirmed!*\n\n"
        f"Hi{' ' + order.customer_name if order.customer_name else ''}! "
        f"We've received your order.\n\n"
        f"*{settings.restaurant_name}*\n"
        f"Order #{order.order_id[:8].upper()}\n\n"
        f"{items_text}\n\n"
        f"*Total: GHS {order.total_amount:.2f}*\n"
        f"📍 Delivering to: {order.delivery_address}\n\n"
        f"We'll message you when your food is on the way. 🛵"
    )

    return await send_whatsapp_message(customer_phone, message)
