from datetime import datetime
from uuid import UUID

from app.core.config import settings
from pydantic import BaseModel, EmailStr, Field, field_validator


def normalize_email(email: str) -> str:
    return email.strip().lower()


class UserPublic(BaseModel):
    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    phone: str | None
    is_active: bool
    email_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    phone: str | None = Field(default=None, max_length=32)

    @field_validator("password")
    @classmethod
    def enforce_password_policy(cls, value: str) -> str:
        minimum = settings.auth_password_min_length
        if len(value) < minimum:
            raise ValueError(f"Password must be at least {minimum} characters.")
        return value

    @field_validator("email")
    @classmethod
    def normalize(cls, value: EmailStr) -> str:
        return normalize_email(str(value))

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_names(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)

    @field_validator("email")
    @classmethod
    def normalize(cls, value: EmailStr) -> str:
        return normalize_email(str(value))


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MembershipPublic(BaseModel):
    id: UUID
    organization_id: UUID
    role_code: str
    status: str

    model_config = {"from_attributes": True}


class MeResponse(BaseModel):
    user: UserPublic
    memberships: list[MembershipPublic]
    current_organization_id: UUID | None = None
