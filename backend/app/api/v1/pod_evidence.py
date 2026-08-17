from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import TenantContext, require_roles
from app.db.database import get_db
from app.models.pod_evidence import PodEvidence
from app.models.role import POD_CREATE_ROLES, SHIPMENT_READ_ROLES
from app.schemas.pod_evidence import (
    CreatePodUploadRequest,
    PodDownloadResponse,
    PodEvidenceListResponse,
    PodEvidenceResponse,
    PodEvidenceSummary,
    PodUploadInstructionsResponse,
)
from app.services.pod_evidence_service import PodEvidenceService
from app.services.storage_provider import StorageProvider, get_storage_provider

router = APIRouter(prefix="/shipments", tags=["pod-evidence"])

require_pod_create = require_roles(*POD_CREATE_ROLES)
require_shipment_read = require_roles(*SHIPMENT_READ_ROLES)


def to_evidence_summary(row: PodEvidence) -> PodEvidenceSummary:
    return PodEvidenceSummary(
        id=row.id,
        type=row.evidence_type,
        status=row.status,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        original_filename=row.original_filename,
        uploaded_at=row.uploaded_at,
        expired_at=row.expired_at,
        created_at=row.created_at,
    )


def to_evidence_response(row: PodEvidence) -> PodEvidenceResponse:
    return PodEvidenceResponse(
        id=row.id,
        organization_id=row.organization_id,
        pod_id=row.pod_id,
        shipment_id=row.shipment_id,
        type=row.evidence_type,
        status=row.status,
        original_filename=row.original_filename,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        uploaded_at=row.uploaded_at,
        expired_at=row.expired_at,
        created_at=row.created_at,
        created_by_user_id=row.created_by_user_id,
    )


@router.post(
    "/{shipment_id}/pod/uploads",
    response_model=PodUploadInstructionsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request a signed POD evidence upload URL",
    description=(
        "Creates a PENDING evidence record and returns a short-lived signed upload URL. "
        "The client uploads directly to object storage. STAFF cannot request uploads."
    ),
)
def request_pod_upload(
    shipment_id: UUID,
    payload: CreatePodUploadRequest,
    ctx: TenantContext = Depends(require_pod_create),
    db: Session = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> PodUploadInstructionsResponse:
    evidence, signed = PodEvidenceService(db, storage).request_upload(
        shipment_id,
        ctx.organization.id,
        ctx.user,
        payload,
    )
    return PodUploadInstructionsResponse(
        upload_id=evidence.id,
        evidence_id=evidence.id,
        type=evidence.evidence_type,
        status=evidence.status,
        object_key=evidence.object_key,
        upload_url=signed.url,
        method=signed.method,
        headers=signed.headers,
        expires_at=signed.expires_at,
    )


@router.post(
    "/{shipment_id}/pod/uploads/{upload_id}/complete",
    response_model=PodEvidenceResponse,
    summary="Confirm a POD evidence upload",
    description=(
        "Verifies the object in storage and marks PENDING evidence UPLOADED. "
        "Missing or invalid objects are marked FAILED."
    ),
)
def complete_pod_upload(
    shipment_id: UUID,
    upload_id: UUID,
    ctx: TenantContext = Depends(require_pod_create),
    db: Session = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> PodEvidenceResponse:
    evidence = PodEvidenceService(db, storage).complete_upload(
        shipment_id,
        ctx.organization.id,
        ctx.user,
        upload_id,
    )
    return to_evidence_response(evidence)


@router.get(
    "/{shipment_id}/pod/evidence",
    response_model=PodEvidenceListResponse,
    summary="List POD evidence metadata",
    description="Returns evidence metadata for a shipment in the current organization. CUSTOMER is denied.",
)
def list_pod_evidence(
    shipment_id: UUID,
    ctx: TenantContext = Depends(require_shipment_read),
    db: Session = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> PodEvidenceListResponse:
    items = PodEvidenceService(db, storage).list_for_shipment(
        shipment_id, ctx.organization.id
    )
    return PodEvidenceListResponse(items=[to_evidence_summary(item) for item in items])


@router.get(
    "/{shipment_id}/pod/evidence/{evidence_id}/download",
    response_model=PodDownloadResponse,
    summary="Request a signed POD evidence download URL",
    description="Returns a short-lived signed GET URL for UPLOADED evidence in the current organization.",
)
def download_pod_evidence(
    shipment_id: UUID,
    evidence_id: UUID,
    ctx: TenantContext = Depends(require_shipment_read),
    db: Session = Depends(get_db),
    storage: StorageProvider = Depends(get_storage_provider),
) -> PodDownloadResponse:
    evidence, signed = PodEvidenceService(db, storage).create_download_url(
        shipment_id,
        ctx.organization.id,
        ctx.user,
        evidence_id,
    )
    return PodDownloadResponse(
        evidence_id=evidence.id,
        download_url=signed.url,
        method=signed.method,
        expires_at=signed.expires_at,
    )
