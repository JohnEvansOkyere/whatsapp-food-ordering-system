import asyncio
import copy
from types import SimpleNamespace

import app.services.notification_service as notification_service


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, database, table):
        self.database = database
        self.table = table
        self.filters = []
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

    def limit(self, _value):
        return self

    def execute(self):
        rows = self.database[self.table]
        if self.insert_payload is not None:
            row = {"id": f"notification-{len(rows) + 1}", **self.insert_payload}
            rows.append(row)
            return FakeResponse([copy.deepcopy(row)])
        if self.update_payload is not None:
            updated = []
            for row in rows:
                if all(row.get(field) == value for field, value in self.filters):
                    row.update(self.update_payload)
                    updated.append(copy.deepcopy(row))
            return FakeResponse(updated)
        return FakeResponse(
            [
                copy.deepcopy(row)
                for row in rows
                if all(row.get(field) == value for field, value in self.filters)
            ]
        )


class FakeSupabase:
    def __init__(self):
        self.tables = {"notification_events": []}

    def table(self, name):
        return FakeQuery(self.tables, name)


def test_status_notifications_retry_and_remain_idempotent(monkeypatch):
    database = FakeSupabase()
    attempts = 0

    async def fake_send(_order):
        nonlocal attempts
        attempts += 1
        return attempts >= 3

    monkeypatch.setattr(notification_service, "get_supabase", lambda: database)
    monkeypatch.setattr(
        notification_service,
        "send_order_status_update_to_customer",
        fake_send,
    )

    order = SimpleNamespace(
        id="order-1",
        tenant_id=None,
        branch_id="branch-1",
        order_number="ORD-1",
        status=SimpleNamespace(value="confirmed"),
        branch_name="Ashesi University",
        tracking_url="https://example.com/track/token",
        customer_phone="233244123456",
    )

    first = asyncio.run(
        notification_service.notify_order_status_changed(
            order,
            order_event_id="event-1",
        )
    )
    second = asyncio.run(
        notification_service.notify_order_status_changed(
            order,
            order_event_id="event-1",
        )
    )

    assert first is True
    assert second is True
    assert attempts == 3
    assert len(database.tables["notification_events"]) == 1
    assert database.tables["notification_events"][0]["status"] == "sent"
    assert database.tables["notification_events"][0]["attempt_count"] == 3
