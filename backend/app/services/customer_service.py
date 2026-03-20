"""
Customer Service.

Looks up returning customers by phone number in Supabase.
Fetches their last order for quick reorder suggestions.
Upserts customer records on each new order.
"""

import logging
from datetime import datetime, timezone
from app.database import get_supabase

logger = logging.getLogger(__name__)


async def get_customer(phone: str) -> dict | None:
    """
    Look up a customer by phone number.
    Returns customer dict or None if first-time visitor.
    """
    try:
        supabase = get_supabase()
        result = (
            supabase.table("customers")
            .select("*")
            .eq("phone", phone)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"Customer lookup failed for {phone}: {e}")
        return None


async def get_last_order(phone: str) -> dict | None:
    """
    Fetch the customer's most recent order from Supabase.
    Used by Ama to offer a quick reorder on return visits.
    """
    try:
        supabase = get_supabase()
        result = (
            supabase.table("orders")
            .select("id, items, total_amount, created_at")
            .eq("customer_phone", phone)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"Last order lookup failed for {phone}: {e}")
        return None


async def upsert_customer(phone: str, name: str | None = None) -> None:
    """
    Create or update a customer record.
    Called after every successful order.
    """
    try:
        supabase = get_supabase()
        now = datetime.now(timezone.utc).isoformat()

        existing = await get_customer(phone)

        if existing:
            update_data = {"last_seen": now, "order_count": existing.get("order_count", 0) + 1}
            if name and not existing.get("name"):
                update_data["name"] = name

            supabase.table("customers").update(update_data).eq("phone", phone).execute()
        else:
            supabase.table("customers").insert({
                "phone": phone,
                "name": name,
                "order_count": 1,
                "first_seen": now,
                "last_seen": now,
            }).execute()

    except Exception as e:
        logger.error(f"Customer upsert failed for {phone}: {e}")


def format_returning_customer_greeting(customer: dict, last_order: dict | None, restaurant_name: str) -> str:
    """
    Build a personalised greeting for a returning customer.
    """
    name = customer.get("name", "")
    first_name = name.split()[0] if name else ""
    greeting_name = f" {first_name}" if first_name else ""

    if last_order and last_order.get("items"):
        items = last_order["items"]
        # Summarise last order in one line
        if len(items) == 1:
            last_item = f"{items[0]['quantity']}x {items[0]['name']}"
        elif len(items) == 2:
            last_item = f"{items[0]['name']} and {items[1]['name']}"
        else:
            last_item = f"{items[0]['name']} and {len(items) - 1} other items"

        total = last_order.get("total_amount", 0)

        return (
            f"Welcome back{greeting_name}! 👋\n\n"
            f"Last time you had *{last_item}* (GHS {total:.2f}).\n\n"
            f"Want the same again, or would you like to order something different? 😊"
        )

    return (
        f"Welcome back{greeting_name}! Great to see you again 👋\n\n"
        f"Ready to order? Do you know what you want, "
        f"or would you like to browse our menu?"
    )
