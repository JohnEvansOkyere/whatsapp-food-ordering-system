"""
Order parsing for WhatsApp: AI extraction + deterministic menu matching
for vague requests (e.g. "fried rice" -> suggest variants, then quantity).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal, TypedDict

from app.services.ai_service import get_ai_response
from app.services.menu_service import fetch_menu_items, normalize_price

logger = logging.getLogger(__name__)

WORD_NUMBERS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


class OrderLine(TypedDict):
    id: str
    name: str
    quantity: int
    unit_price: float
    total_price: float


class OrderInterpretation(TypedDict):
    kind: Literal["ready", "need_pick", "need_quantity", "empty"]
    items: list[OrderLine]
    candidates: list[dict[str, Any]]
    reply_hint: str


def _build_menu_context(menu_items: list[dict[str, Any]]) -> str:
    lines: list[str] = ["FULL MENU WITH PRICES (GHS):"]
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for row in menu_items:
        cat = str(row.get("category", "other"))
        by_cat.setdefault(cat, []).append(row)
    for cat in sorted(by_cat.keys()):
        lines.append(f"\n{cat.title()}:")
        for row in by_cat[cat]:
            lines.append(f"- {row['name']}: {normalize_price(row):.2f}")
    return "\n".join(lines)


def _parser_system_prompt(menu_context: str) -> str:
    return f"""
You are a food order parser for a Ghanaian restaurant.

{menu_context}

Your job: Extract food items from a customer's message and return ONLY a JSON array.

Rules:
- Match menu items even if the customer uses informal names
  (e.g. "jollof" may map to Jollof Rice + Chicken if they specify chicken or it's the only jollof match)
- If quantity is not specified, assume 1
- Use exact menu item names and prices from the list above
- If an item cannot be matched to any menu item, skip it
- Return ONLY valid JSON, no explanation, no markdown

Output format:
[
  {{"name": "Item Name", "quantity": 2, "unit_price": 45.00}},
  {{"name": "Item Name", "quantity": 1, "unit_price": 12.00}}
]

If nothing can be matched, return an empty array: []
"""


def _tokenize(msg: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", msg.lower()))


def _name_tokens(name: str) -> set[str]:
    raw = re.findall(r"[a-z0-9]+", name.lower())
    return {t for t in raw if len(t) > 1}


def _score_item(msg_lower: str, msg_tokens: set[str], item: dict[str, Any]) -> float:
    name = str(item.get("name", "")).lower()
    score = 0.0
    for token in _name_tokens(name):
        if token in msg_lower:
            score += 3.0
        elif token in msg_tokens and len(token) >= 3:
            score += 1.5
    if "fried" in name and "rice" in name and "fried" in msg_lower and "rice" in msg_lower:
        score += 4.0
    if "jollof" in name and "jollof" in msg_lower:
        score += 4.0
    return score


def _filter_by_protein(msg_lower: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(candidates) <= 1:
        return candidates
    if "chicken" in msg_lower and "beef" not in msg_lower:
        filtered = [candidate for candidate in candidates if "chicken" in str(candidate.get("name", "")).lower()]
        return filtered or candidates
    if "beef" in msg_lower and "chicken" not in msg_lower:
        filtered = [candidate for candidate in candidates if "beef" in str(candidate.get("name", "")).lower()]
        return filtered or candidates
    return candidates


def find_menu_candidates(customer_message: str, menu_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return menu rows that plausibly match a vague or short order phrase."""
    stop = {
        "i", "want", "to", "order", "get", "me", "please", "the", "a", "an", "some",
        "hey", "hi", "hello", "for", "like", "would", "love", "need", "can", "could",
        "us", "we", "my", "give", "grab", "add", "also", "and", "with", "pls",
    }
    msg_lower = customer_message.lower().strip()
    msg_tokens = _tokenize(msg_lower) - stop

    scored: list[tuple[float, dict[str, Any]]] = []
    for item in menu_items:
        if not item.get("name"):
            continue
        score = _score_item(msg_lower, msg_tokens, item)
        if score >= 4.0:
            scored.append((score, item))

    scored.sort(key=lambda item: -item[0])
    if not scored:
        return []

    top = scored[0][0]
    close = [row for score, row in scored if score >= top - 1.5 and score >= 4.0]
    close = _filter_by_protein(msg_lower, close)
    return close


def extract_quantity(customer_message: str) -> int | None:
    text = customer_message.lower().strip()
    match = re.search(r"\b(\d{1,2})\s*(x|pcs|pc|plates?|orders?|portions?|bowls?)?\b", text)
    if match:
        number = int(match.group(1))
        if 1 <= number <= 99:
            return number
    match = re.search(r"\b(\d{1,2})\b", text)
    if match:
        number = int(match.group(1))
        if 1 <= number <= 99:
            return number
    for word, number in WORD_NUMBERS.items():
        if re.search(rf"\b{re.escape(word)}\b", text):
            return number
    return None


def _menu_row_to_line(row: dict[str, Any], quantity: int) -> OrderLine:
    price = normalize_price(row)
    safe_quantity = max(1, quantity)
    total = round(safe_quantity * price, 2)
    return {
        "id": str(row["id"]),
        "name": str(row["name"]),
        "quantity": safe_quantity,
        "unit_price": price,
        "total_price": total,
    }


def make_order_line(row: dict[str, Any], quantity: int) -> dict[str, Any]:
    """Build a pending cart line dict from a menu row."""
    return dict(_menu_row_to_line(row, quantity))


def _validate_ai_items(raw_items: list[dict[str, Any]], menu_items: list[dict[str, Any]]) -> list[OrderLine]:
    by_name = {str(item["name"]).lower(): item for item in menu_items if item.get("name")}
    out: list[OrderLine] = []
    for item in raw_items:
        if not all(key in item for key in ("name", "quantity", "unit_price")):
            continue
        key = str(item["name"]).strip().lower()
        row = by_name.get(key)
        if not row:
            for menu_item in menu_items:
                menu_name = str(menu_item.get("name", "")).lower()
                if menu_name == key or menu_name.startswith(key) or key in menu_name:
                    row = menu_item
                    break
        if not row:
            continue
        quantity = int(item["quantity"])
        out.append(_menu_row_to_line(row, quantity))
    return out


async def parse_order_from_text(
    customer_message: str,
    menu_items: list[dict[str, Any]] | None = None,
) -> list[dict]:
    """
    Parse a natural language order using AI.
    Returns list of item dicts compatible with session pending_items / OrderItemSchema.
    """
    if menu_items is None:
        menu_items = await fetch_menu_items()

    menu_context = _build_menu_context(menu_items)
    system_prompt = _parser_system_prompt(menu_context)
    messages = [{"role": "user", "content": customer_message}]

    raw = await get_ai_response(
        messages=messages,
        system_prompt=system_prompt,
        max_tokens=500,
        temperature=0.1,
    )

    try:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()
        items = json.loads(clean)
        if not isinstance(items, list):
            raise ValueError("Expected a list")
        validated = _validate_ai_items(items, menu_items)
        return [dict(item) for item in validated]
    except (json.JSONDecodeError, ValueError, KeyError, TypeError) as e:
        logger.error(f"Order parse failed. Raw: {raw!r} | Error: {e}")
        return []


async def interpret_order_message(
    customer_message: str,
    menu_items: list[dict[str, Any]] | None = None,
) -> OrderInterpretation:
    """
    Full interpretation: exact AI parse first, then deterministic suggestions
    for vague items and quantity follow-up.
    """
    if menu_items is None:
        menu_items = await fetch_menu_items()

    ai_items = await parse_order_from_text(customer_message, menu_items)
    if ai_items:
        return {"kind": "ready", "items": ai_items, "candidates": [], "reply_hint": ""}

    candidates = find_menu_candidates(customer_message, menu_items)
    candidates = _filter_by_protein(customer_message.lower(), candidates)

    quantity = extract_quantity(customer_message)

    if len(candidates) > 1:
        lines = "\n".join(
            f"{index + 1}️⃣ *{candidate['name']}* — GHS {normalize_price(candidate):.2f}"
            for index, candidate in enumerate(candidates[:6])
        )
        count = len(candidates[:6])
        message = (
            f"I found a few options that match:\n\n{lines}\n\n"
            f"Reply with *1–{count}* or the name (e.g. *chicken* / *beef*). "
            f"I'll ask how many portions next. 😊"
        )
        return {
            "kind": "need_pick",
            "items": [],
            "candidates": candidates[:6],
            "reply_hint": message,
        }

    if len(candidates) == 1:
        row = candidates[0]
        if quantity is not None:
            line = _menu_row_to_line(row, quantity)
            return {"kind": "ready", "items": [line], "candidates": [], "reply_hint": ""}
        message = (
            f"Got it — *{row['name']}* is *GHS {normalize_price(row):.2f}*.\n\n"
            f"How many would you like? (Just send a number, e.g. *2*)"
        )
        return {
            "kind": "need_quantity",
            "items": [],
            "candidates": [row],
            "reply_hint": message,
        }

    return {
        "kind": "empty",
        "items": [],
        "candidates": [],
        "reply_hint": "",
    }


def format_order_for_confirmation(items: list[dict], restaurant_name: str) -> str:
    """Build a WhatsApp confirmation message from parsed items."""
    if not items:
        return ""

    lines: list[str] = []
    total = 0.0

    for item in items:
        lines.append(
            f"  • {item['quantity']}x {item['name']} — GHS {item['total_price']:.2f}"
        )
        total += float(item["total_price"])

    items_block = "\n".join(lines)

    return (
        f"📋 *Here's your order:*\n\n"
        f"{items_block}\n\n"
        f"*Total: GHS {total:.2f}*\n\n"
        f"Is this correct? Reply *Yes* to confirm or *No* to change it."
    )


def match_candidate_selection(text: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Map user reply (number or name fragment) to one of the candidate menu rows."""
    lowered = text.strip().lower()
    if not lowered:
        return None
    match = re.match(r"^(\d{1,2})\b", lowered)
    if match:
        index = int(match.group(1)) - 1
        if 0 <= index < len(candidates):
            return candidates[index]
    for candidate in candidates:
        name = str(candidate.get("name", "")).lower()
        if len(lowered) >= 3 and lowered in name:
            return candidate
        parts = name.replace("+", " ").split()
        if lowered in parts:
            return candidate
    return None
