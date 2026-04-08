"""
Menu data for API and WhatsApp order matching.

Tries Supabase first; falls back to static items aligned with frontend/src/lib/menuData.ts.
"""

import logging
from typing import Any

from app.database import get_supabase

logger = logging.getLogger(__name__)

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
    },
    {
        "id": "fried-rice-chicken",
        "name": "Fried Rice + Chicken",
        "description": "Fluffy fried rice with mixed vegetables, egg, and seasoned fried chicken.",
        "price": 45,
        "image_url": "https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=600&q=80",
        "category": "rice",
        "popular": True,
    },
    {
        "id": "fried-rice-beef",
        "name": "Fried Rice + Beef",
        "description": "Fluffy fried rice with mixed vegetables, egg, and tender stewed beef.",
        "price": 42,
        "image_url": "https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=600&q=80",
        "category": "rice",
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
    },
    {
        "id": "jollof-beef",
        "name": "Jollof Rice + Beef",
        "description": "Our signature smoky jollof with tender stewed beef and fresh salad.",
        "price": 42,
        "image_url": "https://images.unsplash.com/photo-1512058564366-18510be2db19?w=600&q=80",
        "category": "rice",
    },
    {
        "id": "grilled-chicken",
        "name": "Grilled Chicken (2 pcs)",
        "description": "Marinated in local spices, slow-grilled to perfection. Served with chips and pepper sauce.",
        "price": 55,
        "image_url": "https://images.unsplash.com/photo-1532550907401-a500c9a57435?w=600&q=80",
        "category": "chicken",
        "popular": True,
    },
    {
        "id": "fried-chicken",
        "name": "Fried Chicken (3 pcs)",
        "description": "Golden crispy fried chicken with our house seasoning. Comes with coleslaw.",
        "price": 50,
        "image_url": "https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?w=600&q=80",
        "category": "chicken",
    },
    {
        "id": "spicy-wings",
        "name": "Spicy Wings (6 pcs)",
        "description": "Fiery hot wings tossed in our signature pepper sauce. Not for the faint-hearted.",
        "price": 48,
        "image_url": "https://images.unsplash.com/photo-1567620832903-9fc6debc209f?w=600&q=80",
        "category": "chicken",
        "spicy": True,
    },
    {
        "id": "pepperoni-pizza",
        "name": "Pepperoni Pizza",
        "description": "Classic pepperoni on rich tomato sauce with melted mozzarella. 10-inch.",
        "price": 80,
        "image_url": "https://images.unsplash.com/photo-1628840042765-356cda07504e?w=600&q=80",
        "category": "pizza",
    },
    {
        "id": "chicken-pizza",
        "name": "BBQ Chicken Pizza",
        "description": "Smoky BBQ base, grilled chicken, red onions, and mozzarella. 10-inch.",
        "price": 85,
        "image_url": "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=600&q=80",
        "category": "pizza",
        "popular": True,
    },
    {
        "id": "chips",
        "name": "Chips (Large)",
        "description": "Crispy golden chips seasoned with our house spice blend.",
        "price": 20,
        "image_url": "https://images.unsplash.com/photo-1573080496219-bb080dd4f877?w=600&q=80",
        "category": "sides",
    },
    {
        "id": "coleslaw",
        "name": "Coleslaw",
        "description": "Fresh creamy coleslaw made daily.",
        "price": 12,
        "image_url": "https://images.unsplash.com/photo-1625944525533-473f1a3d54e7?w=600&q=80",
        "category": "sides",
    },
    {
        "id": "plantain",
        "name": "Fried Plantain",
        "description": "Sweet ripe plantain, perfectly fried. A Ghanaian classic.",
        "price": 18,
        "image_url": "https://images.unsplash.com/photo-1604329760661-e71dc83f8f26?w=600&q=80",
        "category": "sides",
    },
    {
        "id": "sobolo",
        "name": "Sobolo (Zobo)",
        "description": "Chilled hibiscus drink with ginger and spices. Refreshing and local.",
        "price": 12,
        "image_url": "https://images.unsplash.com/photo-1563227812-0ea4c22e6cc8?w=600&q=80",
        "category": "drinks",
    },
    {
        "id": "malt",
        "name": "Malta Guinness",
        "description": "The classic Ghanaian celebration drink. Cold and sweet.",
        "price": 10,
        "image_url": "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=600&q=80",
        "category": "drinks",
    },
    {
        "id": "water",
        "name": "Voltic Water (1.5L)",
        "description": "Ice cold Voltic mineral water.",
        "price": 8,
        "image_url": "https://images.unsplash.com/photo-1548839140-29a749e1cf4d?w=600&q=80",
        "category": "drinks",
    },
]


async def fetch_menu_items() -> list[dict[str, Any]]:
    """Active menu items for ordering and /menu API."""
    try:
        supabase = get_supabase()
        result = supabase.table("menu_items").select("*").eq("active", True).execute()
        if result.data:
            return list(result.data)
    except Exception as e:
        logger.warning(f"Supabase menu fetch failed, using static fallback: {e}")
    return [dict(item) for item in STATIC_MENU_ITEMS]


def normalize_price(row: dict[str, Any]) -> float:
    price = row.get("price")
    if price is None:
        return 0.0
    return float(price)
