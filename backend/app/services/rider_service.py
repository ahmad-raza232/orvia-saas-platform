from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.rider_codes import generate_rider_code
from app.models.rider import Rider, RiderStatus
from app.models.shipment import Shipment, ShipmentStatus
from app.models.user import User
from app.repositories.rider_repository import RiderRepository
from app.schemas.rider import CreateRiderRequest, UpdateRiderRequest
from app.services.audit_service import AuditService


class RiderService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.riders = RiderRepository(db)
        self.audit = AuditService(db)

    def _unique_code(self, organization_id: UUID) -> str:
        for _ in range(8):
            candidate = generate_rider_code()
            if self.riders.get_by_code(organization_id, candidate) is None:
                return candidate
        raise RuntimeError("Unable to allocate a unique rider code")

    def get_for_organization(self, rider_id: UUID, organization_id: UUID) -> Rider:
        rider = self.riders.get_for_organization(rider_id, organization_id)
        if rider is None:
            raise NotFoundError("Rider not found.")
        return rider

    def create(self, organization_id: UUID, actor: User, payload: CreateRiderRequest) -> Rider:
        rider = Rider(
            organization_id=organization_id,
            rider_code=self._unique_code(organization_id),
            name=payload.name,
            phone=payload.phone,
            email=payload.email,
            vehicle_type=payload.vehicle_type.value if payload.vehicle_type else None,
            vehicle_number=payload.vehicle_number,
            notes=payload.notes,
            status=RiderStatus.ACTIVE.value,
            created_by_user_id=actor.id,
        )
        self.riders.create(rider)
        self.audit.record(
            action="RIDER_CREATED",
            resource_type="rider",
            resource_id=rider.id,
            organization_id=organization_id,
            actor_user_id=actor.id,
            details={"rider_code": rider.rider_code},
        )
        self.db.commit()
        self.db.refresh(rider)
        return rider

    def update(
        self,
        rider_id: UUID,
        organization_id: UUID,
        actor: User,
        payload: UpdateRiderRequest,
    ) -> Rider:
        rider = self.get_for_organization(rider_id, organization_id)
        provided = payload.model_dump(exclude_unset=True)
        if "vehicle_type" in provided:
            provided["vehicle_type"] = payload.vehicle_type.value if payload.vehicle_type else None
        if "email" in provided:
            provided["email"] = str(payload.email) if payload.email else None
        for field, value in provided.items():
            setattr(rider, field, value)
        rider.updated_at = datetime.now(timezone.utc)
        self.audit.record(
            action="RIDER_UPDATED",
            resource_type="rider",
            resource_id=rider.id,
            organization_id=organization_id,
            actor_user_id=actor.id,
            details={"fields": sorted(provided.keys()), "rider_code": rider.rider_code},
        )
        self.db.commit()
        self.db.refresh(rider)
        return rider

    def deactivate(self, rider_id: UUID, organization_id: UUID, actor: User) -> Rider:
        rider = self.get_for_organization(rider_id, organization_id)
        if rider.status != RiderStatus.INACTIVE.value:
            rider.status = RiderStatus.INACTIVE.value
            rider.updated_at = datetime.now(timezone.utc)
            self.audit.record(
                action="RIDER_DEACTIVATED",
                resource_type="rider",
                resource_id=rider.id,
                organization_id=organization_id,
                actor_user_id=actor.id,
                details={"rider_code": rider.rider_code},
            )
            self.db.commit()
            self.db.refresh(rider)
        return rider

    def reactivate(self, rider_id: UUID, organization_id: UUID, actor: User) -> Rider:
        rider = self.get_for_organization(rider_id, organization_id)
        if rider.status != RiderStatus.ACTIVE.value:
            rider.status = RiderStatus.ACTIVE.value
            rider.updated_at = datetime.now(timezone.utc)
            self.audit.record(
                action="RIDER_REACTIVATED",
                resource_type="rider",
                resource_id=rider.id,
                organization_id=organization_id,
                actor_user_id=actor.id,
                details={"rider_code": rider.rider_code},
            )
            self.db.commit()
            self.db.refresh(rider)
        return rider

    def list_for_organization(self, organization_id: UUID, **filters):
        return self.riders.list_for_organization(organization_id, **filters)

    def assignment_summary(self, rider_id: UUID, organization_id: UUID) -> dict:
        base = self.db.query(Shipment).filter(
            Shipment.organization_id == organization_id,
            Shipment.rider_id == rider_id,
        )
        assigned = base.with_entities(func.count(Shipment.id)).scalar() or 0
        out_for_delivery = (
            base.filter(Shipment.status == ShipmentStatus.OUT_FOR_DELIVERY.value)
            .with_entities(func.count(Shipment.id))
            .scalar()
            or 0
        )
        return {
            "assigned_shipment_count": int(assigned),
            "out_for_delivery_count": int(out_for_delivery),
        }
