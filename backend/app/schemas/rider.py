from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.rider import RiderStatus, VehicleType
from app.schemas.auth import normalize_email


def _optional_strip(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


class CreateRiderRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=5, max_length=32)
    email: EmailStr | None = None
    vehicle_type: VehicleType | None = None
    vehicle_number: str | None = Field(default=None, max_length=32)
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

    @field_validator("vehicle_number", "notes")
    @classmethod
    def optional_fields(cls, value: str | None) -> str | None:
        return _optional_strip(value)


class UpdateRiderRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, min_length=5, max_length=32)
    email: EmailStr | None = None
    vehicle_type: VehicleType | None = None
    vehicle_number: str | None = Field(default=None, max_length=32)
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

    @field_validator("vehicle_number", "notes")
    @classmethod
    def optional_fields(cls, value: str | None) -> str | None:
        return _optional_strip(value)


class RiderResponse(BaseModel):
    id: UUID
    organization_id: UUID
    rider_code: str
    name: str
    phone: str
    email: str | None
    vehicle_type: str | None
    vehicle_number: str | None
    notes: str | None
    status: RiderStatus
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
    assigned_shipment_count: int | None = None
    out_for_delivery_count: int | None = None

    model_config = {"from_attributes": True}


class RiderListItem(BaseModel):
    id: UUID
    rider_code: str
    name: str
    phone: str
    email: str | None
    vehicle_type: str | None
    vehicle_number: str | None
    status: str
    created_at: datetime


class RiderListResponse(BaseModel):
    items: list[RiderListItem]
    page: int
    page_size: int
    total: int


class ShipmentRiderSummary(BaseModel):
    id: UUID
    rider_code: str
    name: str


class AssignRiderRequest(BaseModel):
    rider_id: UUID
    note: str | None = Field(default=None, max_length=255)

    @field_validator("note")
    @classmethod
    def optional_note(cls, value: str | None) -> str | None:
        return _optional_strip(value)


class UnassignRiderRequest(BaseModel):
    note: str | None = Field(default=None, max_length=255)

    @field_validator("note")
    @classmethod
    def optional_note(cls, value: str | None) -> str | None:
        return _optional_strip(value)


class RiderAssignmentResponse(BaseModel):
    id: UUID
    shipment_id: UUID
    rider_id: UUID
    rider_code: str
    rider_name: str
    assigned_at: datetime
    unassigned_at: datetime | None
    assigned_by_user_id: UUID | None
    unassigned_by_user_id: UUID | None
    note: str | None


class RiderAssignmentHistoryResponse(BaseModel):
    items: list[RiderAssignmentResponse]
