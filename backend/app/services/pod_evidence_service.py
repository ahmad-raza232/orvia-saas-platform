from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    NotFoundError,
    PodEvidenceAlreadyUploadedError,
    PodEvidenceExpiredError,
    PodEvidenceNotReadyError,
    PodEvidenceUploadFailedError,
    PodEvidenceValidationError,
    PodNotAllowedError,
    StorageUnavailableAPIError,
)
from app.core.image_magic import PREFIX_BYTES, content_matches_declared_type
from app.core.storage_keys import generate_pod_object_key
from app.models.pod_evidence import PodEvidence, PodEvidenceStatus, PodEvidenceType
from app.models.shipment import ShipmentStatus
from app.models.user import User
from app.repositories.pod_evidence_repository import PodEvidenceRepository
from app.repositories.pod_repository import ProofOfDeliveryRepository
from app.repositories.shipment_repository import ShipmentRepository
from app.schemas.pod_evidence import MIME_EXTENSIONS, CreatePodUploadRequest
from app.services.audit_service import AuditService
from app.services.storage_provider import (
    StorageProvider,
    StorageUnavailableError,
    get_storage_provider,
)


def _max_bytes_for_type(evidence_type: str) -> int:
    if evidence_type == PodEvidenceType.SIGNATURE.value:
        return settings.pod_signature_max_bytes
    return settings.pod_photo_max_bytes


def _validate_filename_extension(filename: str, content_type: str) -> None:
    suffix = Path(filename).suffix.lower()
    allowed = MIME_EXTENSIONS.get(content_type, set())
    if not suffix:
        raise PodEvidenceValidationError("filename must include a matching image extension")
    if suffix not in allowed:
        raise PodEvidenceValidationError(
            "filename extension does not match the declared content type"
        )


class PodEvidenceService:
    def __init__(self, db: Session, storage: StorageProvider | None = None) -> None:
        self.db = db
        self.storage = storage or get_storage_provider()
        self.evidence = PodEvidenceRepository(db)
        self.pods = ProofOfDeliveryRepository(db)
        self.shipments = ShipmentRepository(db)
        self.audit = AuditService(db)

    def _load_pod(self, shipment_id: UUID, organization_id: UUID):
        shipment = self.shipments.get_for_organization(shipment_id, organization_id)
        if shipment is None:
            raise NotFoundError("Shipment not found.")
        pod = self.pods.get_for_organization(shipment.id, organization_id)
        if pod is None:
            raise NotFoundError("Proof of delivery not found.")
        return shipment, pod

    def _load_delivered_pod(self, shipment_id: UUID, organization_id: UUID):
        shipment = self.shipments.get_for_organization(shipment_id, organization_id)
        if shipment is None:
            raise NotFoundError("Shipment not found.")
        if shipment.status != ShipmentStatus.DELIVERED.value:
            raise PodNotAllowedError()
        pod = self.pods.get_for_organization(shipment.id, organization_id)
        if pod is None:
            raise NotFoundError("Proof of delivery not found.")
        return shipment, pod

    def _load_evidence(
        self,
        shipment_id: UUID,
        organization_id: UUID,
        evidence_id: UUID,
        *,
        for_update: bool = False,
    ) -> PodEvidence:
        shipment = self.shipments.get_for_organization(shipment_id, organization_id)
        if shipment is None:
            raise NotFoundError("Shipment not found.")
        pod = self.pods.get_for_organization(shipment.id, organization_id)
        if pod is None:
            raise NotFoundError("Proof of delivery not found.")
        row = (
            self.evidence.get_for_organization_for_update(evidence_id, organization_id)
            if for_update
            else self.evidence.get_for_organization(evidence_id, organization_id)
        )
        if (
            row is None
            or row.shipment_id != shipment.id
            or row.pod_id != pod.id
        ):
            raise NotFoundError("Proof of delivery not found.")
        return row

    def list_for_shipment(self, shipment_id: UUID, organization_id: UUID) -> list[PodEvidence]:
        _shipment, pod = self._load_pod(shipment_id, organization_id)
        return self.evidence.list_for_pod(pod.id, organization_id)

    def request_upload(
        self,
        shipment_id: UUID,
        organization_id: UUID,
        actor: User,
        payload: CreatePodUploadRequest,
    ) -> tuple[PodEvidence, object]:
        evidence_type = payload.type.value
        shipment, pod = self._load_delivered_pod(shipment_id, organization_id)
        max_bytes = _max_bytes_for_type(evidence_type)
        if payload.size_bytes > max_bytes:
            raise PodEvidenceValidationError(
                f"size_bytes exceeds the limit of {max_bytes} for {evidence_type}"
            )
        _validate_filename_extension(payload.filename, payload.content_type)
        if self.evidence.get_uploaded_for_type(pod.id, evidence_type) is not None:
            raise PodEvidenceAlreadyUploadedError()

        object_key = generate_pod_object_key(organization_id, shipment.id, pod.id)
        row = PodEvidence(
            organization_id=organization_id,
            pod_id=pod.id,
            shipment_id=shipment.id,
            evidence_type=evidence_type,
            object_key=object_key,
            original_filename=payload.filename,
            content_type=payload.content_type,
            size_bytes=payload.size_bytes,
            status=PodEvidenceStatus.PENDING.value,
            created_by_user_id=actor.id,
        )
        self.evidence.create(row)
        self.audit.record(
            action="POD_EVIDENCE_UPLOAD_REQUESTED",
            resource_type="pod_evidence",
            resource_id=row.id,
            organization_id=organization_id,
            actor_user_id=actor.id,
            details={
                "shipment_id": str(shipment.id),
                "tracking_number": shipment.tracking_number,
                "pod_id": str(pod.id),
                "evidence_id": str(row.id),
                "evidence_type": evidence_type,
                "content_type": payload.content_type,
                "size_bytes": payload.size_bytes,
            },
        )
        self.db.commit()

        try:
            signed = self.storage.create_upload_url(
                object_key,
                payload.content_type,
                settings.pod_upload_url_ttl_seconds,
            )
        except StorageUnavailableError:
            failed = self.evidence.get_by_id(row.id)
            if failed is not None and failed.status == PodEvidenceStatus.PENDING.value:
                failed.status = PodEvidenceStatus.FAILED.value
                self.audit.record(
                    action="POD_EVIDENCE_UPLOAD_FAILED",
                    resource_type="pod_evidence",
                    resource_id=failed.id,
                    organization_id=organization_id,
                    actor_user_id=actor.id,
                    details={
                        "shipment_id": str(shipment.id),
                        "tracking_number": shipment.tracking_number,
                        "pod_id": str(pod.id),
                        "evidence_id": str(failed.id),
                        "evidence_type": evidence_type,
                        "content_type": payload.content_type,
                        "size_bytes": payload.size_bytes,
                        "reason": "storage_unavailable",
                    },
                )
                self.db.commit()
            raise StorageUnavailableAPIError() from None

        refreshed = self.evidence.get_by_id(row.id)
        assert refreshed is not None
        return refreshed, signed

    def complete_upload(
        self,
        shipment_id: UUID,
        organization_id: UUID,
        actor: User,
        upload_id: UUID,
    ) -> PodEvidence:
        row = self._load_evidence(shipment_id, organization_id, upload_id)
        if row.status == PodEvidenceStatus.UPLOADED.value:
            return row
        if row.status == PodEvidenceStatus.EXPIRED.value:
            raise PodEvidenceExpiredError()
        if row.status == PodEvidenceStatus.FAILED.value:
            raise PodEvidenceUploadFailedError()

        object_key = row.object_key
        expected_type = row.content_type
        declared_size = row.size_bytes
        max_bytes = _max_bytes_for_type(row.evidence_type)
        evidence_id = row.id
        shipment_tracking = None
        shipment = self.shipments.get_for_organization(shipment_id, organization_id)
        if shipment is not None:
            shipment_tracking = shipment.tracking_number
        pod_id = row.pod_id
        evidence_type = row.evidence_type
        content_type = row.content_type

        self.db.commit()

        try:
            meta = self.storage.head_object(object_key)
        except StorageUnavailableError:
            raise StorageUnavailableAPIError() from None

        locked = self.evidence.get_for_organization_for_update(evidence_id, organization_id)
        if locked is None:
            raise NotFoundError("Proof of delivery not found.")
        if locked.status == PodEvidenceStatus.UPLOADED.value:
            self.db.commit()
            return locked
        if locked.status == PodEvidenceStatus.EXPIRED.value:
            self.db.commit()
            raise PodEvidenceExpiredError()
        if locked.status == PodEvidenceStatus.FAILED.value:
            self.db.commit()
            raise PodEvidenceUploadFailedError()

        failure_reason = None
        if meta is None:
            failure_reason = "object_missing"
        elif meta.key != object_key:
            failure_reason = "object_key_mismatch"
        elif meta.size_bytes < 1 or meta.size_bytes > max_bytes or meta.size_bytes > declared_size:
            failure_reason = "object_size_invalid"
        elif meta.content_type and meta.content_type.split(";")[0].strip().lower() != expected_type:
            failure_reason = "object_content_type_invalid"
        else:
            try:
                prefix = self.storage.get_object_prefix(object_key, PREFIX_BYTES)
            except StorageUnavailableError:
                raise StorageUnavailableAPIError() from None
            if prefix is None or not content_matches_declared_type(prefix, expected_type):
                failure_reason = "object_magic_invalid"

        if failure_reason:
            locked.status = PodEvidenceStatus.FAILED.value
            self.audit.record(
                action="POD_EVIDENCE_UPLOAD_FAILED",
                resource_type="pod_evidence",
                resource_id=locked.id,
                organization_id=organization_id,
                actor_user_id=actor.id,
                details={
                    "shipment_id": str(shipment_id),
                    "tracking_number": shipment_tracking,
                    "pod_id": str(pod_id),
                    "evidence_id": str(locked.id),
                    "evidence_type": evidence_type,
                    "content_type": content_type,
                    "size_bytes": declared_size,
                    "reason": failure_reason,
                },
            )
            self.db.commit()
            raise PodEvidenceUploadFailedError()

        locked.status = PodEvidenceStatus.UPLOADED.value
        locked.uploaded_at = datetime.now(timezone.utc)
        try:
            self.audit.record(
                action="POD_EVIDENCE_UPLOADED",
                resource_type="pod_evidence",
                resource_id=locked.id,
                organization_id=organization_id,
                actor_user_id=actor.id,
                details={
                    "shipment_id": str(shipment_id),
                    "tracking_number": shipment_tracking,
                    "pod_id": str(pod_id),
                    "evidence_id": str(locked.id),
                    "evidence_type": evidence_type,
                    "content_type": content_type,
                    "size_bytes": meta.size_bytes if meta else declared_size,
                },
            )
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            existing = self.evidence.get_uploaded_for_type(pod_id, evidence_type)
            if existing is not None and existing.id != evidence_id:
                raise PodEvidenceAlreadyUploadedError() from None
            raise PodEvidenceAlreadyUploadedError() from None

        completed = self.evidence.get_by_id(evidence_id)
        assert completed is not None
        return completed

    def create_download_url(
        self,
        shipment_id: UUID,
        organization_id: UUID,
        actor: User,
        evidence_id: UUID,
    ):
        row = self._load_evidence(shipment_id, organization_id, evidence_id)
        if row.status == PodEvidenceStatus.EXPIRED.value:
            raise PodEvidenceExpiredError()
        if row.status != PodEvidenceStatus.UPLOADED.value:
            raise PodEvidenceNotReadyError()

        shipment = self.shipments.get_for_organization(shipment_id, organization_id)
        tracking_number = shipment.tracking_number if shipment is not None else None
        self.audit.record(
            action="POD_EVIDENCE_DOWNLOAD_REQUESTED",
            resource_type="pod_evidence",
            resource_id=row.id,
            organization_id=organization_id,
            actor_user_id=actor.id,
            details={
                "shipment_id": str(shipment_id),
                "tracking_number": tracking_number,
                "pod_id": str(row.pod_id),
                "evidence_id": str(row.id),
                "evidence_type": row.evidence_type,
                "content_type": row.content_type,
                "size_bytes": row.size_bytes,
            },
        )
        self.db.commit()

        try:
            signed = self.storage.create_download_url(
                row.object_key,
                settings.pod_download_url_ttl_seconds,
            )
        except StorageUnavailableError:
            raise StorageUnavailableAPIError() from None
        return row, signed
