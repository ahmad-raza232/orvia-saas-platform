from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.schemas.pod_evidence import PodEvidenceSummary

ALLOWED_POD_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_POD_FILE_SIZE = 15_000_000


def _strip(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("must not be empty")
    return cleaned


class PodFileMetadata(BaseModel):
    """Placeholder metadata only. URLs are untrusted storage hints, not verified content."""

    file_name: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=64)
    storage_key: str = Field(min_length=1, max_length=512)
    url: str | None = Field(default=None, max_length=1024)
    file_size: int | None = Field(default=None, ge=1, le=MAX_POD_FILE_SIZE)
    checksum: str | None = Field(default=None, max_length=128)

    @field_validator("file_name")
    @classmethod
    def safe_file_name(cls, value: str) -> str:
        cleaned = _strip(value)
        if "/" in cleaned or "\\" in cleaned or ".." in cleaned:
            raise ValueError("file_name must be a basename without path separators")
        return cleaned

    @field_validator("mime_type")
    @classmethod
    def allowed_mime(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in ALLOWED_POD_MIME_TYPES:
            raise ValueError("mime_type must be image/jpeg, image/png, or image/webp")
        return cleaned

    @field_validator("storage_key")
    @classmethod
    def safe_storage_key(cls, value: str) -> str:
        cleaned = _strip(value)
        if ".." in cleaned or cleaned.startswith("/") or "\\" in cleaned:
            raise ValueError("storage_key must be a relative key without '..' or leading slash")
        return cleaned

    @field_validator("url")
    @classmethod
    def untrusted_placeholder_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        lowered = cleaned.lower()
        if lowered.startswith(("javascript:", "data:", "file:", "http:")):
            raise ValueError("url must be an https placeholder or omitted")
        if not lowered.startswith("https://"):
            raise ValueError("url must be an https placeholder or omitted")
        return cleaned

    @field_validator("checksum")
    @classmethod
    def hex_checksum(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if not cleaned:
            return None
        if len(cleaned) < 32 or len(cleaned) > 128 or any(ch not in "0123456789abcdef" for ch in cleaned):
            raise ValueError("checksum must be a hex digest")
        return cleaned


class CreateProofOfDeliveryRequest(BaseModel):
    model_config = {"extra": "ignore"}

    recipient_name: str = Field(min_length=1, max_length=120)
    delivery_note: str | None = Field(default=None, max_length=500)
    signature: PodFileMetadata | None = None
    photo: PodFileMetadata | None = None

    @field_validator("recipient_name")
    @classmethod
    def required_name(cls, value: str) -> str:
        return _strip(value)

    @field_validator("delivery_note")
    @classmethod
    def optional_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ProofOfDeliverySummary(BaseModel):
    pod_id: UUID
    recipient_name: str
    delivered_at: datetime
    has_signature: bool
    has_photo: bool


class ProofOfDeliveryResponse(BaseModel):
    id: UUID
    organization_id: UUID
    shipment_id: UUID
    recipient_name: str
    delivery_note: str | None
    delivered_at: datetime
    recorded_by_user_id: UUID | None
    rider_id: UUID | None
    rider_code: str | None = None
    rider_name: str | None = None
    signature: PodFileMetadata | None = None
    photo: PodFileMetadata | None = None
    has_signature: bool
    has_photo: bool
    evidence: list[PodEvidenceSummary] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}
