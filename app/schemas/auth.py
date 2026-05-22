from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.core.enums import AdminRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AdminMe(BaseModel):
    id: int
    email: EmailStr
    role: AdminRole
    last_login_at: datetime | None

    model_config = {"from_attributes": True}
