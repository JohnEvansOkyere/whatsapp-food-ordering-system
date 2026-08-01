"""Customer account endpoints: signup, phone verification, sign in."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.customer import (
    CustomerLoginSchema,
    CustomerLoginStartResponseSchema,
    CustomerProfileSchema,
    CustomerSessionSchema,
    CustomerSignupResponseSchema,
    CustomerSignupSchema,
    ResendOtpSchema,
    VerifyOtpSchema,
)
from app.services.customer_auth_service import (
    create_customer_token,
    get_customer_by_phone,
    issue_otp,
    mark_phone_verified,
    register_customer,
    require_customer,
    validate_password,
    validate_phone,
    validate_username,
    verify_otp,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/customer", tags=["customer-auth"])


def _profile(customer: dict) -> CustomerProfileSchema:
    return CustomerProfileSchema(
        id=str(customer["id"]),
        username=customer.get("username"),
        name=customer.get("name"),
        phone=str(customer.get("phone") or ""),
        phone_verified=bool(customer.get("phone_verified")),
    )


@router.post("/signup", response_model=CustomerSignupResponseSchema)
async def signup(payload: CustomerSignupSchema):
    username = validate_username(payload.username)
    validate_password(payload.password, payload.password_confirmation)
    phone = validate_phone(payload.phone)

    customer = await register_customer(
        username=username,
        password=payload.password,
        phone=phone,
        name=payload.name,
    )
    code_sent = await issue_otp(phone)

    return CustomerSignupResponseSchema(
        customer=_profile(customer),
        verification_required=True,
        code_sent=code_sent,
        message=(
            "We sent a 6-digit code to your phone."
            if code_sent
            else "Account created, but the verification SMS could not be sent. "
            "Tap resend in a moment."
        ),
    )


@router.post("/verify", response_model=CustomerSessionSchema)
async def verify(payload: VerifyOtpSchema):
    phone = validate_phone(payload.phone)
    customer = await get_customer_by_phone(phone)
    if not customer:
        raise HTTPException(status_code=404, detail="No account for this number")

    await verify_otp(phone, payload.code)
    updated = await mark_phone_verified(str(customer["id"])) or customer

    token, expires_in = create_customer_token(updated)
    return CustomerSessionSchema(
        access_token=token, expires_in=expires_in, customer=_profile(updated)
    )


@router.post("/resend")
async def resend(payload: ResendOtpSchema):
    phone = validate_phone(payload.phone)
    customer = await get_customer_by_phone(phone)
    # Do not disclose whether the number is registered.
    if customer:
        code_sent = await issue_otp(phone)
        return {"code_sent": code_sent}
    return {"code_sent": False}


@router.post("/login", response_model=CustomerLoginStartResponseSchema)
async def login(payload: CustomerLoginSchema):
    """Start a phone sign-in by texting a one-time code to a registered number."""
    phone = validate_phone(payload.phone)
    customer = await get_customer_by_phone(phone)
    if not customer:
        raise HTTPException(
            status_code=404,
            detail="No account uses this number yet. Create one to get started.",
        )
    code_sent = await issue_otp(phone)
    return CustomerLoginStartResponseSchema(
        code_sent=code_sent,
        message=(
            "We sent a 6-digit sign-in code to your phone."
            if code_sent
            else "We could not send the code just now. Tap resend in a moment."
        ),
    )


@router.get("/me", response_model=CustomerProfileSchema)
async def me(session: dict = Depends(require_customer)):
    customer = await get_customer_by_phone(str(session.get("phone") or ""))
    if not customer:
        raise HTTPException(status_code=404, detail="Account not found")
    return _profile(customer)
