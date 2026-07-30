"""
Menu data for API and WhatsApp order matching.

Tries Supabase first; falls back to static items aligned with frontend/src/lib/menuData.ts.
"""

import logging
from typing import Any

from app.database import get_supabase

logger = logging.getLogger(__name__)

MENU_OPTION_GROUPS: dict[str, list[dict[str, Any]]] = {
    "jollof-chicken": [
        {
            "id": "extras",
            "name": "Add something extra",
            "type": "multiple",
            "max_selections": 2,
            "options": [
                {"id": "plantain", "name": "Fried plantain", "price": 8},
                {"id": "coleslaw", "name": "Extra coleslaw", "price": 5},
            ],
        }
    ],
    "fried-rice-chicken": [
        {
            "id": "extras",
            "name": "Add something extra",
            "type": "multiple",
            "max_selections": 2,
            "options": [
                {"id": "plantain", "name": "Fried plantain", "price": 8},
                {"id": "coleslaw", "name": "Extra coleslaw", "price": 5},
            ],
        }
    ],
    "pepperoni-pizza": [
        {
            "id": "size",
            "name": "Choose a size",
            "type": "single",
            "options": [
                {"id": "regular", "name": "Regular 10-inch", "price": 0},
                {"id": "large", "name": "Large 12-inch", "price": 25},
            ],
        },
        {
            "id": "extras",
            "name": "Pizza extras",
            "type": "multiple",
            "max_selections": 2,
            "options": [
                {"id": "cheese", "name": "Extra cheese", "price": 12},
                {"id": "chicken", "name": "Extra chicken", "price": 15},
            ],
        },
    ],
    "chicken-pizza": [
        {
            "id": "size",
            "name": "Choose a size",
            "type": "single",
            "options": [
                {"id": "regular", "name": "Regular 10-inch", "price": 0},
                {"id": "large", "name": "Large 12-inch", "price": 25},
            ],
        },
        {
            "id": "extras",
            "name": "Pizza extras",
            "type": "multiple",
            "max_selections": 2,
            "options": [
                {"id": "cheese", "name": "Extra cheese", "price": 12},
                {"id": "chicken", "name": "Extra chicken", "price": 15},
            ],
        },
    ],
}


def _with_options(row: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(row)
    enriched["option_groups"] = MENU_OPTION_GROUPS.get(str(row.get("id")), [])
    return enriched

# Static fallback — keep in sync with frontend/src/lib/menuData.ts
STATIC_MENU_ITEMS: list[dict[str, Any]] = [
    {
        "id": "jollof-chicken",
        "name": "Jollof Rice + Chicken",
        "description": "Smoky Ghanaian jollof cooked in fresh tomato base, served with crispy fried chicken and coleslaw.",
        "price": 45,
        "image_url": "https://images.unsplash.com/photo-1604329760661-e71dc83f8f26?w=600&q=80",
        "category": "rice",
        "popular": True,
        "spicy": True,
        "sold_out": False,
    },
    {
        "id": "fried-rice-chicken",
        "name": "Fried Rice + Chicken",
        "description": "Fluffy fried rice with mixed vegetables, egg, and seasoned fried chicken.",
        "price": 45,
        "image_url": "https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=600&q=80",
        "category": "rice",
        "popular": True,
        "sold_out": False,
    },
    {
        "id": "fried-rice-beef",
        "name": "Fried Rice + Beef",
        "description": "Fluffy fried rice with mixed vegetables, egg, and tender stewed beef.",
        "price": 42,
        "image_url": "https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=600&q=80",
        "category": "rice",
        "sold_out": False,
    },
    {
        "id": "waakye",
        "name": "Waakye Special",
        "description": "Classic waakye with spaghetti, egg, stew, and your choice of meat. The full Ghanaian experience.",
        "price": 40,
        "image_url": "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=600&q=80",
        "category": "rice",
        "popular": True,
        "spicy": True,
        "sold_out": False,
    },
    {
        "id": "jollof-beef",
        "name": "Jollof Rice + Beef",
        "description": "Our signature smoky jollof with tender stewed beef and fresh salad.",
        "price": 42,
        "image_url": "https://images.unsplash.com/photo-1512058564366-18510be2db19?w=600&q=80",
        "category": "rice",
        "sold_out": False,
    },
    {
        "id": "grilled-chicken",
        "name": "Grilled Chicken (2 pcs)",
        "description": "Marinated in local spices, slow-grilled to perfection. Served with chips and pepper sauce.",
        "price": 55,
        "image_url": "https://images.unsplash.com/photo-1532550907401-a500c9a57435?w=600&q=80",
        "category": "chicken",
        "popular": True,
        "sold_out": False,
    },
    {
        "id": "fried-chicken",
        "name": "Fried Chicken (3 pcs)",
        "description": "Golden crispy fried chicken with our house seasoning. Comes with coleslaw.",
        "price": 50,
        "image_url": "https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?w=600&q=80",
        "category": "chicken",
        "sold_out": False,
    },
    {
        "id": "spicy-wings",
        "name": "Spicy Wings (6 pcs)",
        "description": "Fiery hot wings tossed in our signature pepper sauce. Not for the faint-hearted.",
        "price": 48,
        "image_url": "https://images.unsplash.com/photo-1567620832903-9fc6debc209f?w=600&q=80",
        "category": "chicken",
        "spicy": True,
        "sold_out": False,
    },
    {
        "id": "pepperoni-pizza",
        "name": "Pepperoni Pizza",
        "description": "Classic pepperoni on rich tomato sauce with melted mozzarella. 10-inch.",
        "price": 80,
        "image_url": "https://images.unsplash.com/photo-1628840042765-356cda07504e?w=600&q=80",
        "category": "pizza",
        "sold_out": False,
    },
    {
        "id": "chicken-pizza",
        "name": "BBQ Chicken Pizza",
        "description": "Smoky BBQ base, grilled chicken, red onions, and mozzarella. 10-inch.",
        "price": 85,
        "image_url": "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=600&q=80",
        "category": "pizza",
        "popular": True,
        "sold_out": False,
    },
    {
        "id": "chips",
        "name": "Chips (Large)",
        "description": "Crispy golden chips seasoned with our house spice blend.",
        "price": 20,
        "image_url": "https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=600&q=80",
        "category": "sides",
        "sold_out": False,
    },
    {
        "id": "coleslaw",
        "name": "Coleslaw",
        "description": "Fresh creamy coleslaw made daily.",
        "price": 12,
        "image_url": "https://images.unsplash.com/photo-1625944525533-473f1a3d54e7?w=600&q=80",
        "category": "sides",
        "sold_out": False,
    },
    {
        "id": "plantain",
        "name": "Fried Plantain",
        "description": "Sweet ripe plantain, perfectly fried. A Ghanaian classic.",
        "price": 18,
        "image_url": "https://images.unsplash.com/photo-1604329760661-e71dc83f8f26?w=600&q=80",
        "category": "sides",
        "sold_out": False,
    },
    {
        "id": "sobolo",
        "name": "Sobolo (Zobo)",
        "description": "Chilled hibiscus drink with ginger and spices. Refreshing and local.",
        "price": 12,
        "image_url": "https://images.unsplash.com/photo-1563227812-0ea4c22e6cc8?w=600&q=80",
        "category": "drinks",
        "sold_out": False,
    },
    {
        "id": "malt",
        "name": "Malta Guinness",
        "description": "The classic Ghanaian celebration drink. Cold and sweet.",
        "price": 10,
        "image_url": "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=600&q=80",
        "category": "drinks",
        "sold_out": False,
    },
    {
        "id": "water",
        "name": "Voltic Water (1.5L)",
        "description": "Ice cold Voltic mineral water.",
        "price": 8,
        "image_url": "https://images.unsplash.com/photo-1548839140-29a749e1cf4d?w=600&q=80",
        "category": "drinks",
        "sold_out": False,
    },
]


def is_sold_out(row: dict[str, Any]) -> bool:
    return bool(row.get("sold_out", False))


def _filter_menu_rows(
    rows: list[dict[str, Any]],
    *,
    include_inactive: bool,
    include_sold_out: bool,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for row in rows:
        if not include_inactive and not bool(row.get("active", True)):
            continue
        if not include_sold_out and is_sold_out(row):
            continue
        filtered.append(dict(row))
    return filtered


async def fetch_menu_items(
    *,
    include_inactive: bool = False,
    include_sold_out: bool = False,
    branch_id: str | None = None,
) -> list[dict[str, Any]]:
    """Menu items for ordering, public menu, and admin availability views."""
    try:
        supabase = get_supabase()
        result = supabase.table("menu_items").select("*").execute()
        if result.data:
            rows = list(result.data)
            if branch_id:
                rows = [
                    row
                    for row in rows
                    if not row.get("branch_id")
                    or str(row.get("branch_id")) == branch_id
                ]
                try:
                    override_result = (
                        supabase.table("branch_menu_overrides")
                        .select("*")
                        .eq("branch_id", branch_id)
                        .execute()
                    )
                    overrides = {
                        str(row["menu_item_id"]): row
                        for row in (override_result.data or [])
                    }
                    merged_rows: list[dict[str, Any]] = []
                    for row in rows:
                        merged = dict(row)
                        override = overrides.get(str(row.get("id")))
                        if override:
                            if override.get("price_override") is not None:
                                merged["price"] = float(override["price_override"])
                            merged["sold_out"] = bool(override.get("sold_out", False))
                            merged["active"] = bool(override.get("active", True))
                            merged["branch_override"] = True
                        merged_rows.append(merged)
                    rows = merged_rows
                except Exception as exc:
                    logger.warning("Branch menu overrides unavailable: %s", exc)
            return [
                _with_options(row)
                for row in _filter_menu_rows(
                rows,
                include_inactive=include_inactive,
                include_sold_out=include_sold_out,
                )
            ]
    except Exception as e:
        logger.warning(f"Supabase menu fetch failed, using static fallback: {e}")
    rows = _filter_menu_rows(
        [dict(item) for item in STATIC_MENU_ITEMS],
        include_inactive=include_inactive,
        include_sold_out=include_sold_out,
    )
    if branch_id:
        rows = [
            row
            for row in rows
            if not row.get("branch_id")
            or str(row.get("branch_id")) == branch_id
        ]
    return [_with_options(row) for row in rows]


async def update_menu_item_availability(
    item_id: str,
    *,
    sold_out: bool | None = None,
    active: bool | None = None,
    branch_id: str | None = None,
) -> dict[str, Any] | None:
    update_payload: dict[str, Any] = {}
    if sold_out is not None:
        update_payload["sold_out"] = sold_out
    if active is not None:
        update_payload["active"] = active
    if not update_payload:
        return None

    supabase = get_supabase()
    if branch_id:
        existing = (
            supabase.table("branch_menu_overrides")
            .select("*")
            .eq("branch_id", branch_id)
            .eq("menu_item_id", item_id)
            .execute()
        )
        if existing.data:
            result = (
                supabase.table("branch_menu_overrides")
                .update(update_payload)
                .eq("id", existing.data[0]["id"])
                .execute()
            )
        else:
            result = (
                supabase.table("branch_menu_overrides")
                .insert(
                    {
                        "branch_id": branch_id,
                        "menu_item_id": item_id,
                        "sold_out": bool(sold_out) if sold_out is not None else False,
                        "active": bool(active) if active is not None else True,
                    }
                )
                .execute()
            )
        if result.data:
            matching = [
                item
                for item in await fetch_menu_items(
                    include_inactive=True,
                    include_sold_out=True,
                    branch_id=branch_id,
                )
                if str(item.get("id")) == item_id
            ]
            return matching[0] if matching else dict(result.data[0])
        return None

    result = (
        supabase.table("menu_items")
        .update(update_payload)
        .eq("id", item_id)
        .execute()
    )
    if result.data:
        return dict(result.data[0])
    return None


def normalize_price(row: dict[str, Any]) -> float:
    price = row.get("price")
    if price is None:
        return 0.0
    return float(price)
