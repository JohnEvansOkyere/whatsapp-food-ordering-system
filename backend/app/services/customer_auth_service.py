"""
Customer account authentication.

Customers register with a username, password and Ghana phone number, then
verify the phone by one-time passcode. Sign-in also starts from the phone
number and is completed with a texted passcode. The verified number is the
authoritative destination for order SMS, so nothing may be sent to an
unverified number.

Password hashing uses PBKDF2-HMAC-SHA256 from the standard library — no extra
dependency, and the iteration count is stored alongside each hash so it can be
raised later without invalidating existing passwords.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
import secrets
import time
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.database import get_supabase
from app.services.sms import normalise_ghana_msisdn, send_sms
from app.services.logging_utils import mask_phone

logger = logging.getLogger(__name__)

customer_security = HTTPBearer(auto_error=False)

PBKDF2_ITERATIONS = 240_000
OTP_LENGTH = 6
OTP_TTL_SECONDS = 10 * 60
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN_SECONDS = 60

USERNAME_PATTERN = re.compile(r"^[a-z0-9._-]{3,30}$")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${derived.hex()}"


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algorithm, iterations, salt_hex, expected_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        )
        return hmac.compare_digest(derived.hex(), expected_hex)
    except (ValueError, TypeError):
        return False


def validate_username(username: str) -> str:
    candidate = (username or "").strip().lower()
    if not USERNAME_PATTERN.match(candidate):
        raise HTTPException(
            status_code=422,
            detail=(
                "Username must be 3-30 characters using letters, numbers, "
                "dots, underscores or hyphens"
            ),
        )
    return candidate


def validate_password(password: str, confirmation: str) -> str:
    if password != confirmation:
        raise HTTPException(status_code=422, detail="Passwords do not match")
    if len(password or "") < 8:
        raise HTTPException(
            status_code=422, detail="Password must be at least 8 characters"
        )
    return password


def validate_phone(phone: str) -> str:
    normalised = normalise_ghana_msisdn(phone)
    if not normalised:
        raise HTTPException(
            status_code=422,
            detail="Enter a valid Ghana phone number (e.g. 0244123456)",
        )
    return normalised


# ---------------------------------------------------------------------------
# Session tokens
# ---------------------------------------------------------------------------


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def _sign(encoded: str) -> bytes:
    settings = get_settings()
    return hmac.new(
        settings.customer_auth_secret.encode("utf-8"),
        encoded.encode("ascii"),
        hashlib.sha256,
    ).digest()


def create_customer_token(customer: dict) -> tuple[str, int]:
    settings = get_settings()
    expires_in = settings.customer_token_ttl_minutes * 60
    payload = {
        "sub": str(customer["id"]),
        "username": customer.get("username"),
        "phone": customer.get("phone"),
        "exp": int(time.time()) + expires_in,
        "iat": int(time.time()),
    }
    encoded = _encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    return f"{encoded}.{_encode(_sign(encoded))}", expires_in


def decode_customer_token(token: str) -> dict:
    try:
        encoded, supplied = token.split(".", 1)
        if not hmac.compare_digest(_decode(supplied), _sign(encoded)):
            raise ValueError("Invalid signature")
        payload = json.loads(_decode(encoded))
        if int(payload.get("exp", 0)) <= int(time.time()):
            raise ValueError("Expired token")
        return payload
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def require_customer(
    credentials: HTTPAuthorizationCredentials | None = Depends(customer_security),
) -> dict:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to continue",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_customer_token(credentials.credentials)


# ---------------------------------------------------------------------------
# Customer records
# ---------------------------------------------------------------------------


async def get_customer_by_username(username: str) -> dict | None:
    result = (
        get_supabase()
        .table("customers")
        .select("*")
        .eq("username", username)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


async def get_customer_by_phone(phone: str) -> dict | None:
    result = (
        get_supabase()
        .table("customers")
        .select("*")
        .eq("phone", phone)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


async def register_customer(
    *, username: str, password: str, phone: str, name: str | None = None
) -> dict:
    """
    Create (or claim) a customer account. Returns the stored row.

    A phone that already belongs to a *verified* account is rejected; an
    unverified row is re-claimed so an abandoned signup does not permanently
    lock the number.
    """
    supabase = get_supabase()

    if await get_customer_by_username(username):
        raise HTTPException(status_code=409, detail="That username is already taken")

    existing = await get_customer_by_phone(phone)
    if existing and existing.get("phone_verified") and existing.get("password_hash"):
        raise HTTPException(
            status_code=409,
            detail="An account already exists for this number. Please sign in.",
        )

    record = {
        "username": username,
        "password_hash": hash_password(password),
        "phone": phone,
        "phone_verified": False,
        "updated_at": _now_iso(),
    }
    if name:
        record["name"] = name

    if existing:
        result = (
            supabase.table("customers")
            .update(record)
            .eq("id", existing["id"])
            .execute()
        )
    else:
        result = supabase.table("customers").insert(record).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Could not create your account")
    return result.data[0]


# ---------------------------------------------------------------------------
# One-time passcodes
# ---------------------------------------------------------------------------


def _hash_code(phone: str, code: str) -> str:
    settings = get_settings()
    return hmac.new(
        settings.customer_auth_secret.encode("utf-8"),
        f"{phone}:{code}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def generate_otp() -> str:
    return f"{secrets.randbelow(10**OTP_LENGTH):0{OTP_LENGTH}d}"


async def _latest_otp(phone: str, purpose: str) -> dict | None:
    result = (
        get_supabase()
        .table("otp_codes")
        .select("*")
        .eq("phone", phone)
        .eq("purpose", purpose)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


async def issue_otp(phone: str, *, purpose: str = "phone_verification") -> bool:
    """
    Create and send a passcode. Returns whether the SMS was accepted.

    Callers must not reveal the code. When SMS is disabled the code is logged
    at debug level for local development only.
    """
    previous = await _latest_otp(phone, purpose)
    if previous and not previous.get("consumed_at"):
        created = _parse_ts(previous.get("created_at"))
        if created and (_now() - created).total_seconds() < OTP_RESEND_COOLDOWN_SECONDS:
            wait = OTP_RESEND_COOLDOWN_SECONDS - int((_now() - created).total_seconds())
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {max(wait, 1)}s before requesting another code",
            )

    code = generate_otp()
    expires_at = _now() + timedelta(seconds=OTP_TTL_SECONDS)

    get_supabase().table("otp_codes").insert(
        {
            "phone": phone,
            "code_hash": _hash_code(phone, code),
            "purpose": purpose,
            "attempt_count": 0,
            "expires_at": expires_at.isoformat(),
            "created_at": _now_iso(),
        }
    ).execute()

    settings = get_settings()
    body = (
        f"{settings.restaurant_name}: your verification code is {code}. "
        f"It expires in {OTP_TTL_SECONDS // 60} minutes."
    )
    sent = await send_sms(phone, body)
    if not sent:
        logger.warning(
            "Verification code for %s could not be sent by SMS", mask_phone(phone)
        )
        if settings.app_environment.lower() != "production":
            logger.info("DEV ONLY - code for %s is %s", mask_phone(phone), code)
    return sent


async def verify_otp(
    phone: str, code: str, *, purpose: str = "phone_verification"
) -> bool:
    """Consume a passcode. Raises 400/429 with a customer-safe message."""
    record = await _latest_otp(phone, purpose)
    if not record or record.get("consumed_at"):
        raise HTTPException(
            status_code=400, detail="Request a new code and try again"
        )

    expires_at = _parse_ts(record.get("expires_at"))
    if not expires_at or expires_at <= _now():
        raise HTTPException(status_code=400, detail="That code has expired")

    attempts = int(record.get("attempt_count") or 0)
    if attempts >= OTP_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail="Too many incorrect attempts. Request a new code.",
        )

    supabase = get_supabase()
    if not hmac.compare_digest(
        _hash_code(phone, (code or "").strip()), str(record.get("code_hash") or "")
    ):
        supabase.table("otp_codes").update({"attempt_count": attempts + 1}).eq(
            "id", record["id"]
        ).execute()
        remaining = OTP_MAX_ATTEMPTS - (attempts + 1)
        raise HTTPException(
            status_code=400,
            detail=f"Incorrect code. {max(remaining, 0)} attempt(s) left.",
        )

    supabase.table("otp_codes").update({"consumed_at": _now_iso()}).eq(
        "id", record["id"]
    ).execute()
    return True


async def mark_phone_verified(customer_id: str) -> dict | None:
    result = (
        get_supabase()
        .table("customers")
        .update(
            {
                "phone_verified": True,
                "phone_verified_at": _now_iso(),
                "updated_at": _now_iso(),
            }
        )
        .eq("id", customer_id)
        .execute()
    )
    return result.data[0] if result.data else None
