import asyncio
import copy
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

import app.routers.customer_auth as customer_auth_router
import app.services.customer_auth_service as cas
from app.schemas.customer import CustomerLoginSchema, ResendOtpSchema


# ---------------------------------------------------------------------------
# Fake Supabase
# ---------------------------------------------------------------------------


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, db, table):
        self.db = db
        self.table = table
        self.filters = []
        self.insert_payload = None
        self.update_payload = None
        self._order = None
        self._desc = False

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
        self._order, self._desc = field, desc
        return self

    def limit(self, _n):
        return self

    def _matches(self, row):
        return all(row.get(f) == v for f, v in self.filters)

    def execute(self):
        rows = self.db.setdefault(self.table, [])
        if self.insert_payload is not None:
            row = {"id": f"{self.table}-{len(rows) + 1}", **self.insert_payload}
            rows.append(row)
            return FakeResponse([copy.deepcopy(row)])
        if self.update_payload is not None:
            updated = []
            for row in rows:
                if self._matches(row):
                    row.update(self.update_payload)
                    updated.append(copy.deepcopy(row))
            return FakeResponse(updated)
        found = [copy.deepcopy(r) for r in rows if self._matches(r)]
        if self._order:
            found.sort(key=lambda r: r.get(self._order) or "", reverse=self._desc)
        return FakeResponse(found)


class FakeSupabase:
    def __init__(self):
        self.tables = {"customers": [], "otp_codes": []}

    def table(self, name):
        return FakeQuery(self.tables, name)


@pytest.fixture
def db(monkeypatch):
    fake = FakeSupabase()
    monkeypatch.setattr(cas, "get_supabase", lambda: fake)
    return fake


@pytest.fixture
def sent(monkeypatch):
    outbox = []

    async def fake_send(to, body):
        outbox.append((to, body))
        return True

    monkeypatch.setattr(cas, "send_sms", fake_send)
    return outbox


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------


def test_password_round_trip():
    encoded = cas.hash_password("correct horse battery")
    assert cas.verify_password("correct horse battery", encoded) is True
    assert cas.verify_password("wrong password", encoded) is False


def test_password_hash_is_salted_and_not_reversible():
    a = cas.hash_password("same-password")
    b = cas.hash_password("same-password")
    assert a != b, "each hash must use a fresh salt"
    assert "same-password" not in a


def test_verify_password_handles_missing_or_malformed_hash():
    assert cas.verify_password("x", None) is False
    assert cas.verify_password("x", "") is False
    assert cas.verify_password("x", "not-a-real-hash") is False
    assert cas.verify_password("x", "md5$1$aa$bb") is False


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["kofi", "kofi.mensah", "ama_23", "a-b-c"])
def test_valid_usernames(value):
    assert cas.validate_username(value.upper()) == value


@pytest.mark.parametrize("value", ["ab", "has space", "we!rd", "x" * 31, ""])
def test_invalid_usernames_rejected(value):
    with pytest.raises(HTTPException) as exc:
        cas.validate_username(value)
    assert exc.value.status_code == 422


def test_password_confirmation_must_match():
    with pytest.raises(HTTPException) as exc:
        cas.validate_password("longenough1", "different1")
    assert "do not match" in exc.value.detail


def test_password_minimum_length_enforced():
    with pytest.raises(HTTPException) as exc:
        cas.validate_password("short", "short")
    assert exc.value.status_code == 422


def test_phone_normalised_to_international():
    assert cas.validate_phone("0244123456") == "233244123456"
    with pytest.raises(HTTPException):
        cas.validate_phone("447700900000")


# ---------------------------------------------------------------------------
# Registration and sign-in
# ---------------------------------------------------------------------------


def _register(db, username="kofi", phone="233244123456", password="hunter2hunter"):
    return asyncio.run(
        cas.register_customer(username=username, password=password, phone=phone)
    )


def test_register_stores_hashed_password_and_unverified_phone(db):
    customer = _register(db)
    assert customer["phone_verified"] is False
    assert customer["password_hash"] != "hunter2hunter"
    assert cas.verify_password("hunter2hunter", customer["password_hash"])


def test_duplicate_username_rejected(db):
    _register(db)
    with pytest.raises(HTTPException) as exc:
        _register(db, phone="233201111111")
    assert exc.value.status_code == 409


def test_verified_phone_cannot_be_reused(db):
    customer = _register(db)
    asyncio.run(cas.mark_phone_verified(customer["id"]))
    with pytest.raises(HTTPException) as exc:
        _register(db, username="other")
    assert exc.value.status_code == 409


def test_abandoned_unverified_signup_can_be_reclaimed(db):
    _register(db, username="first")
    # Same number, never verified — a second attempt should take it over.
    reclaimed = _register(db, username="second")
    assert reclaimed["username"] == "second"
    assert len(db.tables["customers"]) == 1


def test_phone_login_unknown_number_directed_to_signup(db, sent):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            customer_auth_router.login(CustomerLoginSchema(phone="0244123456"))
        )
    assert exc.value.status_code == 404
    assert sent == []


def test_phone_login_texts_code_to_registered_number(db, sent):
    customer = _register(db)
    asyncio.run(cas.mark_phone_verified(customer["id"]))

    result = asyncio.run(
        customer_auth_router.login(CustomerLoginSchema(phone="0244123456"))
    )
    assert result.code_sent is True
    to, body = sent[0]
    assert to == "233244123456"
    assert "code" in body.lower()


def test_resend_reaches_verified_accounts_signing_back_in(db, sent):
    customer = _register(db)
    asyncio.run(cas.mark_phone_verified(customer["id"]))

    result = asyncio.run(
        customer_auth_router.resend(ResendOtpSchema(phone="0244123456"))
    )
    assert result == {"code_sent": True}
    assert sent[0][0] == "233244123456"


# ---------------------------------------------------------------------------
# OTP
# ---------------------------------------------------------------------------


def test_otp_is_stored_hashed_and_sent_by_sms(db, sent):
    assert asyncio.run(cas.issue_otp("233244123456")) is True
    record = db.tables["otp_codes"][0]
    assert "code_hash" in record and len(record["code_hash"]) == 64
    to, body = sent[0]
    assert to == "233244123456"
    # The clear-text code is in the SMS but never in the database.
    code = "".join(c for c in body if c.isdigit())[:6]
    assert record["code_hash"] != code


def test_correct_code_verifies_once_then_is_consumed(db, sent, monkeypatch):
    monkeypatch.setattr(cas, "generate_otp", lambda: "424242")

    asyncio.run(cas.issue_otp("233244123456"))

    assert asyncio.run(cas.verify_otp("233244123456", "424242")) is True
    # Replay must fail — the row is consumed.
    with pytest.raises(HTTPException):
        asyncio.run(cas.verify_otp("233244123456", "424242"))


def test_code_is_bound_to_the_phone_that_requested_it(db, sent, monkeypatch):
    monkeypatch.setattr(cas, "generate_otp", lambda: "424242")
    asyncio.run(cas.issue_otp("233244123456"))

    # The same digits must not verify a different number.
    with pytest.raises(HTTPException):
        asyncio.run(cas.verify_otp("233201111111", "424242"))


def test_wrong_code_counts_attempts_and_locks_out(db, sent):
    asyncio.run(cas.issue_otp("233244123456"))
    for _ in range(cas.OTP_MAX_ATTEMPTS):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(cas.verify_otp("233244123456", "000000"))
        assert exc.value.status_code == 400
    with pytest.raises(HTTPException) as exc:
        asyncio.run(cas.verify_otp("233244123456", "000000"))
    assert exc.value.status_code == 429


def test_expired_code_is_rejected(db, sent):
    asyncio.run(cas.issue_otp("233244123456"))
    db.tables["otp_codes"][0]["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(minutes=1)
    ).isoformat()
    with pytest.raises(HTTPException) as exc:
        asyncio.run(cas.verify_otp("233244123456", "123456"))
    assert "expired" in exc.value.detail.lower()


def test_resend_is_rate_limited_by_cooldown(db, sent):
    asyncio.run(cas.issue_otp("233244123456"))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(cas.issue_otp("233244123456"))
    assert exc.value.status_code == 429


def test_verify_without_any_code_is_rejected(db):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(cas.verify_otp("233244123456", "123456"))
    assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# Session tokens
# ---------------------------------------------------------------------------


def test_token_round_trip_carries_identity():
    token, expires_in = cas.create_customer_token(
        {"id": "cust-1", "username": "kofi", "phone": "233244123456"}
    )
    payload = cas.decode_customer_token(token)
    assert payload["sub"] == "cust-1"
    assert payload["phone"] == "233244123456"
    assert expires_in > 0


def test_tampered_token_rejected():
    token, _ = cas.create_customer_token(
        {"id": "cust-1", "username": "kofi", "phone": "233244123456"}
    )
    body, signature = token.split(".", 1)
    with pytest.raises(HTTPException) as exc:
        cas.decode_customer_token(f"{body}x.{signature}")
    assert exc.value.status_code == 401


def test_expired_token_rejected(monkeypatch):
    token, _ = cas.create_customer_token(
        {"id": "cust-1", "username": "kofi", "phone": "233244123456"}
    )
    monkeypatch.setattr(cas.time, "time", lambda: 9_999_999_999)
    with pytest.raises(HTTPException) as exc:
        cas.decode_customer_token(token)
    assert exc.value.status_code == 401
