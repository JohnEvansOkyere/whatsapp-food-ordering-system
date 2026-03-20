"""
Ama — WhatsApp conversation handler.

Builds the system prompt and manages the full conversation flow:
  1. Greeting (new vs returning customer)
  2. Intent detection (knows what they want vs wants to browse)
  3. Order taking via chat
  4. Order confirmation
  5. Address collection
  6. Payment method collection
  7. Order finalisation → triggers receipt + owner notification

All AI calls go through ai_service.py (Groq → OpenAI → Gemini cascade).
"""

import logging
from app.config import get_settings
from app.services.ai_service import get_ai_response
from app.services import session_store as store
from app.services.order_parser import parse_order_from_text, format_order_for_confirmation
from app.services.customer_service import (
    get_customer,
    get_last_order,
    upsert_customer,
    format_returning_customer_greeting,
)
from app.services.order_service import create_order
from app.schemas.order import CreateOrderSchema, OrderItemSchema

logger = logging.getLogger(__name__)

AMA_SYSTEM_PROMPT = """\
You are Ama, the friendly WhatsApp food ordering assistant for {restaurant_name} in Accra, Ghana.

YOUR PERSONALITY:
- Warm, helpful, natural — like a real Ghanaian cashier
- Short replies — WhatsApp is not email. 1–3 sentences max
- Occasional light expressions are fine (Chale, No problem!, Ei!)
- Never sound robotic or scripted
- Never make up menu items or prices

YOUR ROLE IN THIS CONVERSATION:
You help customers order food. The ordering flow is handled by the system —
your job in freeform conversation is to:
- Answer questions about the restaurant (hours, location, delivery areas)
- Help undecided customers pick something
- Handle small talk warmly and redirect to ordering
- If a customer seems confused, offer the menu link: {menu_url}

RESTAURANT INFO:
- Location: Osu, Accra
- Hours: Mon–Sun, 10am–10pm
- Delivery: Within Accra, free delivery
- Payment: MoMo or Cash on delivery

MENU HIGHLIGHTS (share when asked):
🍚 Jollof Rice + Chicken — GHS 45
🍚 Waakye Special — GHS 40
🍗 Grilled Chicken (2 pcs) — GHS 55
🍗 Spicy Wings (6 pcs) — GHS 48
🍕 BBQ Chicken Pizza — GHS 85
🍟 Chips Large — GHS 20
🥤 Sobolo — GHS 12

Full menu with photos: {menu_url}

IMPORTANT: Keep it short and human. This is WhatsApp.
"""


async def handle_incoming_message(sender: str, text: str, branch_id: str | None = None) -> str:
    """
    Main entry point for all incoming WhatsApp messages.
    Routes based on current conversation state.
    Returns the reply to send back to the customer.
    """
    settings = get_settings()
    state = store.get_state(sender)

    # Store branch ID if provided (from QR code)
    if branch_id:
        store.set_branch_id(sender, branch_id)

    text_lower = text.lower().strip()

    # ── GREETING STATE ─────────────────────────────────────────────────────────
    if state == "greeting":
        return await _handle_greeting(sender, settings)

    # ── ASKED INTENT ───────────────────────────────────────────────────────────
    if state == "asked_intent":
        return await _handle_intent_response(sender, text_lower, settings)

    # ── TAKING ORDER ───────────────────────────────────────────────────────────
    if state == "taking_order":
        return await _handle_order_input(sender, text, settings)

    # ── CONFIRMING ORDER ───────────────────────────────────────────────────────
    if state == "confirming_order":
        return await _handle_order_confirmation(sender, text_lower, settings)

    # ── COLLECTING ADDRESS ─────────────────────────────────────────────────────
    if state == "collecting_address":
        return await _handle_address_input(sender, text, settings)

    # ── COLLECTING PAYMENT ─────────────────────────────────────────────────────
    if state == "collecting_payment":
        return await _handle_payment_input(sender, text_lower, settings)

    # ── DONE / FALLBACK ────────────────────────────────────────────────────────
    return await _handle_freeform(sender, text, settings)


# ── STATE HANDLERS ─────────────────────────────────────────────────────────────

async def _handle_greeting(sender: str, settings) -> str:
    """First message — check if returning customer, personalise greeting."""
    customer = await get_customer(sender)

    if customer:
        last_order = await get_last_order(sender)
        reply = format_returning_customer_greeting(customer, last_order, settings.restaurant_name)

        # If they have a last order, offer quick reorder path
        if last_order:
            store.set_pending_items(sender, last_order["items"])
            store.set_state(sender, "asked_intent")
            return reply

    # New customer greeting
    reply = (
        f"👋 Welcome to *{settings.restaurant_name}*!\n\n"
        f"I'm Ama, your food assistant. 😊\n\n"
        f"Do you know what you'd like to order, "
        f"or would you like to browse our menu first?"
    )
    store.set_state(sender, "asked_intent")
    return reply


async def _handle_intent_response(sender: str, text_lower: str, settings) -> str:
    """Customer responded to 'do you know what you want?' question."""

    # Wants to browse
    browse_signals = ["browse", "menu", "see", "show", "look", "photo", "picture", "no", "nope", "not sure", "idk", "don't know", "dont know"]
    if any(word in text_lower for word in browse_signals):
        store.set_state(sender, "taking_order")
        return (
            f"Sure! Here's our menu with photos 📸\n\n"
            f"{settings.menu_web_app_url}\n\n"
            f"Browse, add to cart, and place your order there — "
            f"your receipt will come straight to WhatsApp. 🧾"
        )

    # Wants to reorder last order
    reorder_signals = ["same", "again", "repeat", "last", "previous", "yes"]
    pending = store.get_pending_items(sender)
    if any(word in text_lower for word in reorder_signals) and pending:
        store.set_state(sender, "confirming_order")
        confirmation = format_order_for_confirmation(pending, settings.restaurant_name)
        return confirmation

    # Knows what they want — start taking order
    knows_signals = ["i want", "i'll have", "give me", "order", "get me", "i need", "yes", "yeah", "sure", "okay", "ok", "yep"]
    if any(word in text_lower for word in knows_signals):
        # If they already typed the order in this message, parse it
        items = await parse_order_from_text(text_lower)
        if items:
            store.set_pending_items(sender, items)
            store.set_state(sender, "confirming_order")
            return format_order_for_confirmation(items, settings.restaurant_name)

        # Otherwise ask them to tell us
        store.set_state(sender, "taking_order")
        return "Great! What would you like to order? 😊"

    # Unclear — use AI to respond naturally and re-ask
    store.add_message(sender, "user", text_lower)
    reply = await _ai_freeform(sender, text_lower, settings)
    store.add_message(sender, "assistant", reply)
    return reply


async def _handle_order_input(sender: str, text: str, settings) -> str:
    """Customer is telling us what they want via chat."""
    items = await parse_order_from_text(text)

    if not items:
        return (
            "Hmm, I couldn't quite catch that. 😅\n\n"
            "Try something like: *'2 jollof rice with chicken and a sobolo'*\n\n"
            f"Or browse our full menu here: {settings.menu_web_app_url}"
        )

    store.set_pending_items(sender, items)
    store.set_state(sender, "confirming_order")
    return format_order_for_confirmation(items, settings.restaurant_name)


async def _handle_order_confirmation(sender: str, text_lower: str, settings) -> str:
    """Customer is confirming or rejecting the order summary."""
    yes_signals = ["yes", "yeah", "yep", "correct", "right", "ok", "okay", "confirm", "sure", "perfect", "exactly"]
    no_signals = ["no", "nope", "wrong", "change", "different", "not right", "cancel"]

    if any(word in text_lower for word in yes_signals):
        store.set_state(sender, "collecting_address")
        return (
            "Perfect! 🎉\n\n"
            "📍 What's your *delivery address*?\n"
            "_(Please be specific — e.g. House 5, Kanda Highway, near Total filling station)_"
        )

    if any(word in text_lower for word in no_signals):
        store.set_state(sender, "taking_order")
        store.set_pending_items(sender, [])
        return (
            "No problem! Let's start again. 😊\n\n"
            "What would you like to order?"
        )

    # Ambiguous — treat as freeform but nudge
    return "Reply *Yes* to confirm your order, or *No* to change it. 😊"


async def _handle_address_input(sender: str, text: str, settings) -> str:
    """Collect delivery address."""
    if len(text.strip()) < 10:
        return (
            "Please give me a bit more detail on your address so we can find you easily. 📍\n"
            "_(e.g. House 5, Kanda Highway, near Total filling station)_"
        )

    store.set_delivery_address(sender, text.strip())
    store.set_state(sender, "collecting_payment")

    return (
        "Got it! 📍\n\n"
        "💳 How would you like to pay?\n\n"
        "1️⃣ *MoMo* — Mobile Money\n"
        "2️⃣ *Cash* — Pay on delivery\n\n"
        "Reply *1* or *2*"
    )


async def _handle_payment_input(sender: str, text_lower: str, settings) -> str:
    """Collect payment method and finalise the order."""
    momo_signals = ["1", "momo", "mobile money", "mobile", "mm"]
    cash_signals = ["2", "cash", "cod", "delivery", "door"]

    if any(word in text_lower for word in momo_signals):
        payment = "momo"
    elif any(word in text_lower for word in cash_signals):
        payment = "cash"
    else:
        return "Please reply *1* for MoMo or *2* for Cash on delivery. 😊"

    store.set_payment_method(sender, payment)

    # Place the order
    try:
        order = await _finalise_order(sender, payment, settings)
        store.set_state(sender, "done")

        payment_label = "Mobile Money" if payment == "momo" else "Cash on Delivery"
        reply = (
            f"✅ *Order placed successfully!*\n\n"
            f"Order #{order.id[:8].upper()}\n"
            f"Payment: {payment_label}\n\n"
            f"Your full receipt is coming right now 🧾\n"
            f"We'll deliver within 45–60 minutes. 🛵\n\n"
            f"Questions? Just reply here anytime!"
        )

        # Reset session for next time
        store.clear_session(sender)
        return reply

    except Exception as e:
        logger.error(f"Order finalisation failed for {sender}: {e}")
        store.set_state(sender, "collecting_payment")
        return (
            "Sorry, something went wrong placing your order. 😔\n"
            "Please try again or call us directly."
        )


async def _finalise_order(sender: str, payment: str, settings):
    """Build CreateOrderSchema from session data and call order_service."""
    items_raw = store.get_pending_items(sender)
    address = store.get_delivery_address(sender)
    customer_name = store.get_customer_name(sender)

    order_items = [
        OrderItemSchema(
            item_id=item.get("id", item["name"].lower().replace(" ", "_")),
            name=item["name"],
            quantity=item["quantity"],
            unit_price=item["unit_price"],
            total_price=item["total_price"],
        )
        for item in items_raw
    ]

    total = sum(i.total_price for i in order_items)

    data = CreateOrderSchema(
        customer_phone=sender,
        customer_name=customer_name,
        delivery_address=address,
        items=order_items,
        total_amount=total,
        payment_method=payment,
    )

    order = await create_order(data)

    # Update customer record
    await upsert_customer(sender, customer_name)

    return order


async def _handle_freeform(sender: str, text: str, settings) -> str:
    """Handle messages outside the ordering flow with AI."""
    store.add_message(sender, "user", text)
    reply = await _ai_freeform(sender, text, settings)
    store.add_message(sender, "assistant", reply)

    # If they're saying they want to order, nudge them
    order_signals = ["order", "buy", "want", "hungry", "food", "eat"]
    if any(word in text.lower() for word in order_signals):
        store.set_state(sender, "asked_intent")

    return reply


async def _ai_freeform(sender: str, text: str, settings) -> str:
    """Call AI for natural freeform conversation."""
    system = AMA_SYSTEM_PROMPT.format(
        restaurant_name=settings.restaurant_name,
        menu_url=settings.menu_web_app_url,
    )
    history = store.get_history(sender)

    return await get_ai_response(
        messages=[*history, {"role": "user", "content": text}],
        system_prompt=system,
        max_tokens=250,
        temperature=0.75,
    )
