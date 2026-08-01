from typing import Optional

from pydantic import BaseModel, Field


class CustomerSignupSchema(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=8, max_length=128)
    password_confirmation: str = Field(..., min_length=8, max_length=128)
    phone: str = Field(..., min_length=9, max_length=20)
    name: Optional[str] = Field(default=None, max_length=100)


class CustomerLoginSchema(BaseModel):
    """Sign-in starts from the contact number; a texted code proves ownership."""

    phone: str = Field(..., min_length=9, max_length=20)


class VerifyOtpSchema(BaseModel):
    phone: str = Field(..., min_length=9, max_length=20)
    code: str = Field(..., min_length=4, max_length=8)


class ResendOtpSchema(BaseModel):
    phone: str = Field(..., min_length=9, max_length=20)


class CustomerProfileSchema(BaseModel):
    id: str
    username: Optional[str] = None
    name: Optional[str] = None
    phone: str
    phone_verified: bool = False


class CustomerSignupResponseSchema(BaseModel):
    """Signup does not return a session — the phone must be verified first."""

    customer: CustomerProfileSchema
    verification_required: bool = True
    code_sent: bool
    message: str


class CustomerLoginStartResponseSchema(BaseModel):
    """Login does not return a session — the texted code must be verified first."""

    code_sent: bool
    message: str


class CustomerSessionSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    customer: CustomerProfileSchema
