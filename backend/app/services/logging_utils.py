import logging
import re

# Credentials that ride in URLs. Arkesel V1 authenticates with an `api_key`
# query parameter, so any logger that prints a request URL — including httpx's
# own INFO-level request log — would otherwise write the key out in plaintext.
_CREDENTIAL_IN_URL = re.compile(r"\b(api[_-]?key)=[^&\s\"'>]+", re.IGNORECASE)


def mask_phone(value: str | None) -> str:
    digits = "".join(character for character in str(value or "") if character.isdigit())
    return f"***{digits[-4:]}" if digits else "***"


def redact_credentials(text: str) -> str:
    """Replace credential query parameters with `***`."""
    return _CREDENTIAL_IN_URL.sub(r"\1=***", text)


class CredentialRedactingFilter(logging.Filter):
    """Strip credentials from every log record, whoever emitted it.

    Installed on the root handler rather than on our own loggers, because the
    leak we care about comes from third-party libraries logging request URLs.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # Render args now so the redaction also covers interpolated values.
        if record.args:
            record.msg = record.getMessage()
            record.args = ()
        if isinstance(record.msg, str):
            record.msg = redact_credentials(record.msg)
        return True


def install_credential_redaction() -> None:
    """Attach the redacting filter to every root handler."""
    log_filter = CredentialRedactingFilter()
    for handler in logging.getLogger().handlers:
        handler.addFilter(log_filter)
