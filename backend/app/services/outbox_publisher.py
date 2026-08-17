from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.events import (
    AGGREGATE_PROOF_OF_DELIVERY,
    AGGREGATE_SHIPMENT,
    POD_CREATED,
    SENSITIVE_PAYLOAD_KEYS,
    STATUS_TO_EVENT,
)
from app.models.shipment import Shipment
from app.repositories.outbox_repository import OutboxRepository


def _safe_payload(payload: dict) -> dict:
    cleaned = {}
    for key, value in payload.items():
        lowered = key.lower()
        if lowered in SENSITIVE_PAYLOAD_KEYS or any(
            part in lowered for part in ("address", "password", "token", "secret", "storage")
        ):
            continue
        cleaned[key] = value
    return cleaned


class OutboxPublisher:
    """Writes domain events into the transactional outbox. Does not send email."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.outbox = OutboxRepository(db)

    def publish_shipment_status(
        self,
        shipment: Shipment,
        actor_user_id: UUID | None,
        event_type: str | None = None,
    ) -> None:
        resolved = event_type or STATUS_TO_EVENT.get(shipment.status)
        if resolved is None:
            return
        occurred_at = datetime.now(timezone.utc)
        delivered_at = shipment.delivered_at.isoformat() if shipment.delivered_at else None
        payload = _safe_payload(
            {
                "organization_id": str(shipment.organization_id),
                "event_type": resolved,
                "shipment_id": str(shipment.id),
                "tracking_number": shipment.tracking_number,
                "occurred_at": occurred_at.isoformat(),
                "actor_user_id": str(actor_user_id) if actor_user_id else None,
                "status": shipment.status,
                "customer_id": str(shipment.customer_id) if shipment.customer_id else None,
                "delivered_at": delivered_at,
            }
        )
        self.outbox.enqueue(
            organization_id=shipment.organization_id,
            event_type=resolved,
            aggregate_type=AGGREGATE_SHIPMENT,
            aggregate_id=shipment.id,
            payload=payload,
            available_at=occurred_at,
        )

    def publish_pod_created(
        self,
        *,
        organization_id: UUID,
        shipment: Shipment,
        pod_id: UUID,
        actor_user_id: UUID | None,
    ) -> None:
        occurred_at = datetime.now(timezone.utc)
        delivered_at = shipment.delivered_at.isoformat() if shipment.delivered_at else None
        payload = _safe_payload(
            {
                "organization_id": str(organization_id),
                "event_type": POD_CREATED,
                "shipment_id": str(shipment.id),
                "tracking_number": shipment.tracking_number,
                "occurred_at": occurred_at.isoformat(),
                "actor_user_id": str(actor_user_id) if actor_user_id else None,
                "status": shipment.status,
                "customer_id": str(shipment.customer_id) if shipment.customer_id else None,
                "pod_id": str(pod_id),
                "delivered_at": delivered_at,
            }
        )
        self.outbox.enqueue(
            organization_id=organization_id,
            event_type=POD_CREATED,
            aggregate_type=AGGREGATE_PROOF_OF_DELIVERY,
            aggregate_id=pod_id,
            payload=payload,
            available_at=occurred_at,
        )
