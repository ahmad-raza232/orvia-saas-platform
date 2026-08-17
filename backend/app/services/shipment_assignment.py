from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    NotFoundError,
    RiderAlreadyAssignedError,
    RiderInactiveError,
    RiderNotAssignedError,
    ShipmentNotAssignableError,
    ShipmentNotUnassignableError,
)
from app.models.rider import RiderStatus, ShipmentRiderAssignment
from app.models.shipment import Shipment, ShipmentStatus
from app.models.user import User
from app.repositories.rider_repository import RiderRepository
from app.repositories.shipment_repository import ShipmentRepository
from app.services.audit_service import AuditService

ASSIGNABLE_STATUSES = {ShipmentStatus.OUT_FOR_DELIVERY.value}
UNASSIGNABLE_STATUSES = {ShipmentStatus.OUT_FOR_DELIVERY.value}


class ShipmentAssignmentService:
    """Current rider_id plus append-only assignment history, in one transaction."""

    def __init__(
        self,
        db: Session,
        shipments: ShipmentRepository,
        riders: RiderRepository,
        audit: AuditService,
    ) -> None:
        self.db = db
        self.shipments = shipments
        self.riders = riders
        self.audit = audit

    def assign(
        self,
        shipment_id: UUID,
        organization_id: UUID,
        actor: User,
        rider_id: UUID,
        note: str | None = None,
    ) -> Shipment:
        shipment = self.shipments.get_for_organization_for_update(shipment_id, organization_id)
        if shipment is None:
            raise NotFoundError("Shipment not found.")
        if shipment.status not in ASSIGNABLE_STATUSES:
            raise ShipmentNotAssignableError()

        rider = self.riders.get_for_organization(rider_id, organization_id)
        if rider is None:
            raise NotFoundError("Rider not found.")
        if rider.status != RiderStatus.ACTIVE.value:
            raise RiderInactiveError()
        if shipment.rider_id == rider.id:
            raise RiderAlreadyAssignedError()

        now = datetime.now(timezone.utc)
        previous_code = None
        active = self.riders.get_active_assignment(shipment.id)
        if active is not None:
            previous = self.riders.get_by_id(active.rider_id)
            previous_code = previous.rider_code if previous else None
            active.unassigned_at = now
            active.unassigned_by_user_id = actor.id
        shipment.rider_id = rider.id
        shipment.updated_at = now
        self.riders.add_assignment(
            ShipmentRiderAssignment(
                organization_id=organization_id,
                shipment_id=shipment.id,
                rider_id=rider.id,
                assigned_by_user_id=actor.id,
                assigned_at=now,
                note=note,
            )
        )
        self.audit.record(
            action="RIDER_ASSIGNED_TO_SHIPMENT",
            resource_type="shipment",
            resource_id=shipment.id,
            organization_id=organization_id,
            actor_user_id=actor.id,
            details={
                "tracking_number": shipment.tracking_number,
                "rider_code": rider.rider_code,
                "previous_rider_code": previous_code,
            },
        )
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise RiderAlreadyAssignedError() from None
        reloaded = self.shipments.get_by_id(shipment.id)
        assert reloaded is not None
        return reloaded

    def unassign(
        self,
        shipment_id: UUID,
        organization_id: UUID,
        actor: User,
        note: str | None = None,
    ) -> Shipment:
        shipment = self.shipments.get_for_organization_for_update(shipment_id, organization_id)
        if shipment is None:
            raise NotFoundError("Shipment not found.")
        if shipment.status not in UNASSIGNABLE_STATUSES:
            raise ShipmentNotUnassignableError()
        if shipment.rider_id is None:
            raise RiderNotAssignedError()

        now = datetime.now(timezone.utc)
        active = self.riders.get_active_assignment(shipment.id)
        rider = self.riders.get_by_id(shipment.rider_id)
        if active is not None:
            active.unassigned_at = now
            active.unassigned_by_user_id = actor.id
            if note:
                active.note = note if not active.note else active.note
        shipment.rider_id = None
        shipment.updated_at = now
        self.audit.record(
            action="RIDER_UNASSIGNED_FROM_SHIPMENT",
            resource_type="shipment",
            resource_id=shipment.id,
            organization_id=organization_id,
            actor_user_id=actor.id,
            details={
                "tracking_number": shipment.tracking_number,
                "rider_code": rider.rider_code if rider else None,
            },
        )
        self.db.commit()
        reloaded = self.shipments.get_by_id(shipment.id)
        assert reloaded is not None
        return reloaded

    def list_history(self, shipment_id: UUID, organization_id: UUID) -> list[ShipmentRiderAssignment]:
        shipment = self.shipments.get_for_organization(shipment_id, organization_id)
        if shipment is None:
            raise NotFoundError("Shipment not found.")
        return self.riders.list_assignments(organization_id, shipment_id)
