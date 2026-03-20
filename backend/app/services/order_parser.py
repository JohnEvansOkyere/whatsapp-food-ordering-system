"""
Order Parser.

Takes a natural language order from WhatsApp chat
and extracts structured order items using the AI cascade.

Example input:
  "I want 2 jollof rice with chicken, 1 sobolo and add some plantain"

Example output:
  [
    {"name": "Jollof Rice + Chicken", "quantity": 2, "unit_price": 45.0},
    {"name": "Sobolo", "quantity": 1, "unit_price": 12.0},
    {"name": "Fried Plantain", "quantity": 1, "unit_price": 18.0},
  ]
"""

import json
import logging
from app.services.ai_service import get_ai_response

logger = logging.getLogger(__name__)

# Full menu passed to the parser so it can match items accurately
MENU_CONTEXT = """
FULL MENU WITH PRICES (GHS):
Rice Dishes:
- Jollof Rice + Chicken: 45.00
- Jollof Rice + Beef: 42.00
- Fried Rice + Chicken: 45.00
- Waakye Special: 40.00

Chicken:
- Grilled Chicken (2 pcs): 55.00
- Fried Chicken (3 pcs): 50.00
- Spicy Wings (6 pcs): 48.00

Pizza:
- BBQ Chicken Pizza: 85.00
- Pepperoni Pizza: 80.00

Sides:
- Chips Large: 20.00
- Fried Plantain: 18.00
- Coleslaw: 12.00

Drinks:
- Sobolo: 12.00
- Malta Guinness: 10.00
- Voltic Water 1.5L: 8.00
"""

PARSER_SYSTEM_PROMPT = f"""
You are a food order parser for a Ghanaian restaurant.

{MENU_CONTEXT}

Your job: Extract food items from a customer's message and return ONLY a JSON array.

Rules:
- Match menu items even if the customer uses informal names
  (e.g. "jollof" = "Jollof Rice + Chicken", "wings" = "Spicy Wings (6 pcs)")
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


async def parse_order_from_text(customer_message: str) -> list[dict]:
    """
    Parse a natural language order message into structured items.
    Returns a list of order item dicts, or empty list if nothing matched.
    """
    messages = [{"role": "user", "content": customer_message}]

    raw = await get_ai_response(
        messages=messages,
        system_prompt=PARSER_SYSTEM_PROMPT,
        max_tokens=400,
        temperature=0.1,  # Low temp — we want deterministic extraction
    )

    try:
        # Strip markdown code fences if AI adds them
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()

        items = json.loads(clean)

        if not isinstance(items, list):
            raise ValueError("Expected a list")

        # Validate each item has required fields
        validated = []
        for item in items:
            if all(k in item for k in ["name", "quantity", "unit_price"]):
                validated.append({
                    "name": str(item["name"]),
                    "quantity": int(item["quantity"]),
                    "unit_price": float(item["unit_price"]),
                    "total_price": round(int(item["quantity"]) * float(item["unit_price"]), 2),
                })

        return validated

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        logger.error(f"Order parse failed. Raw: {raw!r} | Error: {e}")
        return []


def format_order_for_confirmation(items: list[dict], restaurant_name: str) -> str:
    """
    Build a WhatsApp confirmation message from parsed items.
    Sent to customer before they confirm the order.
    """
    if not items:
        return ""

    lines = []
    total = 0.0

    for item in items:
        lines.append(
            f"  • {item['quantity']}x {item['name']} — GHS {item['total_price']:.2f}"
        )
        total += item["total_price"]

    items_block = "\n".join(lines)

    return (
        f"📋 *Here's your order:*\n\n"
        f"{items_block}\n\n"
        f"*Total: GHS {total:.2f}*\n\n"
        f"Is this correct? Reply *Yes* to confirm or *No* to change it."
    )
