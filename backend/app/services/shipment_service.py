from datetime import datetime, timezone
from uuid import UUID

from fastapi import status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    APIError,
    CustomerInactiveError,
    NotFoundError,
    ShipmentNotEditableError,
)
from app.core.tracking import generate_tracking_number
from app.models.customer import Customer, CustomerStatus
from app.models.shipment import Shipment, ShipmentStatus, ShipmentStatusHistory
from app.models.user import User
from app.repositories.customer_repository import CustomerRepository
from app.repositories.rider_repository import RiderRepository
from app.repositories.shipment_repository import ShipmentRepository
from app.schemas.shipment import CreateShipmentRequest, UpdateShipmentRequest
from app.services.audit_service import AuditService
from app.services.outbox_publisher import OutboxPublisher
from app.services.shipment_assignment import ShipmentAssignmentService
from app.services.shipment_status import ShipmentStatusTransitionService

OPERATIONAL_EDITABLE_STATUSES = {
    ShipmentStatus.PICKED_UP.value,
    ShipmentStatus.IN_TRANSIT.value,
    ShipmentStatus.OUT_FOR_DELIVERY.value,
    ShipmentStatus.DELIVERED.value,
}
BOOKED_ALLOWED_FIELDS = {"notes", "reference_number", "receiver", "customer_id"}
BOOKED_RECEIVER_FIELDS = {"phone", "email"}
OPERATIONAL_ALLOWED_FIELDS = {"notes", "reference_number"}


class ShipmentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.shipments = ShipmentRepository(db)
        self.customers = CustomerRepository(db)
        self.riders = RiderRepository(db)
        self.audit = AuditService(db)
        self.outbox = OutboxPublisher(db)
        self.status_transitions = ShipmentStatusTransitionService(db, self.shipments, self.audit)
        self.assignments = ShipmentAssignmentService(db, self.shipments, self.riders, self.audit)

    def _resolve_customer(
        self, organization_id: UUID, customer_id: UUID | None, *, current_customer_id: UUID | None = None
    ) -> Customer | None:
        if customer_id is None:
            return None
        customer = self.customers.get_for_organization(customer_id, organization_id)
        if customer is None:
            raise NotFoundError("Customer not found.")
        assigning = current_customer_id != customer_id
        if assigning and customer.status != CustomerStatus.ACTIVE.value:
            raise CustomerInactiveError()
        return customer

    def _unique_tracking_number(self) -> str:
        for _ in range(8):
            candidate = generate_tracking_number()
            if self.shipments.get_by_tracking_number(candidate) is None:
                return candidate
        raise RuntimeError("Unable to allocate a unique tracking number")

    def get_for_organization(self, shipment_id: UUID, organization_id: UUID) -> Shipment:
        shipment = self.shipments.get_for_organization(shipment_id, organization_id)
        if shipment is None:
            raise NotFoundError("Shipment not found.")
        return shipment

    def create(
        self, organization_id: UUID, actor: User, payload: CreateShipmentRequest
    ) -> Shipment:
        shipment = Shipment(
            organization_id=organization_id,
            tracking_number=self._unique_tracking_number(),
            reference_number=payload.reference_number,
            sender_name=payload.sender.name,
            sender_phone=payload.sender.phone,
            sender_email=str(payload.sender.email) if payload.sender.email else None,
            sender_address=payload.sender.address,
            sender_city=payload.sender.city,
            sender_state=payload.sender.state,
            sender_country=payload.sender.country,
            sender_postal_code=payload.sender.postal_code,
            receiver_name=payload.receiver.name,
            receiver_phone=payload.receiver.phone,
            receiver_email=str(payload.receiver.email) if payload.receiver.email else None,
            receiver_address=payload.receiver.address,
            receiver_city=payload.receiver.city,
            receiver_state=payload.receiver.state,
            receiver_country=payload.receiver.country,
            receiver_postal_code=payload.receiver.postal_code,
            weight_kg=payload.parcel.weight_kg,
            length_cm=payload.parcel.length_cm,
            width_cm=payload.parcel.width_cm,
            height_cm=payload.parcel.height_cm,
            package_type=payload.parcel.package_type,
            description=payload.parcel.description,
            quantity=payload.parcel.quantity,
            service_type=payload.service_type.value,
            status=payload.status.value,
            cod_amount=payload.cod_amount,
            currency=payload.currency,
            notes=payload.notes,
            pickup_at=payload.pickup_at,
            created_by_user_id=actor.id,
            customer_id=None,
        )
        customer = self._resolve_customer(organization_id, payload.customer_id)
        if customer is not None:
            shipment.customer_id = customer.id
        self.shipments.create(shipment)
        self.shipments.add_history(
            ShipmentStatusHistory(
                shipment_id=shipment.id,
                previous_status=None,
                new_status=shipment.status,
                changed_by_user_id=actor.id,
                note="Shipment created",
            )
        )
        self.audit.record(
            action="SHIPMENT_CREATED",
            resource_type="shipment",
            resource_id=shipment.id,
            organization_id=organization_id,
            actor_user_id=actor.id,
            details={"tracking_number": shipment.tracking_number, "status": shipment.status},
        )
        if customer is not None:
            self.audit.record(
                action="SHIPMENT_CUSTOMER_ASSIGNED",
                resource_type="shipment",
                resource_id=shipment.id,
                organization_id=organization_id,
                actor_user_id=actor.id,
                details={"customer_id": str(customer.id)},
            )
        if shipment.status == ShipmentStatus.BOOKED.value:
            self.outbox.publish_shipment_status(shipment, actor.id)
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise
        return self.get_for_organization(shipment.id, organization_id)

    def update(
        self,
        shipment_id: UUID,
        organization_id: UUID,
        actor: User,
        payload: UpdateShipmentRequest,
    ) -> Shipment:
        shipment = self.get_for_organization(shipment_id, organization_id)
        if shipment.status == ShipmentStatus.CANCELLED.value:
            raise ShipmentNotEditableError()

        provided = payload.model_dump(exclude_unset=True)
        if shipment.status == ShipmentStatus.BOOKED.value:
            disallowed = set(provided) - BOOKED_ALLOWED_FIELDS
            if disallowed:
                raise ShipmentNotEditableError()
            if "receiver" in provided:
                receiver_fields = set(payload.receiver.model_dump(exclude_unset=True) if payload.receiver else {})
                if receiver_fields - BOOKED_RECEIVER_FIELDS:
                    raise ShipmentNotEditableError()
        elif shipment.status == ShipmentStatus.DRAFT.value:
            pass
        elif shipment.status in OPERATIONAL_EDITABLE_STATUSES:
            if set(provided) - OPERATIONAL_ALLOWED_FIELDS:
                raise ShipmentNotEditableError()
        else:
            raise ShipmentNotEditableError()

        self._apply_update(shipment, payload)
        if shipment.cod_amount is not None and not shipment.currency:
            raise APIError(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "VALIDATION_ERROR",
                "currency is required when cod_amount is set",
            )
        shipment.updated_at = datetime.now(timezone.utc)
        self.audit.record(
            action="SHIPMENT_UPDATED",
            resource_type="shipment",
            resource_id=shipment.id,
            organization_id=organization_id,
            actor_user_id=actor.id,
            details={"fields": sorted(provided.keys())},
        )
        if "customer_id" in provided:
            self.audit.record(
                action="SHIPMENT_CUSTOMER_ASSIGNED",
                resource_type="shipment",
                resource_id=shipment.id,
                organization_id=organization_id,
                actor_user_id=actor.id,
                details={"customer_id": str(shipment.customer_id) if shipment.customer_id else None},
            )
        self.db.commit()
        return self.get_for_organization(shipment.id, organization_id)

    def cancel(
        self,
        shipment_id: UUID,
        organization_id: UUID,
        actor: User,
        note: str | None = None,
    ) -> Shipment:
        return self.status_transitions.cancel(shipment_id, organization_id, actor, note)

    def change_status(
        self,
        shipment_id: UUID,
        organization_id: UUID,
        actor: User,
        new_status: str,
        note: str | None = None,
    ) -> Shipment:
        return self.status_transitions.change_status(
            shipment_id, organization_id, actor, new_status, note
        )

    def list_history(self, shipment_id: UUID, organization_id: UUID) -> list[ShipmentStatusHistory]:
        return list(self.get_for_organization(shipment_id, organization_id).status_history)

    def list_for_organization(self, organization_id: UUID, **filters):
        return self.shipments.list_for_organization(organization_id, **filters)

    def _apply_update(self, shipment: Shipment, payload: UpdateShipmentRequest) -> None:
        if payload.sender is not None:
            data = payload.sender.model_dump(exclude_unset=True)
            for field, value in data.items():
                setattr(shipment, f"sender_{field}", str(value) if field == "email" and value else value)
        if payload.receiver is not None:
            data = payload.receiver.model_dump(exclude_unset=True)
            for field, value in data.items():
                setattr(shipment, f"receiver_{field}", str(value) if field == "email" and value else value)
        if payload.parcel is not None:
            data = payload.parcel.model_dump(exclude_unset=True)
            mapping = {
                "weight_kg": "weight_kg",
                "length_cm": "length_cm",
                "width_cm": "width_cm",
                "height_cm": "height_cm",
                "package_type": "package_type",
                "description": "description",
                "quantity": "quantity",
            }
            for key, column in mapping.items():
                if key in data:
                    setattr(shipment, column, data[key])
        if payload.service_type is not None:
            shipment.service_type = payload.service_type.value
        if "reference_number" in payload.model_dump(exclude_unset=True):
            shipment.reference_number = payload.reference_number
        if "notes" in payload.model_dump(exclude_unset=True):
            shipment.notes = payload.notes
        if "pickup_at" in payload.model_dump(exclude_unset=True):
            shipment.pickup_at = payload.pickup_at
        if "cod_amount" in payload.model_dump(exclude_unset=True):
            shipment.cod_amount = payload.cod_amount
        if "currency" in payload.model_dump(exclude_unset=True):
            shipment.currency = payload.currency
        if "customer_id" in payload.model_dump(exclude_unset=True):
            customer = self._resolve_customer(
                shipment.organization_id,
                payload.customer_id,
                current_customer_id=shipment.customer_id,
            )
            shipment.customer_id = customer.id if customer else None

    def list_for_customer(self, organization_id: UUID, customer_id: UUID, **filters):
        return self.shipments.list_for_customer(organization_id, customer_id, **filters)

    def list_for_rider(self, organization_id: UUID, rider_id: UUID, **filters):
        return self.shipments.list_for_rider(organization_id, rider_id, **filters)

    def assign_rider(self, shipment_id: UUID, organization_id: UUID, actor: User, rider_id: UUID, note: str | None = None):
        return self.assignments.assign(shipment_id, organization_id, actor, rider_id, note)

    def unassign_rider(self, shipment_id: UUID, organization_id: UUID, actor: User, note: str | None = None):
        return self.assignments.unassign(shipment_id, organization_id, actor, note)

    def list_rider_history(self, shipment_id: UUID, organization_id: UUID):
        return self.assignments.list_history(shipment_id, organization_id)
