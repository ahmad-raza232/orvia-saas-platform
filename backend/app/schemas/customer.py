from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.customer import CustomerStatus
from app.schemas.auth import normalize_email


def _optional_strip(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


class CreateCustomerRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=5, max_length=32)
    email: EmailStr | None = None
    alternate_phone: str | None = Field(default=None, max_length=32)
    company_name: str | None = Field(default=None, max_length=160)
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=80)
    state: str | None = Field(default=None, max_length=80)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    postal_code: str | None = Field(default=None, max_length=20)
    notes: str | None = None

    @field_validator("name", "phone")
    @classmethod
    def required_strip(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned

    @field_validator("email")
    @classmethod
    def normalize(cls, value: EmailStr | None) -> str | None:
        if value is None:
            return None
        return normalize_email(str(value))

    @field_validator("alternate_phone", "company_name", "address", "city", "state", "postal_code", "notes")
    @classmethod
    def optional_fields(cls, value: str | None) -> str | None:
        return _optional_strip(value)

    @field_validator("country")
    @classmethod
    def country_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().upper()
        if len(cleaned) != 2 or not cleaned.isalpha():
            raise ValueError("country must be a 2-letter ISO code")
        return cleaned


class UpdateCustomerRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, min_length=5, max_length=32)
    email: EmailStr | None = None
    alternate_phone: str | None = Field(default=None, max_length=32)
    company_name: str | None = Field(default=None, max_length=160)
    address: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=80)
    state: str | None = Field(default=None, max_length=80)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    postal_code: str | None = Field(default=None, max_length=20)
    notes: str | None = None

    @field_validator("name", "phone")
    @classmethod
    def required_strip(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("must not be empty")
        return cleaned

    @field_validator("email")
    @classmethod
    def normalize(cls, value: EmailStr | None) -> str | None:
        if value is None:
            return None
        return normalize_email(str(value))

    @field_validator("alternate_phone", "company_name", "address", "city", "state", "postal_code", "notes")
    @classmethod
    def optional_fields(cls, value: str | None) -> str | None:
        return _optional_strip(value)

    @field_validator("country")
    @classmethod
    def country_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().upper()
        if len(cleaned) != 2 or not cleaned.isalpha():
            raise ValueError("country must be a 2-letter ISO code")
        return cleaned


class CustomerResponse(BaseModel):
    id: UUID
    organization_id: UUID
    customer_code: str
    name: str
    email: str | None
    phone: str
    alternate_phone: str | None
    company_name: str | None
    address: str | None
    city: str | None
    state: str | None
    country: str | None
    postal_code: str | None
    notes: str | None
    status: CustomerStatus
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
    shipment_count: int | None = None
    active_shipment_count: int | None = None
    latest_shipment_at: datetime | None = None

    model_config = {"from_attributes": True}


class CustomerListItem(BaseModel):
    id: UUID
    customer_code: str
    name: str
    email: str | None
    phone: str
    company_name: str | None
    city: str | None
    status: str
    created_at: datetime


class CustomerListResponse(BaseModel):
    items: list[CustomerListItem]
    page: int
    page_size: int
    total: int


class ShipmentCustomerSummary(BaseModel):
    id: UUID
    customer_code: str
    name: str
