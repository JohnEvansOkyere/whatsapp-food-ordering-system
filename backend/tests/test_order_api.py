import copy
import asyncio
import uuid

import httpx
import pytest

import app.routers.public as public_router
import app.services.customer_service as customer_service
import app.services.order_service as order_service


SAMPLE_MENU = [
    {
        "id": "jollof-chicken",
        "name": "Jollof Rice + Chicken",
        "description": "Signature jollof with fried chicken.",
        "price": 45,
        "category": "rice",
        "active": True,
    },
    {
        "id": "sobolo",
        "name": "Sobolo (Zobo)",
        "description": "Hibiscus drink.",
        "price": 12,
        "category": "drinks",
        "active": True,
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
        self.sort_field = None
        self.sort_desc = False
        self.limit_value = None
        self.insert_payload = None
        self.update_payload = None

    def select(self, _fields="*"):
        return self

    def insert(self, payload):
        self.insert_payload = payload
        return self

    def update(self, payload):
        self.update_payload = payload
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def order(self, field, desc=False):
        self.sort_field = field
        self.sort_desc = desc
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def execute(self):
        table = self.supabase.tables[self.table_name]

        if self.insert_payload is not None:
            payloads = self.insert_payload if isinstance(self.insert_payload, list) else [self.insert_payload]
            inserted = []
            for payload in payloads:
                row = copy.deepcopy(payload)
                row.setdefault("id", str(uuid.uuid4()))
                table.append(row)
                inserted.append(copy.deepcopy(row))
            return FakeResponse(inserted)

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
        if self.sort_field is not None:
            rows.sort(key=lambda row: row.get(self.sort_field) or "", reverse=self.sort_desc)
        if self.limit_value is not None:
            rows = rows[: self.limit_value]
        return FakeResponse(rows)


class FakeSupabase:
    def __init__(self):
        self.tables = {
            "orders": [],
            "order_items": [],
            "order_events": [],
            "customers": [],
            "menu_items": copy.deepcopy(SAMPLE_MENU),
        }

    def table(self, table_name):
        return FakeQuery(self, table_name)


class LegacyCompatQuery(FakeQuery):
    def execute(self):
        if (
            self.table_name == "orders"
            and self.insert_payload is not None
            and isinstance(self.insert_payload, dict)
            and "channel" in self.insert_payload
        ):
            raise Exception("Could not find the 'channel' column of 'orders' in the schema cache")
        return super().execute()


class LegacyCompatSupabase(FakeSupabase):
    def table(self, table_name):
        return LegacyCompatQuery(self, table_name)


def api_request(app, method, url, **kwargs):
    async def _request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.request(method, url, **kwargs)

    return asyncio.run(_request())


@pytest.fixture
def fake_backend(monkeypatch):
    fake_supabase = FakeSupabase()

    async def fake_fetch_menu_items():
        return copy.deepcopy(SAMPLE_MENU)

    async def fake_send_message(_order):
        return True

    monkeypatch.setattr(order_service, "get_supabase", lambda: fake_supabase)
    monkeypatch.setattr(customer_service, "get_supabase", lambda: fake_supabase)
    monkeypatch.setattr(order_service, "fetch_menu_items", fake_fetch_menu_items)
    monkeypatch.setattr(order_service, "send_order_receipt_to_customer", fake_send_message)
    monkeypatch.setattr(order_service, "send_order_notification_to_owner", fake_send_message)

    return fake_supabase


def test_public_menu_endpoint_returns_items(app, monkeypatch):
    async def fake_fetch_menu_items():
        return copy.deepcopy(SAMPLE_MENU)

    monkeypatch.setattr(public_router, "fetch_menu_items", fake_fetch_menu_items)

    response = api_request(app, "GET", "/public/menu")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["items"][0]["id"] == "jollof-chicken"


def test_public_order_creation_writes_normalized_records(app, fake_backend):
    response = api_request(
        app,
        "POST",
        "/public/orders",
        json={
            "customer_phone": "233244123456",
            "customer_name": "Kojo",
            "delivery_address": "House 5, Osu, Accra",
            "items": [
                {
                    "item_id": "jollof-chicken",
                    "name": "Incorrect Client Name",
                    "quantity": 2,
                    "unit_price": 1,
                    "total_price": 2,
                }
            ],
            "total_amount": 2,
            "payment_method": "momo",
        },
    )

    assert response.status_code == 201
    body = response.json()

    assert body["status"] == "new"
    assert body["total_amount"] == 90.0
    assert body["subtotal_amount"] == 90.0
    assert body["items"][0]["name"] == "Jollof Rice + Chicken"
    assert body["tracking_code"].startswith("TRK-")
    assert body["order_number"].startswith("ORD-")

    assert len(fake_backend.tables["orders"]) == 1
    assert len(fake_backend.tables["order_items"]) == 1
    assert len(fake_backend.tables["order_events"]) == 1
    assert len(fake_backend.tables["customers"]) == 1

    stored_order = fake_backend.tables["orders"][0]
    assert stored_order["status"] == "new"
    assert stored_order["customer_phone_snapshot"] == "233244123456"
    assert stored_order["items"][0]["total_price"] == 90.0
    assert fake_backend.tables["order_items"][0]["item_name_snapshot"] == "Jollof Rice + Chicken"
    assert fake_backend.tables["order_events"][0]["event_type"] == "order_created"


def test_admin_order_flow_validates_transitions_and_tracking(app, fake_backend):
    create_response = api_request(
        app,
        "POST",
        "/public/orders",
        json={
            "customer_phone": "233244123456",
            "customer_name": "Ama",
            "delivery_address": "Dansoman, Accra",
            "items": [{"item_id": "sobolo", "quantity": 1}],
            "payment_method": "cash",
        },
    )
    assert create_response.status_code == 201

    created_order = create_response.json()
    order_id = created_order["id"]
    tracking_code = created_order["tracking_code"]

    list_response = api_request(app, "GET", "/admin/orders")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    detail_response = api_request(app, "GET", f"/admin/orders/{order_id}")
    assert detail_response.status_code == 200
    assert "confirmed" in detail_response.json()["allowed_next_statuses"]

    invalid_response = api_request(
        app,
        "PATCH",
        f"/admin/orders/{order_id}/status",
        json={"status": "delivered", "actor_label": "unit-test"},
    )
    assert invalid_response.status_code == 400
    assert "Invalid status transition" in invalid_response.json()["detail"]

    confirm_response = api_request(
        app,
        "PATCH",
        f"/admin/orders/{order_id}/status",
        json={"status": "confirmed", "actor_label": "unit-test"},
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "confirmed"

    cancel_response = api_request(
        app,
        "POST",
        f"/admin/orders/{order_id}/cancel",
        json={
            "reason_code": "customer_changed_mind",
            "reason_note": "Customer called back immediately.",
            "actor_label": "unit-test",
        },
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"

    tracking_response = api_request(app, "GET", f"/public/orders/{tracking_code}")
    assert tracking_response.status_code == 200
    tracking_body = tracking_response.json()

    assert tracking_body["status"] == "cancelled"
    assert [event["status"] for event in tracking_body["timeline"]] == [
        "new",
        "confirmed",
        "cancelled",
    ]
    assert fake_backend.tables["order_events"][-1]["reason_code"] == "customer_changed_mind"


def test_public_order_creation_falls_back_for_legacy_orders_schema(app, monkeypatch):
    fake_supabase = LegacyCompatSupabase()

    async def fake_fetch_menu_items():
        return copy.deepcopy(SAMPLE_MENU)

    async def fake_send_message(_order):
        return True

    monkeypatch.setattr(order_service, "get_supabase", lambda: fake_supabase)
    monkeypatch.setattr(customer_service, "get_supabase", lambda: fake_supabase)
    monkeypatch.setattr(order_service, "fetch_menu_items", fake_fetch_menu_items)
    monkeypatch.setattr(order_service, "send_order_receipt_to_customer", fake_send_message)
    monkeypatch.setattr(order_service, "send_order_notification_to_owner", fake_send_message)

    response = api_request(
        app,
        "POST",
        "/public/orders",
        json={
            "customer_phone": "233500000111",
            "customer_name": "Legacy Customer",
            "delivery_address": "Tema Community 9",
            "items": [{"item_id": "sobolo", "quantity": 2}],
            "payment_method": "cash",
        },
    )

    assert response.status_code == 201
    body = response.json()

    assert body["status"] == "new"
    assert body["channel"] == "web"
    assert body["tracking_code"] is None
    assert body["order_number"] is None
    assert len(fake_supabase.tables["orders"]) == 1
    assert fake_supabase.tables["orders"][0]["status"] == "pending"
    assert fake_supabase.tables["orders"][0]["items"][0]["name"] == "Sobolo (Zobo)"
    assert fake_supabase.tables["order_items"] == []
    assert fake_supabase.tables["order_events"] == []
