from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.pod_evidence import PodEvidenceStatus, PodEvidenceType

ALLOWED_POD_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MIME_EXTENSIONS = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/webp": {".webp"},
}


def _strip(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("must not be empty")
    return cleaned


class CreatePodUploadRequest(BaseModel):
    model_config = {"extra": "ignore"}

    type: PodEvidenceType
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=64)
    size_bytes: int = Field(ge=1)

    @field_validator("filename")
    @classmethod
    def safe_filename(cls, value: str) -> str:
        cleaned = _strip(value)
        if "/" in cleaned or "\\" in cleaned or ".." in cleaned:
            raise ValueError("filename must be a basename without path separators")
        return cleaned

    @field_validator("content_type")
    @classmethod
    def allowed_mime(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned == "application/octet-stream":
            raise ValueError("content_type application/octet-stream is not allowed")
        if cleaned not in ALLOWED_POD_MIME_TYPES:
            raise ValueError("content_type must be image/jpeg, image/png, or image/webp")
        return cleaned


class PodEvidenceSummary(BaseModel):
    id: UUID
    type: PodEvidenceType
    status: PodEvidenceStatus
    content_type: str
    size_bytes: int
    original_filename: str
    uploaded_at: datetime | None
    expired_at: datetime | None = None
    created_at: datetime


class PodEvidenceResponse(BaseModel):
    id: UUID
    organization_id: UUID
    pod_id: UUID
    shipment_id: UUID
    type: PodEvidenceType
    status: PodEvidenceStatus
    original_filename: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime | None
    expired_at: datetime | None = None
    created_at: datetime
    created_by_user_id: UUID | None


class PodUploadInstructionsResponse(BaseModel):
    upload_id: UUID
    evidence_id: UUID
    type: PodEvidenceType
    status: PodEvidenceStatus
    object_key: str
    upload_url: str
    method: str
    headers: dict[str, str]
    expires_at: datetime


class PodEvidenceListResponse(BaseModel):
    items: list[PodEvidenceSummary]


class PodDownloadResponse(BaseModel):
    evidence_id: UUID
    download_url: str
    method: str
    expires_at: datetime
