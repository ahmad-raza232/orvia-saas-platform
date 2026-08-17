from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    NotFoundError,
    PodAlreadyExistsError,
    PodNotAllowedError,
)
from app.models.proof_of_delivery import ProofOfDelivery
from app.models.shipment import ShipmentStatus
from app.models.user import User
from app.repositories.pod_repository import ProofOfDeliveryRepository
from app.repositories.shipment_repository import ShipmentRepository
from app.schemas.pod import CreateProofOfDeliveryRequest, PodFileMetadata
from app.services.audit_service import AuditService
from app.services.outbox_publisher import OutboxPublisher


def _metadata_columns(prefix: str, metadata: PodFileMetadata | None) -> dict:
    if metadata is None:
        return {
            f"{prefix}_file_name": None,
            f"{prefix}_mime_type": None,
            f"{prefix}_storage_key": None,
            f"{prefix}_url": None,
            f"{prefix}_file_size": None,
            f"{prefix}_checksum": None,
        }
    return {
        f"{prefix}_file_name": metadata.file_name,
        f"{prefix}_mime_type": metadata.mime_type,
        f"{prefix}_storage_key": metadata.storage_key,
        f"{prefix}_url": metadata.url,
        f"{prefix}_file_size": metadata.file_size,
        f"{prefix}_checksum": metadata.checksum,
    }


class ProofOfDeliveryService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.pods = ProofOfDeliveryRepository(db)
        self.shipments = ShipmentRepository(db)
        self.audit = AuditService(db)
        self.outbox = OutboxPublisher(db)

    def get_for_organization(self, shipment_id: UUID, organization_id: UUID) -> ProofOfDelivery:
        shipment = self.shipments.get_for_organization(shipment_id, organization_id)
        if shipment is None:
            raise NotFoundError("Shipment not found.")
        pod = self.pods.get_for_organization(shipment.id, organization_id)
        if pod is None:
            raise NotFoundError("Proof of delivery not found.")
        return pod

    def create(
        self,
        shipment_id: UUID,
        organization_id: UUID,
        actor: User,
        payload: CreateProofOfDeliveryRequest,
    ) -> ProofOfDelivery:
        shipment = self.shipments.get_for_organization_for_update(shipment_id, organization_id)
        if shipment is None:
            raise NotFoundError("Shipment not found.")
        if shipment.status != ShipmentStatus.DELIVERED.value:
            raise PodNotAllowedError()
        if self.pods.get_by_shipment_id(shipment.id) is not None:
            raise PodAlreadyExistsError()

        delivered_at = shipment.delivered_at or datetime.now(timezone.utc)
        pod = ProofOfDelivery(
            organization_id=organization_id,
            shipment_id=shipment.id,
            recipient_name=payload.recipient_name,
            delivery_note=payload.delivery_note,
            delivered_at=delivered_at,
            recorded_by_user_id=actor.id,
            rider_id=shipment.rider_id,
            **_metadata_columns("signature", payload.signature),
            **_metadata_columns("photo", payload.photo),
        )
        self.pods.create(pod)
        rider_code = shipment.rider.rider_code if shipment.rider else None
        self.audit.record(
            action="POD_CREATED",
            resource_type="proof_of_delivery",
            resource_id=pod.id,
            organization_id=organization_id,
            actor_user_id=actor.id,
            details={
                "shipment_id": str(shipment.id),
                "tracking_number": shipment.tracking_number,
                "rider_code": rider_code,
                "recipient_name": payload.recipient_name,
            },
        )
        self.outbox.publish_pod_created(
            organization_id=organization_id,
            shipment=shipment,
            pod_id=pod.id,
            actor_user_id=actor.id,
        )
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise PodAlreadyExistsError() from None
        created = self.pods.get_by_shipment_id(shipment.id)
        assert created is not None
        return created
