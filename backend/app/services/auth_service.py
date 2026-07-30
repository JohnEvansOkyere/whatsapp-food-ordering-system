"""Small signed-session staff authentication for the provisional launch build."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.schemas.auth import StaffPrincipalSchema
from app.services.branch_service import ABELEMKPE_BRANCH_ID, ASHESI_BRANCH_ID

security = HTTPBearer(auto_error=False)


def _accounts() -> dict[str, StaffPrincipalSchema]:
    return {
        "owner": StaffPrincipalSchema(
            username="owner",
            display_name="Restaurant Owner",
            role="tenant_owner",
            branch_ids=[ASHESI_BRANCH_ID, ABELEMKPE_BRANCH_ID],
        ),
        "ashesi": StaffPrincipalSchema(
            username="ashesi",
            display_name="Ashesi Kitchen",
            role="manager",
            branch_ids=[ASHESI_BRANCH_ID],
        ),
        "abelemkpe": StaffPrincipalSchema(
            username="abelemkpe",
            display_name="Abelemkpe Kitchen",
            role="manager",
            branch_ids=[ABELEMKPE_BRANCH_ID],
        ),
        "ashesi-kitchen": StaffPrincipalSchema(
            username="ashesi-kitchen",
            display_name="Ashesi Kitchen Team",
            role="kitchen",
            branch_ids=[ASHESI_BRANCH_ID],
        ),
        "abelemkpe-kitchen": StaffPrincipalSchema(
            username="abelemkpe-kitchen",
            display_name="Abelemkpe Kitchen Team",
            role="kitchen",
            branch_ids=[ABELEMKPE_BRANCH_ID],
        ),
        "ashesi-dispatch": StaffPrincipalSchema(
            username="ashesi-dispatch",
            display_name="Ashesi Dispatch",
            role="dispatch",
            branch_ids=[ASHESI_BRANCH_ID],
        ),
        "abelemkpe-dispatch": StaffPrincipalSchema(
            username="abelemkpe-dispatch",
            display_name="Abelemkpe Dispatch",
            role="dispatch",
            branch_ids=[ABELEMKPE_BRANCH_ID],
        ),
        "support": StaffPrincipalSchema(
            username="support",
            display_name="Customer Support",
            role="support",
            branch_ids=[ASHESI_BRANCH_ID, ABELEMKPE_BRANCH_ID],
        ),
    }


def authenticate_staff(username: str, password: str) -> StaffPrincipalSchema | None:
    settings = get_settings()
    principal = _accounts().get(username.strip().lower())
    password_ok = hmac.compare_digest(
        password.encode("utf-8"),
        settings.staff_demo_password.encode("utf-8"),
    )
    return principal if principal and password_ok else None


def _encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def create_staff_token(principal: StaffPrincipalSchema) -> tuple[str, int]:
    settings = get_settings()
    expires_in = settings.staff_token_ttl_minutes * 60
    payload = {
        **principal.model_dump(),
        "exp": int(time.time()) + expires_in,
        "iat": int(time.time()),
    }
    encoded = _encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signature = hmac.new(
        settings.staff_auth_secret.encode("utf-8"),
        encoded.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{encoded}.{_encode(signature)}", expires_in


def decode_staff_token(token: str) -> StaffPrincipalSchema:
    settings = get_settings()
    try:
        encoded, supplied_signature = token.split(".", 1)
        expected_signature = hmac.new(
            settings.staff_auth_secret.encode("utf-8"),
            encoded.encode("ascii"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(_decode(supplied_signature), expected_signature):
            raise ValueError("Invalid signature")
        payload = json.loads(_decode(encoded))
        if int(payload.get("exp", 0)) <= int(time.time()):
            raise ValueError("Expired token")
        return StaffPrincipalSchema.model_validate(payload)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Staff session is invalid or expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def require_staff(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> StaffPrincipalSchema:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Staff sign-in required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_staff_token(credentials.credentials)


def ensure_branch_access(staff: StaffPrincipalSchema, branch_id: str | None) -> None:
    if branch_id and branch_id not in staff.branch_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this branch",
        )


def ensure_role(staff: StaffPrincipalSchema, *allowed_roles: str) -> None:
    if staff.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your staff role cannot perform this action",
        )
