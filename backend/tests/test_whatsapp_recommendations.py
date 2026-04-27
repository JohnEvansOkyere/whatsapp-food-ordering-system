import asyncio

import pytest

from app.services import session_store as store
import app.services.groq_service as groq_service


SAMPLE_MENU = [
    {
        "id": "waakye",
        "name": "Waakye Special",
        "description": "Classic waakye with spaghetti, egg, stew, and your choice of meat.",
        "price": 40,
        "category": "rice",
        "popular": True,
        "spicy": True,
    },
    {
        "id": "jollof-chicken",
        "name": "Jollof Rice + Chicken",
        "description": "Smoky Ghanaian jollof cooked in fresh tomato base, served with crispy fried chicken and coleslaw.",
        "price": 45,
        "category": "rice",
        "popular": True,
        "spicy": True,
    },
    {
        "id": "fried-rice-chicken",
        "name": "Fried Rice + Chicken",
        "description": "Fluffy fried rice with mixed vegetables, egg, and seasoned fried chicken.",
        "price": 45,
        "category": "rice",
        "popular": True,
    },
    {
        "id": "sobolo",
        "name": "Sobolo (Zobo)",
        "description": "Chilled hibiscus drink with ginger and spices. Refreshing and local.",
        "price": 12,
        "category": "drinks",
        "active": True,
    },
    {
        "id": "water",
        "name": "Voltic Water (1.5L)",
        "description": "Ice cold Voltic mineral water.",
        "price": 8,
        "category": "drinks",
        "active": True,
    },
]


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def clear_sessions():
    store._store.clear()
    store._processed_message_ids.clear()


@pytest.fixture(autouse=True)
def stub_dependencies(monkeypatch):
    async def fake_fetch_menu_items():
        return SAMPLE_MENU

    async def fake_get_customer(_sender):
        return None

    async def fake_get_last_order(_sender):
        return None

    async def fake_get_latest_order_status(_sender):
        return None

    async def fake_ai_response(**_kwargs):
        return "AI fallback should not be used in these tests."

    monkeypatch.setattr(groq_service, "fetch_menu_items", fake_fetch_menu_items)
    monkeypatch.setattr(groq_service, "get_customer", fake_get_customer)
    monkeypatch.setattr(groq_service, "get_last_order", fake_get_last_order)
    monkeypatch.setattr(groq_service, "get_latest_order_status", fake_get_latest_order_status)
    monkeypatch.setattr(groq_service, "get_ai_response", fake_ai_response)


def test_breakfast_recommendation_uses_menu_items_and_menu_link():
    sender = "233244123456"

    reply = run(
        groq_service.handle_incoming_message(
            sender,
            "I need something for breakfast, can you recommend something for me?",
        )
    )

    assert "Waakye Special" in reply
    assert "https://your-menu-app.vercel.app" in reply
    assert "Please send the dish and quantity" not in reply
    assert store.get_state(sender) == "taking_order"


def test_hot_weather_recommendation_prefers_cooling_items():
    sender = "233244123457"

    reply = run(
        groq_service.handle_incoming_message(
            sender,
            "I am feeling hot today, what would you recommend?",
        )
    )

    assert "Sobolo (Zobo)" in reply
    assert "Voltic Water" in reply
    assert "https://your-menu-app.vercel.app" in reply


def test_unrelated_question_is_rejected():
    reply = run(
        groq_service.handle_incoming_message(
            "233244123458",
            "Who won the champions league?",
        )
    )

    assert "I can help with our menu" in reply
    assert "https://your-menu-app.vercel.app" in reply
