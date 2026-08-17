from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    NotFoundError,
    ShipmentInvalidTransitionError,
    ShipmentNotCancellableError,
)
from app.models.shipment import Shipment, ShipmentStatus, ShipmentStatusHistory
from app.models.user import User
from app.repositories.shipment_repository import ShipmentRepository
from app.services.audit_service import AuditService
from app.services.outbox_publisher import OutboxPublisher

S = ShipmentStatus

OPERATIONAL_TRANSITIONS: dict[str, set[str]] = {
    S.DRAFT.value: {S.BOOKED.value},
    S.BOOKED.value: {S.PICKED_UP.value},
    S.PICKED_UP.value: {S.IN_TRANSIT.value},
    S.IN_TRANSIT.value: {S.OUT_FOR_DELIVERY.value},
    S.OUT_FOR_DELIVERY.value: {S.DELIVERED.value},
}

CANCEL_TRANSITIONS: dict[str, set[str]] = {
    S.DRAFT.value: {S.CANCELLED.value},
    S.BOOKED.value: {S.CANCELLED.value},
}

STATUS_TIMESTAMPS = {
    S.PICKED_UP.value: "picked_up_at",
    S.IN_TRANSIT.value: "in_transit_at",
    S.OUT_FOR_DELIVERY.value: "out_for_delivery_at",
    S.DELIVERED.value: "delivered_at",
    S.CANCELLED.value: "cancelled_at",
}


class ShipmentStatusTransitionService:
    """Single status-change path for operational transitions and cancellation."""

    def __init__(self, db: Session, shipments: ShipmentRepository, audit: AuditService) -> None:
        self.db = db
        self.shipments = shipments
        self.audit = audit
        self.outbox = OutboxPublisher(db)

    def change_status(
        self,
        shipment_id: UUID,
        organization_id: UUID,
        actor: User,
        new_status: str,
        note: str | None = None,
    ) -> Shipment:
        return self._transition(
            shipment_id,
            organization_id,
            actor,
            new_status,
            note,
            allowed=OPERATIONAL_TRANSITIONS,
            emit_cancelled_audit=False,
        )

    def cancel(
        self,
        shipment_id: UUID,
        organization_id: UUID,
        actor: User,
        note: str | None = None,
    ) -> Shipment:
        return self._transition(
            shipment_id,
            organization_id,
            actor,
            ShipmentStatus.CANCELLED.value,
            note or "Shipment cancelled",
            allowed=CANCEL_TRANSITIONS,
            emit_cancelled_audit=True,
        )

    def _transition(
        self,
        shipment_id: UUID,
        organization_id: UUID,
        actor: User,
        new_status: str,
        note: str | None,
        *,
        allowed: dict[str, set[str]],
        emit_cancelled_audit: bool,
    ) -> Shipment:
        shipment = self.shipments.get_for_organization_for_update(shipment_id, organization_id)
        if shipment is None:
            raise NotFoundError("Shipment not found.")

        current = shipment.status
        if current == new_status:
            raise ShipmentInvalidTransitionError(current, new_status)
        if new_status not in allowed.get(current, set()):
            if emit_cancelled_audit:
                raise ShipmentNotCancellableError()
            raise ShipmentInvalidTransitionError(current, new_status)

        now = datetime.now(timezone.utc)
        shipment.status = new_status
        shipment.updated_at = now
        self._stamp(shipment, new_status, now)
        self.shipments.add_history(
            ShipmentStatusHistory(
                shipment_id=shipment.id,
                previous_status=current,
                new_status=new_status,
                changed_by_user_id=actor.id,
                note=note,
            )
        )
        details = {
            "tracking_number": shipment.tracking_number,
            "from": current,
            "to": new_status,
        }
        if emit_cancelled_audit:
            self.audit.record(
                action="SHIPMENT_CANCELLED",
                resource_type="shipment",
                resource_id=shipment.id,
                organization_id=organization_id,
                actor_user_id=actor.id,
                details=details,
            )
        self.audit.record(
            action="SHIPMENT_STATUS_CHANGED",
            resource_type="shipment",
            resource_id=shipment.id,
            organization_id=organization_id,
            actor_user_id=actor.id,
            details=details,
        )
        self.outbox.publish_shipment_status(shipment, actor.id)
        self.db.commit()
        reloaded = self.shipments.get_by_id(shipment.id)
        assert reloaded is not None
        return reloaded

    def _stamp(self, shipment: Shipment, new_status: str, now: datetime) -> None:
        column = STATUS_TIMESTAMPS.get(new_status)
        if column and getattr(shipment, column) is None:
            setattr(shipment, column, now)
