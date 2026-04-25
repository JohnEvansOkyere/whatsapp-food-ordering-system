"""
Customer service helpers.

Customer records remain compatibility-friendly with the current schema while the
rest of the application moves toward tenant-aware order operations.
"""

import logging
from datetime import datetime, timezone

from app.database import get_supabase

logger = logging.getLogger(__name__)


async def get_customer(phone: str) -> dict | None:
    """Look up a customer by phone number."""
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
    except Exception as exc:
        logger.error("Customer lookup failed for %s: %s", phone, exc)
        return None


async def get_last_order(phone: str) -> dict | None:
    """Fetch the customer's most recent order for reorder prompts."""
    try:
        supabase = get_supabase()
        result = (
            supabase.table("orders")
            .select("id, items, total_amount, created_at")
            .eq("customer_phone_snapshot", phone)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None
    except Exception as exc:
        logger.error("Last order lookup failed for %s: %s", phone, exc)
        return None


async def get_latest_order_status(phone: str) -> dict | None:
    """Fetch the customer's most recent order status for WhatsApp tracking."""
    try:
        supabase = get_supabase()
        result = (
            supabase.table("orders")
            .select("id, tracking_code, status, total_amount, created_at")
            .eq("customer_phone_snapshot", phone)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None
    except Exception as exc:
        logger.error("Latest order status lookup failed for %s: %s", phone, exc)
        return None


async def upsert_customer(
    phone: str,
    name: str | None = None,
    tenant_id: str | None = None,
    default_branch_id: str | None = None,
) -> dict | None:
    """Create or update a customer record and return the latest row when possible."""
    try:
        supabase = get_supabase()
        now = datetime.now(timezone.utc).isoformat()
        existing = await get_customer(phone)

        if existing:
            update_data: dict[str, object] = {
                "last_seen": now,
                "order_count": int(existing.get("order_count", 0)) + 1,
            }
            if name and not existing.get("name"):
                update_data["name"] = name
            if tenant_id:
                update_data["tenant_id"] = tenant_id
            if default_branch_id:
                update_data["default_branch_id"] = default_branch_id

            result = (
                supabase.table("customers")
                .update(update_data)
                .eq("phone", phone)
                .execute()
            )
            if result.data:
                return result.data[0]
            return await get_customer(phone)

        insert_data: dict[str, object] = {
            "phone": phone,
            "name": name,
            "order_count": 1,
            "first_seen": now,
            "last_seen": now,
        }
        if tenant_id:
            insert_data["tenant_id"] = tenant_id
        if default_branch_id:
            insert_data["default_branch_id"] = default_branch_id

        result = supabase.table("customers").insert(insert_data).execute()
        if result.data:
            return result.data[0]
        return await get_customer(phone)
    except Exception as exc:
        logger.error("Customer upsert failed for %s: %s", phone, exc)
        return None


def format_returning_customer_greeting(
    customer: dict,
    last_order: dict | None,
    restaurant_name: str,
) -> str:
    """Build a personalized greeting for a returning customer."""
    name = customer.get("name", "")
    first_name = name.split()[0] if name else ""
    greeting_name = f" {first_name}" if first_name else ""

    if last_order and last_order.get("items"):
        items = last_order["items"]
        if len(items) == 1:
            last_item = f"{items[0]['quantity']}x {items[0]['name']}"
        elif len(items) == 2:
            last_item = f"{items[0]['name']} and {items[1]['name']}"
        else:
            last_item = f"{items[0]['name']} and {len(items) - 1} other items"

        total = float(last_order.get("total_amount", 0) or 0)

        return (
            f"Welcome back{greeting_name}! 👋\n\n"
            f"Last time you had *{last_item}* (GHS {total:.2f}).\n\n"
            f"Want the same again, or would you like to order something different? 😊"
        )

    return (
        f"Welcome back{greeting_name}! Great to see you again 👋\n\n"
        f"Ready to order from *{restaurant_name}*? Do you know what you want, "
        f"or would you like to browse our menu?"
    )
