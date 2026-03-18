from fastapi import APIRouter, HTTPException
from app.database import get_supabase
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/menu", tags=["menu"])


@router.get("/")
async def get_menu():
    """
    Get full menu. 
    For MVP, returns static data. Later you can manage items in Supabase.
    """
    try:
        supabase = get_supabase()
        result = supabase.table("menu_items").select("*").eq("active", True).execute()
        if result.data:
            return {"items": result.data}
    except Exception as e:
        logger.warning(f"Supabase menu fetch failed, using static fallback: {e}")

    # Static fallback — same data as frontend menuData.ts
    return {
        "items": [
            {
                "id": "jollof-chicken",
                "name": "Jollof Rice + Chicken",
                "description": "Smoky Ghanaian jollof with crispy fried chicken.",
                "price": 45,
                "category": "rice",
                "popular": True,
                "spicy": True,
            },
            {
                "id": "fried-rice-chicken",
                "name": "Fried Rice + Chicken",
                "description": "Fluffy fried rice with mixed vegetables and seasoned chicken.",
                "price": 45,
                "category": "rice",
                "popular": True,
            },
            {
                "id": "grilled-chicken",
                "name": "Grilled Chicken (2 pcs)",
                "description": "Marinated in local spices, slow-grilled to perfection.",
                "price": 55,
                "category": "chicken",
                "popular": True,
            },
            {
                "id": "spicy-wings",
                "name": "Spicy Wings (6 pcs)",
                "description": "Fiery wings tossed in our signature pepper sauce.",
                "price": 48,
                "category": "chicken",
                "spicy": True,
            },
            {
                "id": "bbq-chicken-pizza",
                "name": "BBQ Chicken Pizza",
                "description": "Smoky BBQ base, grilled chicken, mozzarella. 10-inch.",
                "price": 85,
                "category": "pizza",
                "popular": True,
            },
            {
                "id": "chips",
                "name": "Chips (Large)",
                "description": "Crispy golden chips with house spice blend.",
                "price": 20,
                "category": "sides",
            },
            {
                "id": "sobolo",
                "name": "Sobolo",
                "description": "Chilled hibiscus drink with ginger. Refreshing and local.",
                "price": 12,
                "category": "drinks",
            },
        ]
    }
