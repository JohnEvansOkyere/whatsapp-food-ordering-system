import asyncio
from types import SimpleNamespace

import pytest

import app.services.sms as sms


def _order(**overrides):
    base = dict(
        id="0123456789abcdef",
        order_number="ORD-7F3A21",
        status=SimpleNamespace(value="confirmed"),
        branch_name="Abelemkpe",
        tracking_url="https://veloxa.app/track/abc123token",
        customer_phone="233244123456",
        total_amount=132.0,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("0244123456", "233244123456"),
        ("+233244123456", "233244123456"),
        ("233244123456", "233244123456"),
        ("233 244 123 456", "233244123456"),
        ("00233244123456", "233244123456"),
    ],
)
def test_normalise_ghana_msisdn_accepts_local_and_international(raw, expected):
    assert sms.normalise_ghana_msisdn(raw) == expected


@pytest.mark.parametrize(
    "raw", ["", None, "12345", "0244", "447700900000", "2332441234567890"]
)
def test_normalise_ghana_msisdn_rejects_invalid(raw):
    assert sms.normalise_ghana_msisdn(raw) is None


def test_receipt_sms_contains_reference_total_and_tracking_link():
    body = sms.build_receipt_sms(_order(), "VelOxa Food")
    assert "ORD-7F3A21" in body
    assert "Abelemkpe" in body
    assert "GHS 132.00" in body
    assert "https://veloxa.app/track/abc123token" in body


def test_status_sms_uses_customer_facing_label():
    body = sms.build_status_sms(
        _order(status=SimpleNamespace(value="out_for_delivery")), "VelOxa Food"
    )
    assert "out for delivery" in body
    assert "ORD-7F3A21" in body
    assert "https://veloxa.app/track/abc123token" in body


def test_receipt_sms_stays_within_two_segments():
    body = sms.build_receipt_sms(_order(), "VelOxa Food")
    assert sms.count_segments(body) <= 2


def test_count_segments_boundaries():
    assert sms.count_segments("") == 0
    assert sms.count_segments("a" * 160) == 1
    assert sms.count_segments("a" * 161) == 2
    assert sms.count_segments("a" * 306) == 2
    assert sms.count_segments("a" * 307) == 3


def test_send_sms_is_a_noop_while_disabled(monkeypatch):
    monkeypatch.setattr(
        sms, "get_settings", lambda: SimpleNamespace(sms_enabled=False)
    )
    called = False

    async def fail(*_args, **_kwargs):
        nonlocal called
        called = True
        return True

    monkeypatch.setattr(sms, "_moolre_send_request", fail)
    assert asyncio.run(sms.send_sms("0244123456", "hello")) is False
    assert called is False


def test_send_sms_requires_credentials(monkeypatch):
    monkeypatch.setattr(
        sms,
        "get_settings",
        lambda: SimpleNamespace(sms_enabled=True, moolre_api_key="", moolre_api_user=""),
    )
    assert asyncio.run(sms.send_sms("0244123456", "hello")) is False


def test_send_sms_normalises_recipient_before_dispatch(monkeypatch):
    monkeypatch.setattr(
        sms,
        "get_settings",
        lambda: SimpleNamespace(
            sms_enabled=True, moolre_api_key="k", moolre_api_user="u"
        ),
    )
    seen = {}

    async def capture(to, body):
        seen["to"] = to
        seen["body"] = body
        return True

    monkeypatch.setattr(sms, "_moolre_send_request", capture)
    assert asyncio.run(sms.send_sms("0244123456", "hello")) is True
    assert seen["to"] == "233244123456"


def test_send_sms_rejects_non_ghana_number(monkeypatch):
    monkeypatch.setattr(
        sms,
        "get_settings",
        lambda: SimpleNamespace(
            sms_enabled=True, moolre_api_key="k", moolre_api_user="u"
        ),
    )

    async def fail(*_args, **_kwargs):
        raise AssertionError("should not dispatch an invalid number")

    monkeypatch.setattr(sms, "_moolre_send_request", fail)
    assert asyncio.run(sms.send_sms("447700900000", "hello")) is False


def test_send_sms_swallows_transport_errors(monkeypatch):
    import httpx

    monkeypatch.setattr(
        sms,
        "get_settings",
        lambda: SimpleNamespace(
            sms_enabled=True, moolre_api_key="k", moolre_api_user="u"
        ),
    )

    async def boom(*_args, **_kwargs):
        raise httpx.ConnectError("network down")

    monkeypatch.setattr(sms, "_moolre_send_request", boom)
    # A failed notification must never propagate and roll back a valid order.
    assert asyncio.run(sms.send_sms("0244123456", "hello")) is False


def test_noisy_statuses_do_not_spend_a_segment(monkeypatch):
    sent = []

    async def record(_to, body):
        sent.append(body)
        return True

    monkeypatch.setattr(sms, "send_sms", lambda to, body: record(to, body))
    monkeypatch.setattr(
        sms, "get_settings", lambda: SimpleNamespace(restaurant_name="VelOxa Food")
    )

    for status in ("preparing", "ready"):
        result = asyncio.run(
            sms.send_order_status_sms(_order(status=SimpleNamespace(value=status)))
        )
        assert result is False
    assert sent == []

    asyncio.run(
        sms.send_order_status_sms(
            _order(status=SimpleNamespace(value="out_for_delivery"))
        )
    )
    assert len(sent) == 1
