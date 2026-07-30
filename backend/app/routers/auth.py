from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas.auth import StaffLoginSchema, StaffPrincipalSchema, StaffSessionSchema
from app.services.auth_service import (
    authenticate_staff,
    create_staff_token,
    require_staff,
)

router = APIRouter(prefix="/auth", tags=["staff-auth"])


@router.post("/staff/login", response_model=StaffSessionSchema)
async def staff_login(payload: StaffLoginSchema):
    staff = authenticate_staff(payload.username, payload.password)
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token, expires_in = create_staff_token(staff)
    return StaffSessionSchema(
        access_token=token,
        expires_in=expires_in,
        staff=staff,
    )


@router.get("/staff/me", response_model=StaffPrincipalSchema)
async def staff_me(staff: StaffPrincipalSchema = Depends(require_staff)):
    return staff
