from fastapi import APIRouter

from app.services.menu_service import fetch_menu_items

router = APIRouter(prefix="/menu", tags=["menu"])


@router.get("/")
async def get_menu():
    """
    Full menu for the web app and internal order matching.
    Uses Supabase when configured; otherwise static items from menu_service.
    """
    items = await fetch_menu_items()
    return {"items": items}
