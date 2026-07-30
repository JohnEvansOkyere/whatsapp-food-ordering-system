import copy
import asyncio
import uuid

import httpx
import pytest

import app.routers.public as public_router
import app.services.customer_service as customer_service
import app.services.notification_service as notification_service
import app.services.order_service as order_service
from app.schemas.branch import PublicBranchSchema


ASHESI_BRANCH_ID = "a5010000-0000-4000-8000-000000000001"
SAMPLE_BRANCH = PublicBranchSchema(
    id=ASHESI_BRANCH_ID,
    name="Ashesi University",
    code="ASHESI",
    slug="ashesi-university",
    address="Ashesi University campus",
    city="Berekuso",
    is_default=True,
    accepting_orders=True,
    delivery_fee=5,
)


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
            "notification_events": [],
            "payments": [],
            "order_feedback": [],
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


class LegacyPhoneLookupQuery(FakeQuery):
    def execute(self):
        if (
            self.table_name == "orders"
            and self.insert_payload is None
            and any(field == "customer_phone_snapshot" for field, _value in self.filters)
        ):
            raise Exception("column orders.customer_phone_snapshot does not exist")
        return super().execute()


class LegacyPhoneLookupSupabase(FakeSupabase):
    def table(self, table_name):
        return LegacyPhoneLookupQuery(self, table_name)


def api_request(app, method, url, **kwargs):
    async def _request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.request(method, url, **kwargs)

    return asyncio.run(_request())


def staff_headers(app, username="owner"):
    response = api_request(
        app,
        "POST",
        "/auth/staff/login",
        json={"username": username, "password": "ChangeMe123!"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def fake_backend(monkeypatch):
    fake_supabase = FakeSupabase()

    async def fake_fetch_menu_items(branch_id=None):
        assert branch_id in {None, ASHESI_BRANCH_ID}
        rows = copy.deepcopy(SAMPLE_MENU)
        rows[0]["option_groups"] = [
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
        ]
        return rows

    async def fake_send_message(_order):
        return True

    async def fake_get_public_branch(reference):
        if reference in {ASHESI_BRANCH_ID, "ashesi-university", "ASHESI"}:
            return SAMPLE_BRANCH.model_copy(deep=True)
        return None

    async def fake_notify_status(_order, *, order_event_id):
        assert order_event_id
        return True

    async def fake_notify_created(_order, *, order_event_id):
        assert order_event_id
        return True

    monkeypatch.setattr(order_service, "get_supabase", lambda: fake_supabase)
    monkeypatch.setattr(customer_service, "get_supabase", lambda: fake_supabase)
    monkeypatch.setattr(order_service, "fetch_menu_items", fake_fetch_menu_items)
    monkeypatch.setattr(order_service, "get_public_branch", fake_get_public_branch)
    monkeypatch.setattr(public_router, "get_public_branch", fake_get_public_branch)
    monkeypatch.setattr(order_service, "send_order_receipt_to_customer", fake_send_message)
    monkeypatch.setattr(order_service, "send_order_notification_to_owner", fake_send_message)
    monkeypatch.setattr(notification_service, "notify_order_status_changed", fake_notify_status)
    monkeypatch.setattr(notification_service, "notify_order_created", fake_notify_created)

    return fake_supabase


def test_public_menu_endpoint_returns_items(app, monkeypatch):
    async def fake_fetch_menu_items(**_kwargs):
        return copy.deepcopy(SAMPLE_MENU)

    monkeypatch.setattr(public_router, "fetch_menu_items", fake_fetch_menu_items)

    response = api_request(app, "GET", "/public/menu")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["items"][0]["id"] == "jollof-chicken"


def test_public_branches_endpoint_returns_the_two_supported_locations(app, monkeypatch):
    branches = [
        SAMPLE_BRANCH,
        SAMPLE_BRANCH.model_copy(
            update={
                "id": "abe10000-0000-4000-8000-000000000002",
                "name": "Abelemkpe",
                "code": "ABELEMKPE",
                "slug": "abelemkpe",
                "address": "Abelemkpe, Accra",
                "city": "Accra",
                "is_default": False,
            }
        ),
    ]

    async def fake_fetch_public_branches():
        return branches

    monkeypatch.setattr(
        public_router,
        "fetch_public_branches",
        fake_fetch_public_branches,
    )

    response = api_request(app, "GET", "/public/branches")

    assert response.status_code == 200
    assert [item["slug"] for item in response.json()["items"]] == [
        "ashesi-university",
        "abelemkpe",
    ]


def test_public_order_requires_a_supported_active_branch(app, fake_backend):
    missing_response = api_request(
        app,
        "POST",
        "/public/orders",
        json={
            "customer_phone": "233244123456",
            "delivery_address": "Berekuso",
            "items": [{"item_id": "sobolo", "quantity": 1}],
            "payment_method": "cash",
        },
    )
    assert missing_response.status_code == 400
    assert "select" in missing_response.json()["detail"].lower()

    unknown_response = api_request(
        app,
        "POST",
        "/public/orders",
        json={
            "branch_id": "unknown-branch",
            "whatsapp_consent": True,
            "customer_phone": "233244123456",
            "delivery_address": "Berekuso",
            "items": [{"item_id": "sobolo", "quantity": 1}],
            "payment_method": "cash",
        },
    )
    assert unknown_response.status_code == 400
    assert "not found" in unknown_response.json()["detail"].lower()


def test_public_analytics_accepts_known_events_and_rejects_unknown_events(
    app,
    fake_backend,
):
    accepted = api_request(
        app,
        "POST",
        "/public/analytics",
        json={
            "event_name": "branch_selected",
            "branch_id": ASHESI_BRANCH_ID,
            "anonymous_session_id": "anonymous-test-session",
            "metadata": {"branch": "ashesi-university"},
        },
    )
    rejected = api_request(
        app,
        "POST",
        "/public/analytics",
        json={"event_name": "arbitrary_database_event"},
    )

    assert accepted.status_code == 202
    assert accepted.json()["accepted"] is True
    assert rejected.status_code == 400


def test_public_order_creation_writes_normalized_records(app, fake_backend):
    response = api_request(
        app,
        "POST",
        "/public/orders",
        json={
            "branch_id": ASHESI_BRANCH_ID,
            "whatsapp_consent": True,
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
    assert body["total_amount"] == 95.0
    assert body["subtotal_amount"] == 90.0
    assert body["delivery_fee"] == 5.0
    assert body["items"][0]["name"] == "Jollof Rice + Chicken"
    assert body["tracking_code"].startswith("TRK-")
    assert body["order_number"].startswith("ORD-")
    assert body["branch_id"] == ASHESI_BRANCH_ID
    assert body["branch_name"] == "Ashesi University"
    assert body["tracking_url"].startswith("http://localhost:3000/track/")
    assert not body["tracking_url"].endswith(body["tracking_code"])
    assert body["whatsapp_receipt_sent"] is True

    assert len(fake_backend.tables["orders"]) == 1
    assert len(fake_backend.tables["order_items"]) == 1
    assert len(fake_backend.tables["order_events"]) == 1
    assert len(fake_backend.tables["customers"]) == 1

    stored_order = fake_backend.tables["orders"][0]
    assert stored_order["status"] == "new"
    assert stored_order["branch_id"] == ASHESI_BRANCH_ID
    assert len(stored_order["public_tracking_token"]) >= 24
    assert stored_order["customer_phone_snapshot"] == "233244123456"
    assert stored_order["items"][0]["total_price"] == 90.0
    assert fake_backend.tables["order_items"][0]["item_name_snapshot"] == "Jollof Rice + Chicken"
    assert fake_backend.tables["order_events"][0]["event_type"] == "order_created"


def test_public_order_idempotency_prevents_double_tap_duplicates(app, fake_backend):
    payload = {
        "branch_id": ASHESI_BRANCH_ID,
        "whatsapp_consent": True,
        "idempotency_key": "checkout-attempt-00000001",
        "customer_phone": "233244123456",
        "customer_name": "Kojo",
        "delivery_address": "Ashesi campus",
        "items": [{"item_id": "jollof-chicken", "quantity": 1}],
        "payment_method": "cash",
    }

    first = api_request(app, "POST", "/public/orders", json=payload)
    second = api_request(app, "POST", "/public/orders", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]
    assert len(fake_backend.tables["orders"]) == 1
    assert len(fake_backend.tables["order_items"]) == 1


def test_product_options_are_validated_and_priced_on_the_backend(app, fake_backend):
    response = api_request(
        app,
        "POST",
        "/public/orders",
        json={
            "branch_id": ASHESI_BRANCH_ID,
            "whatsapp_consent": True,
            "customer_phone": "233244123456",
            "delivery_address": "Ashesi campus",
            "items": [
                {
                    "item_id": "jollof-chicken",
                    "quantity": 1,
                    "unit_price": 1,
                    "selections": [
                        {
                            "group_id": "extras",
                            "option_id": "plantain",
                            "price": 0,
                        }
                    ],
                }
            ],
            "payment_method": "cash",
        },
    )

    assert response.status_code == 201
    item = response.json()["items"][0]
    assert item["unit_price"] == 53
    assert item["selections"][0]["name"] == "Fried plantain"
    assert response.json()["total_amount"] == 58


def test_delivered_customer_can_rate_the_order_from_private_link(app, fake_backend):
    created = api_request(
        app,
        "POST",
        "/public/orders",
        json={
            "branch_id": ASHESI_BRANCH_ID,
            "whatsapp_consent": True,
            "customer_phone": "233244123456",
            "delivery_address": "Ashesi campus",
            "items": [{"item_id": "jollof-chicken", "quantity": 1}],
            "payment_method": "cash",
        },
    )
    token = created.json()["tracking_url"].rsplit("/", 1)[-1]
    fake_backend.tables["orders"][0]["status"] = "delivered"

    response = api_request(
        app,
        "POST",
        f"/public/orders/{token}/feedback",
        json={"rating": 5, "comment": "Hot and fresh"},
    )

    assert response.status_code == 200
    assert response.json()["accepted"] is True
    assert fake_backend.tables["order_feedback"][0]["rating"] == 5


def test_admin_order_flow_validates_transitions_and_tracking(app, fake_backend):
    headers = staff_headers(app)
    create_response = api_request(
        app,
        "POST",
        "/public/orders",
        json={
            "branch_id": ASHESI_BRANCH_ID,
            "whatsapp_consent": True,
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
    tracking_token = created_order["tracking_url"].rsplit("/", 1)[-1]

    list_response = api_request(app, "GET", "/admin/orders", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    detail_response = api_request(
        app,
        "GET",
        f"/admin/orders/{order_id}",
        headers=headers,
    )
    assert detail_response.status_code == 200
    assert "confirmed" in detail_response.json()["allowed_next_statuses"]

    invalid_response = api_request(
        app,
        "PATCH",
        f"/admin/orders/{order_id}/status",
        headers=headers,
        json={"status": "delivered", "actor_label": "unit-test"},
    )
    assert invalid_response.status_code == 400
    assert "Invalid status transition" in invalid_response.json()["detail"]

    confirm_response = api_request(
        app,
        "PATCH",
        f"/admin/orders/{order_id}/status",
        headers=headers,
        json={
            "status": "confirmed",
            "actor_label": "unit-test",
            "eta_minutes": 40,
        },
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "confirmed"
    assert confirm_response.json()["accepted_eta_minutes"] == 40

    cancel_response = api_request(
        app,
        "POST",
        f"/admin/orders/{order_id}/cancel",
        headers=headers,
        json={
            "reason_code": "customer_changed_mind",
            "reason_note": "Customer called back immediately.",
            "actor_label": "unit-test",
        },
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"

    tracking_response = api_request(app, "GET", f"/public/orders/{tracking_token}")
    assert tracking_response.status_code == 200
    tracking_body = tracking_response.json()

    assert tracking_body["status"] == "cancelled"
    assert "customer_phone" not in tracking_body
    assert "delivery_address" not in tracking_body
    assert [event["status"] for event in tracking_body["timeline"]] == [
        "new",
        "confirmed",
        "cancelled",
    ]
    assert fake_backend.tables["order_events"][-1]["reason_code"] == "customer_changed_mind"


def test_admin_routes_require_sign_in(app):
    response = api_request(app, "GET", "/admin/orders")
    assert response.status_code == 401
    assert "sign-in" in response.json()["detail"].lower()


def test_staff_can_record_collected_cash_with_an_audit_payment(app, fake_backend):
    created = api_request(
        app,
        "POST",
        "/public/orders",
        json={
            "branch_id": ASHESI_BRANCH_ID,
            "whatsapp_consent": True,
            "customer_phone": "233244123456",
            "delivery_address": "Ashesi campus",
            "items": [{"item_id": "jollof-chicken", "quantity": 1}],
            "payment_method": "cash",
        },
    )
    headers = staff_headers(app)

    response = api_request(
        app,
        "PATCH",
        f"/admin/orders/{created.json()['id']}/payment",
        headers=headers,
        json={"status": "paid", "provider": "manual"},
    )

    assert response.status_code == 200
    assert response.json()["payment_status"] == "paid"
    assert len(fake_backend.tables["payments"]) == 2
    assert fake_backend.tables["payments"][0]["status"] == "pending"
    assert fake_backend.tables["payments"][1]["method"] == "cash"
    assert fake_backend.tables["order_events"][-1]["event_type"] == "payment_updated"


def test_branch_staff_cannot_open_another_branch_queue(app):
    headers = staff_headers(app, username="ashesi")
    response = api_request(
        app,
        "GET",
        "/admin/orders?branch_id=abe10000-0000-4000-8000-000000000002",
        headers=headers,
    )
    assert response.status_code == 403


def test_kitchen_role_cannot_mark_an_order_delivered(app, fake_backend):
    created = api_request(
        app,
        "POST",
        "/public/orders",
        json={
            "branch_id": ASHESI_BRANCH_ID,
            "whatsapp_consent": True,
            "customer_phone": "233244123456",
            "delivery_address": "Ashesi campus",
            "items": [{"item_id": "jollof-chicken", "quantity": 1}],
            "payment_method": "cash",
        },
    )
    headers = staff_headers(app, username="ashesi-kitchen")

    response = api_request(
        app,
        "PATCH",
        f"/admin/orders/{created.json()['id']}/status",
        headers=headers,
        json={"status": "delivered"},
    )

    assert response.status_code == 403


def test_public_order_creation_falls_back_for_legacy_orders_schema(app, monkeypatch):
    fake_supabase = LegacyCompatSupabase()

    async def fake_fetch_menu_items(branch_id=None):
        assert branch_id in {None, ASHESI_BRANCH_ID}
        return copy.deepcopy(SAMPLE_MENU)

    async def fake_send_message(_order):
        return True

    async def fake_get_public_branch(reference):
        if reference == ASHESI_BRANCH_ID:
            return SAMPLE_BRANCH.model_copy(deep=True)
        return None

    monkeypatch.setattr(order_service, "get_supabase", lambda: fake_supabase)
    monkeypatch.setattr(customer_service, "get_supabase", lambda: fake_supabase)
    monkeypatch.setattr(order_service, "fetch_menu_items", fake_fetch_menu_items)
    monkeypatch.setattr(order_service, "get_public_branch", fake_get_public_branch)
    monkeypatch.setattr(public_router, "get_public_branch", fake_get_public_branch)
    monkeypatch.setattr(order_service, "send_order_receipt_to_customer", fake_send_message)
    monkeypatch.setattr(order_service, "send_order_notification_to_owner", fake_send_message)

    response = api_request(
        app,
        "POST",
        "/public/orders",
        json={
            "branch_id": ASHESI_BRANCH_ID,
            "whatsapp_consent": True,
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


def test_customer_service_falls_back_when_snapshot_phone_column_is_missing(monkeypatch):
    fake_supabase = LegacyPhoneLookupSupabase()
    fake_supabase.tables["orders"].append(
        {
            "id": str(uuid.uuid4()),
            "customer_phone": "233245540271",
            "items": [{"name": "Jollof Rice + Chicken", "quantity": 1}],
            "total_amount": 45,
            "tracking_code": "TRK-DEMO1001",
            "status": "confirmed",
            "created_at": "2026-04-27T12:00:00+00:00",
        }
    )

    monkeypatch.setattr(customer_service, "get_supabase", lambda: fake_supabase)

    last_order = asyncio.run(customer_service.get_last_order("233245540271"))
    latest_status = asyncio.run(customer_service.get_latest_order_status("233245540271"))

    assert last_order is not None
    assert last_order["total_amount"] == 45
    assert latest_status is not None
    assert latest_status["tracking_code"] == "TRK-DEMO1001"
    assert latest_status["status"] == "confirmed"
