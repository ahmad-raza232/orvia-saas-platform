from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.customer_codes import generate_customer_code
from app.core.exceptions import DuplicateCustomerEmailError, NotFoundError
from app.models.customer import Customer, CustomerStatus
from app.models.shipment import Shipment, ShipmentStatus
from app.models.user import User
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import CreateCustomerRequest, UpdateCustomerRequest
from app.services.audit_service import AuditService

ACTIVE_SHIPMENT_STATUSES = (
    ShipmentStatus.DRAFT.value,
    ShipmentStatus.BOOKED.value,
    ShipmentStatus.PICKED_UP.value,
    ShipmentStatus.IN_TRANSIT.value,
    ShipmentStatus.OUT_FOR_DELIVERY.value,
)


class CustomerService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.customers = CustomerRepository(db)
        self.audit = AuditService(db)

    def _unique_code(self, organization_id: UUID) -> str:
        for _ in range(8):
            candidate = generate_customer_code()
            if self.customers.get_by_code(organization_id, candidate) is None:
                return candidate
        raise RuntimeError("Unable to allocate a unique customer code")

    def get_for_organization(self, customer_id: UUID, organization_id: UUID) -> Customer:
        customer = self.customers.get_for_organization(customer_id, organization_id)
        if customer is None:
            raise NotFoundError("Customer not found.")
        return customer

    def create(
        self, organization_id: UUID, actor: User, payload: CreateCustomerRequest
    ) -> Customer:
        if payload.email and self.customers.get_by_email(organization_id, payload.email):
            raise DuplicateCustomerEmailError()
        customer = Customer(
            organization_id=organization_id,
            customer_code=self._unique_code(organization_id),
            name=payload.name,
            email=payload.email,
            phone=payload.phone,
            alternate_phone=payload.alternate_phone,
            company_name=payload.company_name,
            address=payload.address,
            city=payload.city,
            state=payload.state,
            country=payload.country,
            postal_code=payload.postal_code,
            notes=payload.notes,
            status=CustomerStatus.ACTIVE.value,
            created_by_user_id=actor.id,
        )
        self.customers.create(customer)
        self.audit.record(
            action="CUSTOMER_CREATED",
            resource_type="customer",
            resource_id=customer.id,
            organization_id=organization_id,
            actor_user_id=actor.id,
            details={"customer_code": customer.customer_code},
        )
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateCustomerEmailError() from exc
        self.db.refresh(customer)
        return customer

    def update(
        self,
        customer_id: UUID,
        organization_id: UUID,
        actor: User,
        payload: UpdateCustomerRequest,
    ) -> Customer:
        customer = self.get_for_organization(customer_id, organization_id)
        provided = payload.model_dump(exclude_unset=True)
        if "email" in provided and payload.email:
            other = self.customers.get_by_email(organization_id, payload.email)
            if other and other.id != customer.id:
                raise DuplicateCustomerEmailError()
        for field, value in provided.items():
            setattr(customer, field, str(value) if field == "email" and value else value)
        customer.updated_at = datetime.now(timezone.utc)
        self.audit.record(
            action="CUSTOMER_UPDATED",
            resource_type="customer",
            resource_id=customer.id,
            organization_id=organization_id,
            actor_user_id=actor.id,
            details={"fields": sorted(provided.keys())},
        )
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateCustomerEmailError() from exc
        self.db.refresh(customer)
        return customer

    def deactivate(self, customer_id: UUID, organization_id: UUID, actor: User) -> Customer:
        customer = self.get_for_organization(customer_id, organization_id)
        if customer.status != CustomerStatus.INACTIVE.value:
            customer.status = CustomerStatus.INACTIVE.value
            customer.updated_at = datetime.now(timezone.utc)
            self.audit.record(
                action="CUSTOMER_DEACTIVATED",
                resource_type="customer",
                resource_id=customer.id,
                organization_id=organization_id,
                actor_user_id=actor.id,
                details={"customer_code": customer.customer_code},
            )
            self.db.commit()
            self.db.refresh(customer)
        return customer

    def reactivate(self, customer_id: UUID, organization_id: UUID, actor: User) -> Customer:
        customer = self.get_for_organization(customer_id, organization_id)
        if customer.status != CustomerStatus.ACTIVE.value:
            customer.status = CustomerStatus.ACTIVE.value
            customer.updated_at = datetime.now(timezone.utc)
            self.audit.record(
                action="CUSTOMER_REACTIVATED",
                resource_type="customer",
                resource_id=customer.id,
                organization_id=organization_id,
                actor_user_id=actor.id,
                details={"customer_code": customer.customer_code},
            )
            self.db.commit()
            self.db.refresh(customer)
        return customer

    def list_for_organization(self, organization_id: UUID, **filters):
        return self.customers.list_for_organization(organization_id, **filters)

    def shipment_summary(self, customer_id: UUID, organization_id: UUID) -> dict:
        base = self.db.query(Shipment).filter(
            Shipment.organization_id == organization_id,
            Shipment.customer_id == customer_id,
        )
        shipment_count = base.with_entities(func.count(Shipment.id)).scalar() or 0
        active_shipment_count = (
            base.filter(Shipment.status.in_(ACTIVE_SHIPMENT_STATUSES))
            .with_entities(func.count(Shipment.id))
            .scalar()
            or 0
        )
        latest = base.with_entities(func.max(Shipment.created_at)).scalar()
        return {
            "shipment_count": int(shipment_count),
            "active_shipment_count": int(active_shipment_count),
            "latest_shipment_at": latest,
        }
