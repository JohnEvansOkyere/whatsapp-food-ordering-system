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
        customer_name="Kofi Mensah",
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


def test_receipt_sms_thanks_the_customer_by_first_name():
    body = sms.build_receipt_sms(_order(), "HallMark Cafe")
    assert body.startswith("Hi Kofi! Thank you,")
    assert "HallMark Cafe is happy to see you" in body
    # First name only — the surname buys no warmth and costs characters.
    assert "Mensah" not in body


def test_receipt_sms_contains_reference_total_and_tracking_link():
    body = sms.build_receipt_sms(_order(), "HallMark Cafe")
    assert "ORD-7F3A21" in body
    assert "GHS 132.00" in body
    assert "https://veloxa.app/track/abc123token" in body


def test_receipt_sms_still_thanks_a_customer_with_no_name():
    body = sms.build_receipt_sms(_order(customer_name=None), "HallMark Cafe")
    assert body.startswith("Thank you!")
    assert "https://veloxa.app/track/abc123token" in body


def test_long_name_is_dropped_rather_than_spending_a_second_segment():
    order = _order(
        customer_name="Nanaadwoabaakotwewaa Osei-Bonsu",
        # A real token is secrets.token_urlsafe(24) — 32 chars, not the short
        # placeholder the other tests use.
        tracking_url="https://veloxa.app/track/" + "a" * 32,
    )
    body = sms.build_receipt_sms(order, "HallMark Cafe")
    assert sms.count_segments(body) == 1
    assert "Nanaadwoabaakotwewaa" not in body
    # The thanks survives even when the name cannot.
    assert body.startswith("Thank you!")


def test_status_sms_uses_customer_facing_label():
    body = sms.build_status_sms(
        _order(status=SimpleNamespace(value="out_for_delivery")), "HallMark Cafe"
    )
    assert "out for delivery" in body
    assert "ORD-7F3A21" in body
    assert "https://veloxa.app/track/abc123token" in body


def test_receipt_sms_costs_a_single_segment():
    """Every extra segment is another billed unit on a small prepaid balance."""
    body = sms.build_receipt_sms(_order(), "HallMark Cafe")
    assert sms.count_segments(body) == 1


def test_count_segments_boundaries():
    assert sms.count_segments("") == 0
    assert sms.count_segments("a" * 160) == 1
    assert sms.count_segments("a" * 161) == 2
    assert sms.count_segments("a" * 306) == 2
    assert sms.count_segments("a" * 307) == 3


def test_count_segments_uses_ucs2_limits_for_non_gsm7_text():
    """One non-GSM-7 character halves the segment size for the whole message."""
    assert sms.is_gsm7("Kofi") is True
    assert sms.is_gsm7("Ɛlorm") is False
    # Comfortably one GSM-7 segment, but three under UCS-2.
    plain = "a" * 150
    assert sms.count_segments(plain) == 1
    assert sms.count_segments(plain + "Ɛ") == 3


def test_count_segments_charges_two_septets_for_extended_characters():
    # '€' is in the GSM-7 extension table and costs two septets, so 80 of them
    # fill a 160-character segment exactly.
    assert sms.count_segments("€" * 80) == 1
    assert sms.count_segments("€" * 81) == 2


def test_non_gsm7_name_is_dropped_rather_than_forcing_ucs2():
    order = _order(
        customer_name="Ɛlorm Mensah",
        tracking_url="https://veloxa.app/track/" + "a" * 32,
    )
    body = sms.build_receipt_sms(order, "HallMark Cafe")
    assert sms.is_gsm7(body) is True
    assert sms.count_segments(body) == 1
    assert "Ɛlorm" not in body


def test_accented_name_within_gsm7_is_kept():
    # 'é' is in the GSM-7 basic table, so there is no reason to drop it.
    body = sms.build_receipt_sms(_order(customer_name="José"), "HallMark Cafe")
    assert "José" in body
    assert sms.count_segments(body) == 1


def test_send_sms_is_a_noop_while_disabled(monkeypatch):
    monkeypatch.setattr(
        sms, "get_settings", lambda: SimpleNamespace(sms_enabled=False)
    )
    called = False

    async def fail(*_args, **_kwargs):
        nonlocal called
        called = True
        return True

    monkeypatch.setattr(sms, "_arkesel_send_request", fail)
    assert asyncio.run(sms.send_sms("0244123456", "hello")) is False
    assert called is False


def test_send_sms_requires_credentials(monkeypatch):
    monkeypatch.setattr(
        sms,
        "get_settings",
        lambda: SimpleNamespace(
            sms_enabled=True,
            sms_providers_list=["arkesel", "moolre"],
            arkesel_api_key="",
            arkesel_sender_id="",
            moolre_vas_key="",
            moolre_sender_id="",
        ),
    )
    assert asyncio.run(sms.send_sms("0244123456", "hello")) is False


def test_send_sms_normalises_recipient_before_dispatch(monkeypatch):
    monkeypatch.setattr(
        sms,
        "get_settings",
        lambda: SimpleNamespace(
            sms_enabled=True,
            sms_providers_list=["arkesel"],
            arkesel_api_key="k",
            arkesel_sender_id="Veloxa",
        ),
    )
    seen = {}

    async def capture(to, body):
        seen["to"] = to
        seen["body"] = body
        return True

    monkeypatch.setattr(sms, "_arkesel_send_request", capture)
    assert asyncio.run(sms.send_sms("0244123456", "hello")) is True
    assert seen["to"] == "233244123456"


def test_send_sms_rejects_non_ghana_number(monkeypatch):
    monkeypatch.setattr(
        sms,
        "get_settings",
        lambda: SimpleNamespace(
            sms_enabled=True,
            sms_providers_list=["arkesel"],
            arkesel_api_key="k",
            arkesel_sender_id="Veloxa",
        ),
    )

    async def fail(*_args, **_kwargs):
        raise AssertionError("should not dispatch an invalid number")

    monkeypatch.setattr(sms, "_arkesel_send_request", fail)
    assert asyncio.run(sms.send_sms("447700900000", "hello")) is False


def test_send_sms_swallows_transport_errors(monkeypatch):
    import httpx

    monkeypatch.setattr(
        sms,
        "get_settings",
        lambda: SimpleNamespace(
            sms_enabled=True,
            sms_providers_list=["arkesel"],
            arkesel_api_key="k",
            arkesel_sender_id="Veloxa",
        ),
    )

    async def boom(*_args, **_kwargs):
        raise httpx.ConnectError("network down")

    monkeypatch.setattr(sms, "_arkesel_send_request", boom)
    # A failed notification must never propagate and roll back a valid order.
    assert asyncio.run(sms.send_sms("0244123456", "hello")) is False


def _both_providers(**overrides):
    base = dict(
        sms_enabled=True,
        sms_providers_list=["arkesel", "moolre"],
        arkesel_api_key="k",
        arkesel_sender_id="Veloxa",
        moolre_vas_key="vas",
        moolre_sender_id="Veloxa",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def test_send_sms_falls_over_to_the_next_provider(monkeypatch):
    monkeypatch.setattr(sms, "get_settings", _both_providers)
    tried = []

    async def arkesel_fails(_to, _body):
        tried.append("arkesel")
        return False

    async def moolre_succeeds(_to, _body):
        tried.append("moolre")
        return True

    monkeypatch.setattr(sms, "_arkesel_send_request", arkesel_fails)
    monkeypatch.setattr(sms, "_moolre_send_request", moolre_succeeds)
    assert asyncio.run(sms.send_sms("0244123456", "hello")) is True
    assert tried == ["arkesel", "moolre"]


def test_failover_also_covers_transport_errors(monkeypatch):
    import httpx

    monkeypatch.setattr(sms, "get_settings", _both_providers)

    async def arkesel_boom(_to, _body):
        raise httpx.ConnectError("network down")

    async def moolre_succeeds(_to, _body):
        return True

    monkeypatch.setattr(sms, "_arkesel_send_request", arkesel_boom)
    monkeypatch.setattr(sms, "_moolre_send_request", moolre_succeeds)
    assert asyncio.run(sms.send_sms("0244123456", "hello")) is True


def test_second_provider_is_skipped_when_unconfigured(monkeypatch):
    monkeypatch.setattr(
        sms, "get_settings", lambda: _both_providers(moolre_vas_key="")
    )

    async def arkesel_succeeds(_to, _body):
        return True

    async def moolre_must_not_run(_to, _body):
        raise AssertionError("must not call a provider with no credentials")

    monkeypatch.setattr(sms, "_arkesel_send_request", arkesel_succeeds)
    monkeypatch.setattr(sms, "_moolre_send_request", moolre_must_not_run)
    assert asyncio.run(sms.send_sms("0244123456", "hello")) is True


def test_single_provider_does_not_claim_a_fallback(monkeypatch, caplog):
    monkeypatch.setattr(
        sms, "get_settings", lambda: _both_providers(sms_providers_list=["moolre"])
    )

    async def fails(_to, _body):
        return False

    monkeypatch.setattr(sms, "_moolre_send_request", fails)
    with caplog.at_level("WARNING"):
        assert asyncio.run(sms.send_sms("0244123456", "hello")) is False
    assert "trying the next" not in caplog.text
    assert "no fallback is left" in caplog.text


def test_send_sms_is_false_when_every_provider_fails(monkeypatch):
    monkeypatch.setattr(sms, "get_settings", _both_providers)

    async def fails(_to, _body):
        return False

    monkeypatch.setattr(sms, "_arkesel_send_request", fails)
    monkeypatch.setattr(sms, "_moolre_send_request", fails)
    assert asyncio.run(sms.send_sms("0244123456", "hello")) is False


class _FakeResponse:
    def __init__(self, payload, status_code=200, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload

    def raise_for_status(self):
        return None


def _stub_arkesel_client(monkeypatch, response, calls):
    class _FakeClient:
        def __init__(self, *_args, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc):
            return False

        async def get(self, url, **kwargs):
            calls.append({"url": url, **kwargs})
            return response

    monkeypatch.setattr(sms.httpx, "AsyncClient", _FakeClient)
    monkeypatch.setattr(
        sms,
        "get_settings",
        lambda: SimpleNamespace(
            sms_enabled=True,
            arkesel_api_url="https://sms.arkesel.com/sms/api",
            arkesel_api_key="test-key",
            arkesel_sender_id="Veloxa",
        ),
    )


def test_arkesel_request_uses_v1_query_params(monkeypatch):
    calls = []
    _stub_arkesel_client(monkeypatch, _FakeResponse({"code": "ok"}), calls)

    assert asyncio.run(sms._arkesel_send_request("233244123456", "hello")) is True

    assert calls[0]["url"] == "https://sms.arkesel.com/sms/api"
    assert calls[0]["params"] == {
        "action": "send-sms",
        "api_key": "test-key",
        "to": "233244123456",
        "from": "Veloxa",
        "sms": "hello",
    }


def test_arkesel_error_code_is_not_treated_as_success(monkeypatch):
    calls = []
    # 105 = insufficient balance, returned with a 200.
    _stub_arkesel_client(monkeypatch, _FakeResponse({"code": "105"}), calls)

    assert asyncio.run(sms._arkesel_send_request("233244123456", "hello")) is False


def test_arkesel_plain_text_error_body_is_parsed(monkeypatch):
    calls = []
    _stub_arkesel_client(monkeypatch, _FakeResponse(None, text="102"), calls)

    assert asyncio.run(sms._arkesel_send_request("233244123456", "hello")) is False


def _stub_moolre_client(monkeypatch, response, calls):
    class _FakeClient:
        def __init__(self, *_args, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc):
            return False

        async def post(self, url, **kwargs):
            calls.append({"url": url, **kwargs})
            return response

    monkeypatch.setattr(sms.httpx, "AsyncClient", _FakeClient)
    monkeypatch.setattr(
        sms,
        "get_settings",
        lambda: SimpleNamespace(
            sms_enabled=True,
            moolre_api_url="https://api.moolre.com/open/sms/send",
            moolre_vas_key="vas-key",
            moolre_sender_id="Veloxa",
        ),
    )


def test_moolre_request_uses_vaskey_header_and_messages_array(monkeypatch):
    calls = []
    _stub_moolre_client(monkeypatch, _FakeResponse({"status": 1, "code": "SMS01"}), calls)

    assert asyncio.run(sms._moolre_send_request("233244123456", "hello")) is True

    call = calls[0]
    assert call["url"] == "https://api.moolre.com/open/sms/send"
    assert call["headers"] == {"X-API-VASKEY": "vas-key"}
    assert call["json"]["type"] == 1
    assert call["json"]["senderid"] == "Veloxa"
    message = call["json"]["messages"][0]
    assert message["recipient"] == "233244123456"
    assert message["message"] == "hello"
    assert message["ref"].startswith("veloxa-")


def test_moolre_non_success_status_is_a_failure(monkeypatch):
    calls = []
    _stub_moolre_client(
        monkeypatch,
        _FakeResponse({"status": 0, "code": "AIN01", "message": "Authentication Error"}),
        calls,
    )

    assert asyncio.run(sms._moolre_send_request("233244123456", "hello")) is False


def test_api_key_never_reaches_the_logs(monkeypatch):
    monkeypatch.setattr(
        sms,
        "get_settings",
        lambda: SimpleNamespace(arkesel_api_key="test-key"),
    )
    leaky = "GET https://sms.arkesel.com/sms/api?action=send-sms&api_key=test-key&to=233"
    redacted = sms._redact(leaky)
    assert "test-key" not in redacted
    assert "api_key=***" in redacted


def test_noisy_statuses_do_not_spend_a_segment(monkeypatch):
    sent = []

    async def record(_to, body):
        sent.append(body)
        return True

    monkeypatch.setattr(sms, "send_sms", lambda to, body: record(to, body))
    monkeypatch.setattr(
        sms, "get_settings", lambda: SimpleNamespace(restaurant_name="HallMark Cafe")
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
