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
import re
from app.config import get_settings
from app.services.ai_service import get_ai_response
from app.services import session_store as store
from app.services.menu_service import fetch_menu_items, normalize_price
from app.services.order_parser import (
    format_order_for_confirmation,
    interpret_order_message,
    match_candidate_selection,
    extract_quantity,
    make_order_line,
)
from app.services.customer_service import (
    get_customer,
    get_last_order,
    get_latest_order_status,
    format_returning_customer_greeting,
)
from app.services.order_service import create_order
from app.services.order_service import get_status_label
from app.schemas.order import CreateOrderSchema, OrderItemSchema

logger = logging.getLogger(__name__)

AMA_SYSTEM_PROMPT = """\
You are Ama, the friendly WhatsApp food ordering assistant for {restaurant_name} in Accra, Ghana.

YOUR PERSONALITY:
- Warm, helpful, natural — like a real Ghanaian restaurant cashier
- Sound like a proper restaurant rep, not a bot or call center script
- Short replies — WhatsApp is not email. 1–3 sentences max unless listing menu suggestions
- Occasional light local expressions are fine (Chale, sure, no problem)
- Never sound robotic or scripted
- Never make up menu items or prices

YOUR ROLE IN THIS CONVERSATION:
You are responsible for handling customer questions about food ordering end to end.
Your job in freeform conversation is to:
- Answer questions about the menu, prices, ingredients, spice level, portions, delivery, payment, location, hours, and order flow
- Help undecided customers choose food naturally
- If a customer says they are hungry, suggest 2 or 3 real menu items naturally
- If a customer asks for breakfast, lunch, dinner, something refreshing, or a light or filling meal, infer the best fits from the live menu
- If a customer says thank you, no thanks, or not now, reply warmly like a human rep
- Handle small talk warmly and redirect to ordering
- If a customer seems confused, offer the menu link: {menu_url}
- If a customer asks what is available, mention only real menu items or send the menu link
- If a customer asks for a recommendation, suggest 2 or 3 real items with prices and include the menu link
- Only answer restaurant, menu, food, drink, delivery, payment, location, and order-related questions
- If asked about something outside the restaurant or food domain, politely say you can only help with the menu, recommendations, and orders
- If the customer asks something you cannot confirm from the facts below, do not guess. Tell them to reach customer support on {support_whatsapp}

RESTAURANT INFO:
- Location: Osu, Accra
- Hours: Mon–Sun, 10am–10pm
- Delivery: Within Accra, free delivery
- Usual delivery time: 45–60 minutes depending on traffic
- Payment: MoMo or Cash on delivery

LIVE MENU AND DESCRIPTIONS:
{menu_context}

Full menu with photos: {menu_url}
Customer support: {support_whatsapp}

IMPORTANT: Keep it short and human. This is WhatsApp.
- Never invent details that are not in the restaurant info or menu context above
- If you are unsure, say so briefly and direct the customer to {support_whatsapp}
"""

BROWSE_SIGNALS = [
    "browse", "menu", "see", "show", "look", "photo", "picture",
    "not sure", "idk", "don't know", "dont know", "what do you have",
    "what's on the menu", "whats on the menu",
]
RECOMMENDATION_SIGNALS = [
    "recommend", "suggest", "what should i eat", "what do you recommend",
    "what would you recommend", "help me choose", "pick for me", "something for",
]
DISCOVERY_SIGNALS = [
    "breakfast", "lunch", "dinner", "supper", "snack", "light",
    "filling", "heavy", "hot today", "feeling hot", "refreshing",
    "cold drink", "cool me down", "thirsty", "hungry",
]
REORDER_SIGNALS = ["same", "again", "repeat", "last", "previous"]
GREETING_WORDS = {
    "hi", "hello", "hey", "yo", "hola", "morning", "afternoon", "evening",
    "good", "sup", "please",
}
ORDER_HINTS = [
    "jollof", "waakye", "fried rice", "pizza", "chips", "plantain",
    "sobolo", "malt", "water", "wings", "grilled chicken", "fried chicken",
    "beef", "chicken", "rice",
]
ORDER_INTENT_SIGNALS = [
    "i want", "i'll have", "give me", "order", "get me", "i need",
    "can i get", "let me get", "send me",
]
THANKS_SIGNALS = ["thank you", "thanks", "thank u", "thx", "okay thanks", "alright thanks"]
PAUSE_SIGNALS = [
    "not now", "don't need", "dont need", "maybe later", "later", "just browsing",
    "just looking", "nothing now", "no thanks", "no thank you", "that will be all",
    "that's all", "thats all", "i'm okay", "im okay", "i am okay",
]
STATUS_SIGNALS = [
    "status of my order", "what's the status", "whats the status", "order status",
    "where is my order", "track my order", "how far is my order", "is my order ready",
]
UNCERTAIN_REPLY_SIGNALS = [
    "i'm not sure", "i am not sure", "i dont know", "i don't know", "not certain",
    "can't confirm", "cannot confirm", "having trouble right now", "try again in a moment",
    "call us directly", "please try again later",
]
RESTAURANT_TOPIC_SIGNALS = [
    "menu", "food", "dish", "meal", "breakfast", "lunch", "dinner", "supper",
    "drink", "drinks", "hungry", "eat", "restaurant", "order", "delivery", "deliver",
    "payment", "momo", "cash", "price", "cost", "open", "close", "hours", "location",
    "address", "spicy", "pepper", "ingredient", "portion", "recommend", "suggest",
    "jollof", "waakye", "fried rice", "pizza", "chicken", "chips", "plantain",
    "sobolo", "malt", "water",
]


async def handle_incoming_message(sender: str, text: str, branch_id: str | None = None) -> str:
    """
    Main entry point for all incoming WhatsApp messages.
    Routes based on current conversation state.
    Returns the reply to send back to the customer.
    """
    settings = get_settings()
    state = store.get_state(sender)

    if branch_id:
        store.set_branch_id(sender, branch_id)

    text_lower = text.lower().strip()

    if _is_order_status_request(text_lower):
        return await _handle_order_status_request(sender)

    if state == "greeting":
        return await _handle_greeting(sender, text, settings)

    if state == "asked_intent":
        return await _handle_intent_response(sender, text, settings)

    if state == "taking_order":
        return await _handle_order_input(sender, text, settings)

    if state == "clarifying_order":
        return await _handle_order_clarification(sender, text, settings)

    if state == "confirming_order":
        return await _handle_order_confirmation(sender, text_lower, settings)

    if state == "collecting_address":
        return await _handle_address_input(sender, text, settings)

    if state == "collecting_payment":
        return await _handle_payment_input(sender, text_lower, settings)

    return await _handle_freeform(sender, text, settings)


def _is_simple_greeting(text: str) -> bool:
    cleaned = re.sub(r"[^a-z0-9'\s]", " ", text.lower()).split()
    if not cleaned:
        return True
    return len(cleaned) <= 4 and all(token in GREETING_WORDS for token in cleaned)


def _wants_to_browse(text_lower: str) -> bool:
    return any(word in text_lower for word in BROWSE_SIGNALS)


def _looks_like_order_request(text_lower: str) -> bool:
    if not text_lower:
        return False
    if _looks_like_recommendation_request(text_lower):
        return False
    if extract_quantity(text_lower) is not None:
        return True
    if any(phrase in text_lower for phrase in ORDER_INTENT_SIGNALS):
        return True
    return any(hint in text_lower for hint in ORDER_HINTS)


def _is_thanks_message(text_lower: str) -> bool:
    return any(signal in text_lower for signal in THANKS_SIGNALS)


def _is_pause_message(text_lower: str) -> bool:
    return any(signal in text_lower for signal in PAUSE_SIGNALS)


def _is_order_status_request(text_lower: str) -> bool:
    if any(signal in text_lower for signal in STATUS_SIGNALS):
        return True
    return "order" in text_lower and "status" in text_lower


def _looks_like_recommendation_request(text_lower: str) -> bool:
    if any(signal in text_lower for signal in RECOMMENDATION_SIGNALS):
        return True
    if any(signal in text_lower for signal in DISCOVERY_SIGNALS):
        return not any(hint in text_lower for hint in ORDER_HINTS)
    return False


def _is_restaurant_or_food_query(text_lower: str) -> bool:
    if not text_lower:
        return True
    if _is_simple_greeting(text_lower) or _is_thanks_message(text_lower) or _is_pause_message(text_lower):
        return True
    if _is_order_status_request(text_lower):
        return True
    return any(signal in text_lower for signal in RESTAURANT_TOPIC_SIGNALS)


async def _try_interpret_order(sender: str, text: str, settings) -> str | None:
    if not _looks_like_order_request(text.lower().strip()):
        return None
    interp = await interpret_order_message(text)
    if interp["kind"] in ("ready", "need_pick", "need_quantity", "unavailable"):
        return await _apply_order_interpretation(sender, interp, settings)
    return None


def _close_out_chat(sender: str) -> None:
    store.clear_session(sender)


async def _handle_ordering_side_message(sender: str, text: str, settings) -> str | None:
    text_lower = text.lower().strip()

    if _is_thanks_message(text_lower):
        store.set_state(sender, "asked_intent")
        return "You’re welcome. If you need anything else, just send me a message."

    if _is_pause_message(text_lower):
        _close_out_chat(sender)
        return "No problem at all. If you need anything later, just message me here."

    if not _looks_like_order_request(text_lower):
        return await _handle_freeform(sender, text, settings)

    return None


async def _handle_order_status_request(sender: str) -> str:
    latest_order = await get_latest_order_status(sender)
    settings = get_settings()
    if not latest_order:
        return (
            "I can’t see any recent order on this WhatsApp number yet.\n\n"
            "If you placed it from the web app, make sure you used this same number at checkout.\n"
            f"If you still need help, please reach customer support on {settings.customer_support_whatsapp}."
        )

    status_value = str(latest_order.get("status", "new")).lower()
    order_id = str(latest_order.get("id", ""))[:8].upper()
    tracking_code = latest_order.get("tracking_code")
    status_label = get_status_label(status_value).lower()

    reply = (
        f"Your latest order *#{order_id}* is currently *{status_label}*.\n\n"
        "If you want, I can also help you place another order."
    )
    if tracking_code:
        reply = (
            f"{reply}\n\n"
            f"Tracking code: *{tracking_code}*"
        )
    return reply


async def _handle_greeting(sender: str, text: str, settings) -> str:
    """First message — route obvious order/menu requests before sending a greeting."""
    text_lower = text.lower().strip()
    customer = await get_customer(sender)
    last_order = await get_last_order(sender) if customer else None

    if _wants_to_browse(text_lower):
        store.set_state(sender, "taking_order")
        return (
            f"Sure, here is our menu with photos.\n\n"
            f"{settings.menu_web_app_url}\n\n"
            f"When you're ready, send me the dish and quantity here or place the order on the site."
        )

    order_reply = await _try_interpret_order(sender, text, settings)
    if order_reply:
        return order_reply

    if customer and last_order and any(word in text_lower for word in REORDER_SIGNALS):
        store.set_pending_items(sender, last_order["items"])
        store.set_state(sender, "confirming_order")
        return format_order_for_confirmation(last_order["items"], settings.restaurant_name)

    if customer:
        reply = format_returning_customer_greeting(customer, last_order, settings.restaurant_name)
        if last_order and _is_simple_greeting(text_lower):
            store.set_pending_items(sender, last_order["items"])
            store.set_state(sender, "asked_intent")
            return reply
        if _is_simple_greeting(text_lower):
            store.set_state(sender, "asked_intent")
            return reply

    if _is_simple_greeting(text_lower):
        store.set_state(sender, "asked_intent")
        return (
            f"Hello, welcome to *{settings.restaurant_name}*.\n\n"
            f"I'm Ama. What can I get for you today?\n"
            f"If you'd like, I can also send the full menu with photos."
        )

    store.set_state(sender, "asked_intent")
    return await _handle_freeform(sender, text, settings)


async def _handle_intent_response(sender: str, text: str, settings) -> str:
    """Customer responded to 'do you know what you want?' question."""
    text_lower = text.lower().strip()

    if _wants_to_browse(text_lower) or text_lower in {"no", "nope"}:
        store.set_state(sender, "taking_order")
        return (
            f"Sure, here is our menu with photos.\n\n"
            f"{settings.menu_web_app_url}\n\n"
            f"Browse and send me what you'd like, or place the order there and your receipt will come straight to WhatsApp."
        )

    pending = store.get_pending_items(sender)
    if (any(word in text_lower for word in REORDER_SIGNALS) or text_lower in {"yes", "yeah", "yep"}) and pending:
        store.set_state(sender, "confirming_order")
        confirmation = format_order_for_confirmation(pending, settings.restaurant_name)
        return confirmation

    recommendation_reply = await _maybe_handle_recommendation(sender, text, settings)
    if recommendation_reply:
        return recommendation_reply

    if text_lower in {"yes", "yeah", "yep"}:
        store.set_state(sender, "taking_order")
        return (
            "Alright. Please send the dish and quantity like *2 jollof rice with chicken* "
            "or *1 waakye*."
        )

    order_reply = await _try_interpret_order(sender, text, settings)
    if order_reply:
        return order_reply

    knows_signals = ["i want", "i'll have", "give me", "order", "get me", "i need", "sure", "okay", "ok"]
    if any(word in text_lower for word in knows_signals):
        store.set_state(sender, "taking_order")
        return (
            "Alright. Please send the dish and quantity like *2 jollof rice with chicken* "
            "or *1 waakye*."
        )

    store.add_message(sender, "user", text_lower)
    reply = await _ai_freeform(sender, text_lower, settings)
    store.add_message(sender, "assistant", reply)
    return reply


async def _apply_order_interpretation(sender, interp, settings) -> str:
    """Shared: move session forward from interpret_order_message result."""
    if interp["kind"] == "ready":
        store.set_pending_items(sender, interp["items"])
        store.set_state(sender, "confirming_order")
        store.set_order_clarification(sender, None)
        return format_order_for_confirmation(interp["items"], settings.restaurant_name)

    if interp["kind"] == "need_pick":
        store.set_order_clarification(
            sender,
            {"phase": "pick_variant", "candidates": interp["candidates"]},
        )
        store.set_state(sender, "clarifying_order")
        return interp["reply_hint"]

    if interp["kind"] == "need_quantity":
        store.set_order_clarification(
            sender,
            {"phase": "quantity", "item": interp["candidates"][0]},
        )
        store.set_state(sender, "clarifying_order")
        return interp["reply_hint"]

    if interp["kind"] == "unavailable":
        store.set_state(sender, "taking_order")
        store.set_order_clarification(sender, None)
        return interp["reply_hint"]

    return (
        "Sorry, I couldn't match that to our menu yet.\n\n"
        "Please send it like *2 jollof rice with chicken* or *1 fried rice with beef*.\n\n"
        f"Or browse everything with photos here:\n{settings.menu_web_app_url}"
    )


async def _handle_order_input(sender: str, text: str, settings) -> str:
    """Customer is telling us what they want via chat."""
    side_reply = await _handle_ordering_side_message(sender, text, settings)
    if side_reply:
        return side_reply

    interp = await interpret_order_message(text)
    return await _apply_order_interpretation(sender, interp, settings)


async def _handle_order_clarification(sender: str, text: str, settings) -> str:
    """User is picking between options or sending a quantity."""
    side_reply = await _handle_ordering_side_message(sender, text, settings)
    if side_reply:
        store.set_order_clarification(sender, None)
        return side_reply

    clar = store.get_order_clarification(sender) or {}
    phase = clar.get("phase")

    if phase == "pick_variant":
        candidates = clar.get("candidates") or []
        picked = match_candidate_selection(text, candidates)
        if not picked:
            return (
                "Please reply with the *number* next to the dish, "
                "or say the name like *chicken* or *beef*.\n\n"
                f"Full menu: {settings.menu_web_app_url}"
            )
        qty = extract_quantity(text)
        if qty is not None:
            line = make_order_line(picked, qty)
            store.set_order_clarification(sender, None)
            store.set_pending_items(sender, [line])
            store.set_state(sender, "confirming_order")
            return format_order_for_confirmation([line], settings.restaurant_name)
        price = float(picked.get("price", 0))
        store.set_order_clarification(sender, {"phase": "quantity", "item": picked})
        return (
            f"Okay, *{picked['name']}* is *GHS {price:.2f}*.\n\n"
            "How many would you like? Please send a number, for example *2*."
        )

    if phase == "quantity":
        item = clar.get("item")
        if not item:
            store.set_order_clarification(sender, None)
            store.set_state(sender, "taking_order")
            return "What would you like to order? 😊"
        qty = extract_quantity(text)
        if qty is None:
            return "Please send the quantity as a number, for example *2* or *3*."
        line = make_order_line(item, qty)
        store.set_order_clarification(sender, None)
        store.set_pending_items(sender, [line])
        store.set_state(sender, "confirming_order")
        return format_order_for_confirmation([line], settings.restaurant_name)

    store.set_order_clarification(sender, None)
    store.set_state(sender, "taking_order")
    return await _handle_order_input(sender, text, settings)


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
        store.set_order_clarification(sender, None)
        return (
            "No problem! Let's start again. 😊\n\n"
            "What would you like to order?"
        )

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

    try:
        order = await _finalise_order(sender, payment, settings)
        store.set_state(sender, "done")

        payment_label = "Mobile Money" if payment == "momo" else "Cash on Delivery"
        reply = (
            f"✅ *Order placed successfully!*\n\n"
            f"Order #{(order.order_number or order.id[:8].upper())}\n"
            f"Tracking: {order.tracking_code or 'N/A'}\n"
            f"Payment: {payment_label}\n\n"
            f"Your full receipt is coming right now 🧾\n"
            f"We'll deliver within 45–60 minutes. 🛵\n\n"
            f"Questions? Just reply here anytime!"
        )

        store.clear_session(sender)
        return reply

    except Exception as e:
        logger.error(f"Order finalisation failed for {sender}: {e}")
        store.set_state(sender, "collecting_payment")
        return (
            "Sorry, something went wrong placing your order. 😔\n"
            f"Please try again or reach customer support on {settings.customer_support_whatsapp}."
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

    total = sum(item.total_price for item in order_items)

    data = CreateOrderSchema(
        customer_phone=sender,
        customer_name=customer_name,
        delivery_address=address,
        items=order_items,
        total_amount=total,
        payment_method=payment,
    )

    order = await create_order(data)
    return order


async def _handle_freeform(sender: str, text: str, settings) -> str:
    """Handle messages outside the ordering flow with AI."""
    text_lower = text.lower().strip()

    known_reply = _handle_known_question(text_lower, settings)
    if known_reply:
        store.add_message(sender, "user", text)
        store.add_message(sender, "assistant", known_reply)
        return known_reply

    recommendation_reply = await _maybe_handle_recommendation(sender, text, settings)
    if recommendation_reply:
        store.add_message(sender, "user", text)
        store.add_message(sender, "assistant", recommendation_reply)
        return recommendation_reply

    if not _is_restaurant_or_food_query(text_lower):
        reply = _out_of_scope_message(settings)
        store.add_message(sender, "user", text)
        store.add_message(sender, "assistant", reply)
        return reply

    store.add_message(sender, "user", text)
    reply = await _ai_freeform(sender, text, settings)
    reply = _normalize_freeform_reply(reply, settings)
    store.add_message(sender, "assistant", reply)

    order_signals = ["order", "buy", "want", "hungry", "food", "eat"]
    if any(word in text.lower() for word in order_signals):
        store.set_state(sender, "asked_intent")

    return reply


async def _ai_freeform(sender: str, text: str, settings) -> str:
    """Call AI for natural freeform conversation."""
    system = await _build_freeform_system_prompt(settings)
    history = store.get_history(sender)

    return await get_ai_response(
        messages=[*history, {"role": "user", "content": text}],
        system_prompt=system,
        max_tokens=250,
        temperature=0.75,
    )


async def _build_freeform_system_prompt(settings) -> str:
    menu_items = await fetch_menu_items()
    menu_context = _build_menu_context(menu_items)
    return AMA_SYSTEM_PROMPT.format(
        restaurant_name=settings.restaurant_name,
        menu_url=settings.menu_web_app_url,
        support_whatsapp=settings.customer_support_whatsapp,
        menu_context=menu_context,
    )


def _build_menu_context(menu_items: list[dict]) -> str:
    if not menu_items:
        return "No live menu items were available."

    lines: list[str] = []
    for item in menu_items:
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        price = normalize_price(item)
        description = str(item.get("description", "")).strip()
        category = str(item.get("category", "other")).strip() or "other"
        if description:
            lines.append(f"- {name} ({category}) — GHS {price:.2f}: {description}")
        else:
            lines.append(f"- {name} ({category}) — GHS {price:.2f}")
    return "\n".join(lines)


async def _maybe_handle_recommendation(sender: str, text: str, settings) -> str | None:
    text_lower = text.lower().strip()
    if not _looks_like_recommendation_request(text_lower):
        return None

    menu_items = await fetch_menu_items()
    suggestions = _recommend_menu_items(text_lower, menu_items)
    store.set_state(sender, "taking_order")

    if not suggestions:
        return (
            "Sure, have a look at our full menu with photos here:\n"
            f"{settings.menu_web_app_url}\n\n"
            "When you're ready, send me the dish and quantity."
        )

    return _format_recommendation_reply(text_lower, suggestions, settings)


def _recommend_menu_items(text_lower: str, menu_items: list[dict], limit: int = 3) -> list[dict]:
    ranked: list[tuple[int, dict]] = []
    wants_cooling = any(
        signal in text_lower
        for signal in ["hot today", "feeling hot", "refreshing", "cold drink", "cool me down", "thirsty"]
    )
    wants_breakfast = "breakfast" in text_lower
    wants_lunch = "lunch" in text_lower
    wants_dinner = "dinner" in text_lower or "supper" in text_lower
    wants_light = "light" in text_lower
    wants_filling = any(signal in text_lower for signal in ["filling", "heavy", "hungry"])
    wants_spicy = any(signal in text_lower for signal in ["spicy", "pepper", "hot"])

    for item in menu_items:
        traits = _infer_menu_item_traits(item)
        score = 0

        if wants_breakfast and "breakfast" in traits:
            score += 6
        if wants_lunch and "lunch" in traits:
            score += 5
        if wants_dinner and "dinner" in traits:
            score += 5
        if wants_cooling and "cooling" in traits:
            score += 7
        if wants_cooling and "spicy" in traits:
            score -= 3
        if wants_light and "light" in traits:
            score += 4
        if wants_light and "filling" in traits:
            score -= 1
        if wants_filling and "filling" in traits:
            score += 4
        if wants_spicy and "spicy" in traits:
            score += 4
        if "popular" in traits:
            score += 2
        if any(flag in text_lower for flag in ["recommend", "suggest", "what should i eat", "what would you recommend"]):
            score += 1

        if score > 0:
            ranked.append((score, item))

    if not ranked:
        fallback = sorted(
            menu_items,
            key=lambda item: (
                1 if wants_cooling and "drink" in _infer_menu_item_traits(item) else 0,
                1 if item.get("popular") else 0,
                -normalize_price(item),
            ),
            reverse=True,
        )
        return fallback[:limit]

    ranked.sort(
        key=lambda entry: (
            entry[0],
            1 if entry[1].get("popular") else 0,
            -normalize_price(entry[1]),
        ),
        reverse=True,
    )

    picks: list[dict] = []
    seen: set[str] = set()
    for _score, item in ranked:
        item_id = str(item.get("id", item.get("name", "")))
        if not item_id or item_id in seen:
            continue
        seen.add(item_id)
        picks.append(item)
        if len(picks) >= limit:
            break
    return picks


def _infer_menu_item_traits(item: dict) -> set[str]:
    category = str(item.get("category", "")).lower()
    name = str(item.get("name", "")).lower()
    description = str(item.get("description", "")).lower()
    combined = f"{name} {description}"
    traits: set[str] = set()

    if item.get("popular"):
        traits.add("popular")
    if item.get("spicy") or any(word in combined for word in ["spicy", "pepper", "fiery", "hot"]):
        traits.add("spicy")

    if category == "drinks":
        traits.update({"drink", "cooling", "light"})
    if category == "rice":
        traits.update({"lunch", "dinner", "filling"})
    if category == "pizza":
        traits.update({"lunch", "dinner", "filling"})
    if category == "chicken":
        traits.update({"lunch", "dinner", "filling"})
    if category == "sides":
        traits.update({"light", "snack"})

    if any(word in combined for word in ["waakye", "egg"]):
        traits.update({"breakfast", "lunch", "filling"})
    if any(word in combined for word in ["jollof", "fried rice"]):
        traits.update({"lunch", "dinner", "filling"})
    if any(word in combined for word in ["sobolo", "zobo", "water", "malt", "chilled", "ice cold", "cold"]):
        traits.update({"drink", "cooling", "light"})
    if "grilled" in combined:
        traits.add("light")

    return traits


def _format_recommendation_reply(text_lower: str, suggestions: list[dict], settings) -> str:
    if "breakfast" in text_lower:
        intro = "For breakfast, these are my best picks:"
    elif "lunch" in text_lower:
        intro = "For lunch, I’d recommend these:"
    elif "dinner" in text_lower or "supper" in text_lower:
        intro = "For dinner, these are solid options:"
    elif any(signal in text_lower for signal in ["hot today", "feeling hot", "refreshing", "cold drink", "cool me down", "thirsty"]):
        intro = "Since you're feeling hot, these will cool you down nicely:"
    else:
        intro = "Here are a few good picks from our menu:"

    lines = [intro, ""]
    for item in suggestions:
        price = normalize_price(item)
        lines.append(f"- *{item['name']}* — GHS {price:.2f}")

    lines.extend(
        [
            "",
            f"Full menu with photos: {settings.menu_web_app_url}",
            "If you want, send me the dish and quantity here and I’ll help you place the order.",
        ]
    )
    return "\n".join(lines)


def _handle_known_question(text_lower: str, settings) -> str | None:
    support = settings.customer_support_whatsapp

    if any(word in text_lower for word in ["support", "help line", "customer care", "customer support", "contact", "phone number"]):
        return f"For extra help, please reach customer support on {support}."

    if any(word in text_lower for word in ["open", "close", "hours", "time do you", "when are you", "what time"]):
        return "We’re open every day from 10am to 10pm."

    if any(word in text_lower for word in ["where are you", "location", "located", "address", "where is the restaurant"]):
        return "We’re in Osu, Accra."

    if "delivery" in text_lower or "deliver" in text_lower:
        return "We deliver within Accra, delivery is free, and it usually takes about 45 to 60 minutes depending on traffic."

    if any(word in text_lower for word in ["payment", "pay", "momo", "cash"]):
        return "You can pay by MoMo or cash on delivery."

    if any(word in text_lower for word in ["menu link", "full menu", "menu please", "send menu"]):
        return f"Sure, here is our full menu with photos:\n{settings.menu_web_app_url}"

    return None


def _normalize_freeform_reply(reply: str, settings) -> str:
    cleaned = reply.strip()
    if not cleaned:
        return _support_handoff_message(settings)

    lower = cleaned.lower()
    if any(signal in lower for signal in UNCERTAIN_REPLY_SIGNALS):
        return _support_handoff_message(settings)

    return cleaned


def _support_handoff_message(settings) -> str:
    return (
        "I’m not fully sure about that one. "
        f"Please reach out to customer support on {settings.customer_support_whatsapp}."
    )


def _out_of_scope_message(settings) -> str:
    return (
        "I can help with our menu, food recommendations, prices, delivery, and orders.\n\n"
        f"You can also check the full menu here: {settings.menu_web_app_url}"
    )
