from fastapi import APIRouter, Query

from app.services.menu_service import fetch_menu_items

router = APIRouter(prefix="/menu", tags=["menu"])


@router.get("/")
async def get_menu(branch_id: str | None = Query(default=None)):
    """
    Full menu for the web app and internal order matching.
    Uses Supabase when configured; otherwise static items from menu_service.
    """
    items = (
        await fetch_menu_items(branch_id=branch_id)
        if branch_id
        else await fetch_menu_items()
    )
    return {"items": items}
