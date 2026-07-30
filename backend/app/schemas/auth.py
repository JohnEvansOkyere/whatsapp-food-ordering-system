from pydantic import BaseModel, Field


class StaffLoginSchema(BaseModel):
    username: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=8, max_length=200)


class StaffPrincipalSchema(BaseModel):
    username: str
    display_name: str
    role: str
    branch_ids: list[str]


class StaffSessionSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    staff: StaffPrincipalSchema
