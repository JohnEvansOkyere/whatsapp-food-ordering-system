"""
Session Store.

Manages per-user WhatsApp conversation state in memory.
Each session tracks:
  - conversation history (for AI context)
  - current conversation state (what stage of ordering they're at)
  - pending order items (parsed but not yet confirmed)
  - branch ID (from QR code scan)

For multi-instance production: swap _store for Redis.
Max 30 messages per session to keep AI context lean.
"""

from datetime import datetime, timedelta, timezone
from typing import TypedDict, Literal

MAX_HISTORY = 30
MESSAGE_DEDUP_TTL_MINUTES = 10

ConversationState = Literal[
    "greeting",           # Just started
    "asked_intent",       # Asked "know what you want?"
    "taking_order",       # Customer is telling us what they want
    "clarifying_order",   # Picking between menu options or sending quantity
    "confirming_order",   # Showed order summary, waiting for yes/no
    "collecting_address", # Order confirmed, need delivery address
    "collecting_payment", # Have address, need payment method
    "done",               # Order placed
]


class Message(TypedDict):
    role: str
    content: str


class Session(TypedDict):
    history: list[Message]
    state: ConversationState
    branch_id: str | None
    pending_items: list[dict]   # Parsed order items awaiting confirmation
    order_clarification: dict | None  # pick_variant / quantity follow-up
    delivery_address: str | None
    payment_method: str | None  # "momo" | "cash"
    customer_name: str | None


_store: dict[str, Session] = {}
_processed_message_ids: dict[str, datetime] = {}


def get_session(phone: str) -> Session:
    if phone not in _store:
        _store[phone] = _empty_session()
    return _store[phone]


def _empty_session() -> Session:
    return {
        "history": [],
        "state": "greeting",
        "branch_id": None,
        "pending_items": [],
        "order_clarification": None,
        "delivery_address": None,
        "payment_method": None,
        "customer_name": None,
    }


def add_message(phone: str, role: str, content: str) -> None:
    session = get_session(phone)
    session["history"].append({"role": role, "content": content})
    # Trim oldest messages to keep context window manageable
    if len(session["history"]) > MAX_HISTORY:
        session["history"] = session["history"][-MAX_HISTORY:]


def get_history(phone: str) -> list[Message]:
    return get_session(phone)["history"]


def set_state(phone: str, state: ConversationState) -> None:
    get_session(phone)["state"] = state


def get_state(phone: str) -> ConversationState:
    return get_session(phone)["state"]


def set_pending_items(phone: str, items: list[dict]) -> None:
    get_session(phone)["pending_items"] = items


def get_pending_items(phone: str) -> list[dict]:
    return get_session(phone).get("pending_items", [])


def set_order_clarification(phone: str, data: dict | None) -> None:
    get_session(phone)["order_clarification"] = data


def get_order_clarification(phone: str) -> dict | None:
    return get_session(phone).get("order_clarification")


def set_branch_id(phone: str, branch_id: str) -> None:
    get_session(phone)["branch_id"] = branch_id


def get_branch_id(phone: str) -> str | None:
    return get_session(phone).get("branch_id")


def set_delivery_address(phone: str, address: str) -> None:
    get_session(phone)["delivery_address"] = address


def get_delivery_address(phone: str) -> str | None:
    return get_session(phone).get("delivery_address")


def set_payment_method(phone: str, method: str) -> None:
    get_session(phone)["payment_method"] = method


def get_payment_method(phone: str) -> str | None:
    return get_session(phone).get("payment_method")


def set_customer_name(phone: str, name: str) -> None:
    get_session(phone)["customer_name"] = name


def get_customer_name(phone: str) -> str | None:
    return get_session(phone).get("customer_name")


def clear_session(phone: str) -> None:
    """Reset after order is placed or conversation abandoned."""
    _store[phone] = _empty_session()


def has_processed_message(message_id: str) -> bool:
    """Return True if this WhatsApp message id was processed recently."""
    _prune_processed_message_ids()
    return message_id in _processed_message_ids


def mark_message_processed(message_id: str) -> None:
    """Remember a WhatsApp message id to avoid duplicate replies."""
    _prune_processed_message_ids()
    _processed_message_ids[message_id] = datetime.now(timezone.utc)


def _prune_processed_message_ids() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=MESSAGE_DEDUP_TTL_MINUTES)
    stale_ids = [
        message_id
        for message_id, seen_at in _processed_message_ids.items()
        if seen_at < cutoff
    ]
    for message_id in stale_ids:
        _processed_message_ids.pop(message_id, None)
