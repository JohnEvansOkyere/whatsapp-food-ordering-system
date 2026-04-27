import asyncio
import copy

import httpx
import pytest

from app.services import session_store as store
import app.services.groq_service as groq_service
import app.services.menu_service as menu_service
import app.services.order_parser as order_parser


MENU_ROWS = [
    {
        "id": "waakye",
        "name": "Waakye Special",
        "description": "Classic waakye with spaghetti, egg, stew, and your choice of meat.",
        "price": 40,
        "category": "rice",
        "popular": True,
        "spicy": True,
        "active": True,
        "sold_out": True,
    },
    {
        "id": "fried-rice-chicken",
        "name": "Fried Rice + Chicken",
        "description": "Fluffy fried rice with mixed vegetables, egg, and seasoned fried chicken.",
        "price": 45,
        "category": "rice",
        "popular": True,
        "active": True,
        "sold_out": False,
    },
    {
        "id": "jollof-chicken",
        "name": "Jollof Rice + Chicken",
        "description": "Smoky Ghanaian jollof cooked in fresh tomato base, served with crispy fried chicken and coleslaw.",
        "price": 45,
        "category": "rice",
        "popular": True,
        "active": True,
        "sold_out": False,
    },
]


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, supabase, table_name):
        self.supabase = supabase
        self.table_name = table_name
        self.filters = []
        self.update_payload = None

    def select(self, _fields="*"):
        return self

    def update(self, payload):
        self.update_payload = payload
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def execute(self):
        table = self.supabase.tables[self.table_name]

        if self.update_payload is not None:
            updated = []
            for row in table:
                if all(row.get(field) == value for field, value in self.filters):
                    row.update(copy.deepcopy(self.update_payload))
                    updated.append(copy.deepcopy(row))
            return FakeResponse(updated)

        rows = [
            copy.deepcopy(row)
            for row in table
            if all(row.get(field) == value for field, value in self.filters)
        ]
        return FakeResponse(rows)


class FakeSupabase:
    def __init__(self):
        self.tables = {"menu_items": copy.deepcopy(MENU_ROWS)}

    def table(self, table_name):
        return FakeQuery(self, table_name)


def api_request(app, method, url, **kwargs):
    async def _request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.request(method, url, **kwargs)

    return asyncio.run(_request())


@pytest.fixture(autouse=True)
def clear_sessions():
    store._store.clear()
    store._processed_message_ids.clear()


def test_sold_out_item_is_removed_from_public_menu_and_can_be_toggled(app, monkeypatch):
    fake_supabase = FakeSupabase()
    monkeypatch.setattr(menu_service, "get_supabase", lambda: fake_supabase)

    public_menu = api_request(app, "GET", "/public/menu")
    assert public_menu.status_code == 200
    public_ids = {item["id"] for item in public_menu.json()["items"]}
    assert "waakye" not in public_ids
    assert "fried-rice-chicken" in public_ids

    admin_menu = api_request(app, "GET", "/admin/menu")
    assert admin_menu.status_code == 200
    admin_items = {item["id"]: item for item in admin_menu.json()["items"]}
    assert admin_items["waakye"]["sold_out"] is True

    toggle = api_request(
        app,
        "PATCH",
        "/admin/menu/waakye",
        json={"sold_out": False},
    )
    assert toggle.status_code == 200
    assert toggle.json()["sold_out"] is False

    public_menu_after = api_request(app, "GET", "/public/menu")
    assert public_menu_after.status_code == 200
    public_ids_after = {item["id"] for item in public_menu_after.json()["items"]}
    assert "waakye" in public_ids_after


def test_whatsapp_agent_reports_sold_out_and_offers_alternatives(monkeypatch):
    async def fake_fetch_menu_items(*, include_inactive=False, include_sold_out=False):
        rows = copy.deepcopy(MENU_ROWS)
        filtered = []
        for row in rows:
            if not include_inactive and not row.get("active", True):
                continue
            if not include_sold_out and row.get("sold_out", False):
                continue
            filtered.append(row)
        return filtered

    async def fake_get_customer(_sender):
        return None

    async def fake_get_last_order(_sender):
        return None

    async def fake_get_latest_order_status(_sender):
        return None

    async def fake_ai_response(**_kwargs):
        return "[]"

    monkeypatch.setattr(groq_service, "get_customer", fake_get_customer)
    monkeypatch.setattr(groq_service, "get_last_order", fake_get_last_order)
    monkeypatch.setattr(groq_service, "get_latest_order_status", fake_get_latest_order_status)
    monkeypatch.setattr(groq_service, "fetch_menu_items", fake_fetch_menu_items)
    monkeypatch.setattr(order_parser, "fetch_menu_items", fake_fetch_menu_items)
    monkeypatch.setattr(order_parser, "get_ai_response", fake_ai_response)

    reply = asyncio.run(
        groq_service.handle_incoming_message(
            "233244123459",
            "1 waakye please",
        )
    )

    assert "sold out right now" in reply
    assert "Fried Rice + Chicken" in reply
