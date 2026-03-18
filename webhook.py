from fastapi import APIRouter, Request, HTTPException, Query
from app.config import get_settings
from app.services.whatsapp import send_whatsapp_message
import logging
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])

# In-memory session store for conversation state
# For production scale, move this to Redis or Supabase
sessions: dict[str, dict] = {}


@router.get("/whatsapp")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """Meta webhook verification handshake."""
    settings = get_settings()

    if hub_mode == "subscribe" and hub_verify_token == settings.meta_verify_token:
        logger.info("WhatsApp webhook verified successfully")
        return int(hub_challenge)

    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp")
async def receive_message(request: Request):
    """
    Receive and process incoming WhatsApp messages.
    Handles the full ordering conversation flow.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Extract message
    try:
        entry = body["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "messages" not in value:
            return {"status": "no_message"}

        message = value["messages"][0]
        sender = message["from"]
        msg_type = message.get("type", "")

        if msg_type == "text":
            text = message["text"]["body"].strip()
            await handle_text_message(sender, text)

    except (KeyError, IndexError) as e:
        logger.warning(f"Webhook parse warning: {e}")

    # Always return 200 to Meta
    return {"status": "ok"}


async def handle_text_message(sender: str, text: str):
    """
    Simple state-machine conversation handler.

    States:
    - new / greeting
    - awaiting_address
    - awaiting_payment_method
    - awaiting_momo_number
    - order_complete
    """
    session = sessions.get(sender, {"state": "new", "order_text": ""})
    state = session.get("state", "new")
    text_lower = text.lower()

    # ── GREETING / RESET ──────────────────────────────────────────
    if state == "new" or any(w in text_lower for w in ["hi", "hello", "hey", "start", "menu"]):
        from app.config import get_settings
        settings = get_settings()

        menu_url = "https://your-menu-app.vercel.app"  # Replace with actual deployed URL

        reply = (
            f"👋 Welcome to *{settings.restaurant_name}*!\n\n"
            f"🍽️ Browse our full menu with photos here:\n"
            f"{menu_url}\n\n"
            f"Add items to your cart, then tap *Order on WhatsApp* to continue here.\n\n"
            f"Already have your order? Just type it out like:\n"
            f"_1x Jollof Rice + Chicken, 2x Fried Plantain_"
        )
        sessions[sender] = {"state": "awaiting_order", "order_text": ""}
        await send_whatsapp_message(sender, reply)
        return

    # ── RECEIVED ORDER TEXT ───────────────────────────────────────
    if state == "awaiting_order":
        # Store whatever they typed as the order
        sessions[sender] = {
            "state": "awaiting_address",
            "order_text": text,
        }
        reply = (
            f"✅ Got your order:\n_{text}_\n\n"
            f"📍 What's your *delivery address*?\n"
            f"_(e.g. House 5, Kanda Highway, near Total filling station)_"
        )
        await send_whatsapp_message(sender, reply)
        return

    # ── RECEIVED DELIVERY ADDRESS ─────────────────────────────────
    if state == "awaiting_address":
        sessions[sender] = {
            **session,
            "state": "awaiting_payment",
            "address": text,
        }
        reply = (
            f"📍 Delivery to: _{text}_\n\n"
            f"💳 How would you like to pay?\n\n"
            f"1️⃣ *MoMo* — Mobile Money\n"
            f"2️⃣ *Cash* — Pay on delivery\n\n"
            f"Reply *1* or *2*"
        )
        await send_whatsapp_message(sender, reply)
        return

    # ── PAYMENT METHOD ────────────────────────────────────────────
    if state == "awaiting_payment":
        if text in ["1", "momo", "mobile money"]:
            sessions[sender] = {**session, "state": "awaiting_momo", "payment": "momo"}
            reply = (
                f"📱 Please send your *MoMo number*:\n"
                f"_(e.g. 0244123456)_"
            )
        elif text in ["2", "cash", "cod"]:
            sessions[sender] = {**session, "state": "confirming", "payment": "cash"}
            reply = await build_confirmation_message(sender)
        else:
            reply = "Please reply *1* for MoMo or *2* for Cash on delivery."

        await send_whatsapp_message(sender, reply)
        return

    # ── MOMO NUMBER ───────────────────────────────────────────────
    if state == "awaiting_momo":
        sessions[sender] = {**session, "state": "confirming", "momo_number": text}
        reply = await build_confirmation_message(sender)
        await send_whatsapp_message(sender, reply)
        return

    # ── FINAL CONFIRMATION ────────────────────────────────────────
    if state == "confirming":
        if any(w in text_lower for w in ["yes", "confirm", "ok", "yeah", "yep", "correct"]):
            await finalize_order(sender)
        elif any(w in text_lower for w in ["no", "cancel", "wrong", "nope"]):
            sessions[sender] = {"state": "awaiting_order", "order_text": ""}
            await send_whatsapp_message(
                sender,
                "No problem! Let's start over. What would you like to order?"
            )
        else:
            await send_whatsapp_message(
                sender,
                "Reply *Yes* to confirm your order or *No* to start over."
            )
        return

    # ── FALLBACK ──────────────────────────────────────────────────
    sessions[sender] = {"state": "new"}
    await send_whatsapp_message(
        sender,
        "Sorry, I didn't understand that. Type *Hi* to start a new order. 😊"
    )


async def build_confirmation_message(sender: str) -> str:
    session = sessions.get(sender, {})
    order_text = session.get("order_text", "")
    address = session.get("address", "")
    payment = session.get("payment", "cash")
    momo = session.get("momo_number", "")

    payment_line = f"MoMo: {momo}" if payment == "momo" else "Cash on delivery"

    # Update state to confirming
    sessions[sender] = {**session, "state": "confirming"}

    return (
        f"📋 *Please confirm your order:*\n\n"
        f"🛒 {order_text}\n\n"
        f"📍 Deliver to: {address}\n"
        f"💳 Payment: {payment_line}\n\n"
        f"Reply *Yes* to confirm or *No* to cancel."
    )


async def finalize_order(sender: str):
    """Order confirmed — notify owner and confirm to customer."""
    session = sessions.get(sender, {})
    from app.config import get_settings
    from app.services.whatsapp import notify_owner_new_order
    from app.schemas.order import OrderSummary, OrderItemSchema
    import uuid

    settings = get_settings()
    order_id = str(uuid.uuid4())

    # Build a lightweight summary from session
    # (Full item parsing from text happens here — for MVP keep it simple)
    summary = OrderSummary(
        order_id=order_id,
        customer_phone=sender,
        customer_name=None,
        delivery_address=session.get("address", ""),
        items=[
            OrderItemSchema(
                item_id="custom",
                name=session.get("order_text", "Order"),
                quantity=1,
                unit_price=0,
                total_price=0,
            )
        ],
        total_amount=0,
        payment_method=session.get("payment", "cash"),
    )

    # Notify owner
    await notify_owner_new_order(summary)

    # Confirm to customer
    reply = (
        f"🎉 *Order Confirmed!*\n\n"
        f"Your order #{order_id[:8].upper()} has been received.\n"
        f"We'll prepare it and deliver to:\n"
        f"📍 _{session.get('address', '')}_\n\n"
        f"Questions? Just reply here. Thank you! 🙏"
    )
    await send_whatsapp_message(sender, reply)

    # Clear session
    sessions[sender] = {"state": "new"}
