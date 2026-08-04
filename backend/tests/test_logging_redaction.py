import logging

from app.services.logging_utils import (
    CredentialRedactingFilter,
    mask_phone,
    redact_credentials,
)

# The exact shape httpx logs at INFO for an Arkesel V1 send.
HTTPX_LINE = (
    "HTTP Request: GET https://sms.arkesel.com/sms/api?action=send-sms"
    "&api_key=ZVBpUVV2RkNUb0NUcGRNdFpuaXY&to=233245540271&from=Veloxa "
    '"HTTP/1.1 422 Unprocessable Entity"'
)


def _record(msg, args=()):
    return logging.LogRecord(
        name="httpx",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=args,
        exc_info=None,
    )


def test_redacts_api_key_from_a_url():
    redacted = redact_credentials(HTTPX_LINE)
    assert "ZVBpUVV2RkNUb0NUcGRNdFpuaXY" not in redacted
    assert "api_key=***" in redacted
    # Everything else stays readable for debugging.
    assert "422 Unprocessable Entity" in redacted
    assert "from=Veloxa" in redacted


def test_redacts_hyphenated_and_uppercase_variants():
    for raw in ("api-key=secret123", "API_KEY=secret123", "apikey=secret123"):
        assert "secret123" not in redact_credentials(raw)


def test_filter_redacts_third_party_records():
    record = _record(HTTPX_LINE)
    assert CredentialRedactingFilter().filter(record) is True
    assert "ZVBpUVV2RkNUb0NUcGRNdFpuaXY" not in record.getMessage()


def test_filter_redacts_values_passed_as_args():
    record = _record("calling %s", ("https://x/api?api_key=secret123",))
    CredentialRedactingFilter().filter(record)
    assert "secret123" not in record.getMessage()


def test_filter_leaves_ordinary_records_alone():
    record = _record("order %s confirmed", ("ORD-7F3A21",))
    CredentialRedactingFilter().filter(record)
    assert record.getMessage() == "order ORD-7F3A21 confirmed"


def test_mask_phone_keeps_only_the_last_four_digits():
    assert mask_phone("233245540271") == "***0271"
    assert mask_phone(None) == "***"
