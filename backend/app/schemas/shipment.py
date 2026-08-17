from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, computed_field, field_validator, model_validator

from app.models.shipment import ServiceType, ShipmentStatus
from app.schemas.customer import ShipmentCustomerSummary
from app.schemas.pod import ProofOfDeliverySummary
from app.schemas.rider import ShipmentRiderSummary


def _strip(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("must not be empty")
    return cleaned


class PartySnapshot(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=1, max_length=32)
    email: EmailStr | None = None
    address: str = Field(min_length=1, max_length=255)
    city: str = Field(min_length=1, max_length=80)
    state: str | None = Field(default=None, max_length=80)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    postal_code: str | None = Field(default=None, max_length=20)

    @field_validator("name", "phone", "address", "city")
    @classmethod
    def required_strip(cls, value: str) -> str:
        return _strip(value)

    @field_validator("state", "postal_code")
    @classmethod
    def optional_strip(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("country")
    @classmethod
    def country_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().upper()
        if len(cleaned) != 2 or not cleaned.isalpha():
            raise ValueError("country must be a 2-letter ISO code")
        return cleaned


class PartyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, min_length=1, max_length=32)
    email: EmailStr | None = None
    address: str | None = Field(default=None, min_length=1, max_length=255)
    city: str | None = Field(default=None, min_length=1, max_length=80)
    state: str | None = Field(default=None, max_length=80)
    country: str | None = Field(default=None, min_length=2, max_length=2)
    postal_code: str | None = Field(default=None, max_length=20)

    @field_validator("country")
    @classmethod
    def country_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().upper()
        if len(cleaned) != 2 or not cleaned.isalpha():
            raise ValueError("country must be a 2-letter ISO code")
        return cleaned


class ParcelInfo(BaseModel):
    weight_kg: Decimal = Field(gt=0, max_digits=10, decimal_places=3)
    length_cm: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    width_cm: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    height_cm: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    package_type: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=500)
    quantity: int = Field(default=1, ge=1, le=9999)


class ParcelUpdate(BaseModel):
    weight_kg: Decimal | None = Field(default=None, gt=0, max_digits=10, decimal_places=3)
    length_cm: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    width_cm: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    height_cm: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    package_type: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=500)
    quantity: int | None = Field(default=None, ge=1, le=9999)


class CreateShipmentRequest(BaseModel):
    sender: PartySnapshot
    receiver: PartySnapshot
    parcel: ParcelInfo
    service_type: ServiceType = ServiceType.STANDARD
    reference_number: str | None = Field(default=None, max_length=80)
    notes: str | None = None
    pickup_at: datetime | None = None
    cod_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    status: ShipmentStatus = ShipmentStatus.BOOKED
    customer_id: UUID | None = None

    @field_validator("reference_number", "notes")
    @classmethod
    def optional_strip(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("currency")
    @classmethod
    def currency_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().upper()
        if len(cleaned) != 3 or not cleaned.isalpha():
            raise ValueError("currency must be a 3-letter ISO code")
        return cleaned

    @field_validator("status")
    @classmethod
    def initial_status(cls, value: ShipmentStatus) -> ShipmentStatus:
        if value not in {ShipmentStatus.DRAFT, ShipmentStatus.BOOKED}:
            raise ValueError("new shipments must start as DRAFT or BOOKED")
        return value

    @model_validator(mode="after")
    def cod_requires_currency(self) -> "CreateShipmentRequest":
        if self.cod_amount is not None and self.currency is None:
            raise ValueError("currency is required when cod_amount is set")
        return self


class UpdateShipmentRequest(BaseModel):
    sender: PartyUpdate | None = None
    receiver: PartyUpdate | None = None
    parcel: ParcelUpdate | None = None
    service_type: ServiceType | None = None
    reference_number: str | None = Field(default=None, max_length=80)
    notes: str | None = None
    pickup_at: datetime | None = None
    cod_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    customer_id: UUID | None = None

    @field_validator("currency")
    @classmethod
    def currency_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().upper()
        if len(cleaned) != 3 or not cleaned.isalpha():
            raise ValueError("currency must be a 3-letter ISO code")
        return cleaned


class ShipmentStatusHistoryResponse(BaseModel):
    id: UUID
    previous_status: str | None
    new_status: str
    changed_by_user_id: UUID | None
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def from_status(self) -> str | None:
        return self.previous_status

    @computed_field
    @property
    def to_status(self) -> str:
        return self.new_status


class ShipmentResponse(BaseModel):
    id: UUID
    organization_id: UUID
    tracking_number: str
    reference_number: str | None
    sender: PartySnapshot
    receiver: PartySnapshot
    parcel: ParcelInfo
    service_type: str
    status: str
    cod_amount: Decimal | None
    currency: str | None
    notes: str | None
    pickup_at: datetime | None
    picked_up_at: datetime | None = None
    in_transit_at: datetime | None = None
    out_for_delivery_at: datetime | None = None
    delivered_at: datetime | None = None
    cancelled_at: datetime | None = None
    customer_id: UUID | None = None
    customer: ShipmentCustomerSummary | None = None
    rider_id: UUID | None = None
    rider: ShipmentRiderSummary | None = None
    pod: ProofOfDeliverySummary | None = None
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
    status_history: list[ShipmentStatusHistoryResponse] = []

    model_config = {"from_attributes": True}


class ShipmentListItem(BaseModel):
    id: UUID
    tracking_number: str
    reference_number: str | None
    receiver_name: str
    receiver_city: str
    service_type: str
    status: str
    customer_id: UUID | None = None
    customer_code: str | None = None
    customer_name: str | None = None
    rider_id: UUID | None = None
    rider_code: str | None = None
    rider_name: str | None = None
    created_at: datetime


class ShipmentListResponse(BaseModel):
    items: list[ShipmentListItem]
    page: int
    page_size: int
    total: int


class CustomerShipmentListResponse(ShipmentListResponse):
    """Paginated shipments for one customer, still scoped to the current organization."""


class CancelShipmentRequest(BaseModel):
    note: str | None = Field(default=None, max_length=255)

    @field_validator("note")
    @classmethod
    def optional_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ChangeShipmentStatusRequest(BaseModel):
    status: ShipmentStatus
    note: str | None = Field(default=None, max_length=255)

    @field_validator("note")
    @classmethod
    def optional_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ShipmentHistoryListResponse(BaseModel):
    items: list[ShipmentStatusHistoryResponse]
