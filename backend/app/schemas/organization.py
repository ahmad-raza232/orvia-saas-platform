from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.slugs import is_reserved_slug, slugify
from app.models.organization import OrganizationStatus
from app.schemas.auth import normalize_email


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=80)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = slugify(value)
        if not cleaned:
            return None
        if is_reserved_slug(cleaned):
            raise ValueError("this slug is reserved")
        return cleaned


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=80)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = slugify(value)
        if not cleaned:
            raise ValueError("must not be empty")
        if is_reserved_slug(cleaned):
            raise ValueError("this slug is reserved")
        return cleaned


class OrganizationPublic(BaseModel):
    id: UUID
    name: str
    slug: str
    status: OrganizationStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SwitchOrganizationRequest(BaseModel):
    organization_id: UUID


class UserOrganizationMembership(BaseModel):
    id: UUID
    role_code: str
    status: str


class UserOrganizationPublic(BaseModel):
    id: UUID
    name: str
    slug: str
    status: OrganizationStatus
    membership: UserOrganizationMembership


class MemberInviteRequest(BaseModel):
    email: EmailStr
    role_code: str = Field(min_length=1, max_length=64)

    @field_validator("email")
    @classmethod
    def normalize(cls, value: EmailStr) -> str:
        return normalize_email(str(value))

    @field_validator("role_code")
    @classmethod
    def normalize_role(cls, value: str) -> str:
        return value.strip().upper()


class MemberUpdateRequest(BaseModel):
    role_code: str | None = Field(default=None, max_length=64)
    status: str | None = Field(default=None, max_length=32)

    @field_validator("role_code")
    @classmethod
    def normalize_role(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip().upper()

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().upper()
        if cleaned not in {"ACTIVE", "SUSPENDED"}:
            raise ValueError("status must be ACTIVE or SUSPENDED")
        return cleaned


class MemberPublic(BaseModel):
    id: UUID
    user_id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    role_code: str
    status: str
    created_at: datetime


class InvitationAcceptRequest(BaseModel):
    token: str = Field(min_length=16, max_length=128)


class InvitationPublic(BaseModel):
    id: UUID
    organization_id: UUID
    email: EmailStr
    role_code: str
    status: str
    expires_at: datetime
    created_at: datetime


class InvitationCreatedResponse(InvitationPublic):
    """Invitation metadata. The raw token is never included in API responses."""
