import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class ShipmentStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    BOOKED = "BOOKED"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class ServiceType(str, enum.Enum):
    STANDARD = "STANDARD"
    EXPRESS = "EXPRESS"
    SAME_DAY = "SAME_DAY"


class Shipment(Base):
    __tablename__ = "shipments"
    __table_args__ = (
        CheckConstraint("weight_kg > 0", name="ck_shipments_weight_positive"),
        CheckConstraint("quantity >= 1", name="ck_shipments_quantity_min"),
        CheckConstraint(
            "length_cm IS NULL OR length_cm >= 0",
            name="ck_shipments_length_non_negative",
        ),
        CheckConstraint(
            "width_cm IS NULL OR width_cm >= 0",
            name="ck_shipments_width_non_negative",
        ),
        CheckConstraint(
            "height_cm IS NULL OR height_cm >= 0",
            name="ck_shipments_height_non_negative",
        ),
        CheckConstraint(
            "cod_amount IS NULL OR cod_amount >= 0",
            name="ck_shipments_cod_non_negative",
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'BOOKED', 'PICKED_UP', 'IN_TRANSIT', "
            "'OUT_FOR_DELIVERY', 'DELIVERED', 'CANCELLED')",
            name="ck_shipments_status",
        ),
        CheckConstraint(
            "service_type IN ('STANDARD', 'EXPRESS', 'SAME_DAY')",
            name="ck_shipments_service_type",
        ),
        Index("ix_shipments_organization_id", "organization_id"),
        Index("ix_shipments_org_reference", "organization_id", "reference_number"),
        Index("ix_shipments_org_status", "organization_id", "status"),
        Index("ix_shipments_org_created_at", "organization_id", "created_at"),
        Index("uq_shipments_tracking_number", "tracking_number", unique=True),
        Index("ix_shipments_org_tracking", "organization_id", "tracking_number"),
        Index("ix_shipments_org_customer", "organization_id", "customer_id"),
        Index("ix_shipments_org_rider", "organization_id", "rider_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    tracking_number: Mapped[str] = mapped_column(String(32), nullable=False)
    reference_number: Mapped[str | None] = mapped_column(String(80), nullable=True)

    sender_name: Mapped[str] = mapped_column(String(120), nullable=False)
    sender_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    sender_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sender_address: Mapped[str] = mapped_column(String(255), nullable=False)
    sender_city: Mapped[str] = mapped_column(String(80), nullable=False)
    sender_state: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sender_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    sender_postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    receiver_name: Mapped[str] = mapped_column(String(120), nullable=False)
    receiver_phone: Mapped[str] = mapped_column(String(32), nullable=False)
    receiver_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    receiver_address: Mapped[str] = mapped_column(String(255), nullable=False)
    receiver_city: Mapped[str] = mapped_column(String(80), nullable=False)
    receiver_state: Mapped[str | None] = mapped_column(String(80), nullable=True)
    receiver_country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    receiver_postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)

    weight_kg: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    length_cm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    width_cm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    package_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    service_type: Mapped[str] = mapped_column(String(32), nullable=False, default=ServiceType.STANDARD.value)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=ShipmentStatus.BOOKED.value)

    cod_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    pickup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    picked_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    in_transit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    out_for_delivery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    rider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("riders.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    status_history = relationship(
        "ShipmentStatusHistory",
        back_populates="shipment",
        order_by="ShipmentStatusHistory.created_at",
    )
    customer = relationship("Customer", back_populates="shipments")
    rider = relationship("Rider", back_populates="shipments")
    rider_assignments = relationship(
        "ShipmentRiderAssignment",
        back_populates="shipment",
        order_by="ShipmentRiderAssignment.assigned_at",
    )
    proof_of_delivery = relationship(
        "ProofOfDelivery",
        back_populates="shipment",
        uselist=False,
    )


class ShipmentStatusHistory(Base):
    __tablename__ = "shipment_status_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    shipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shipments.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    previous_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_status: Mapped[str] = mapped_column(String(32), nullable=False)
    changed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    shipment = relationship("Shipment", back_populates="status_history")
