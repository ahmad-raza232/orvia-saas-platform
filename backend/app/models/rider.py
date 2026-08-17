import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class RiderStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class VehicleType(str, enum.Enum):
    MOTORCYCLE = "MOTORCYCLE"
    BICYCLE = "BICYCLE"
    CAR = "CAR"
    VAN = "VAN"
    TRUCK = "TRUCK"
    WALKING = "WALKING"
    OTHER = "OTHER"


class Rider(Base):
    __tablename__ = "riders"
    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_riders_status"),
        CheckConstraint(
            "vehicle_type IS NULL OR vehicle_type IN "
            "('MOTORCYCLE', 'BICYCLE', 'CAR', 'VAN', 'TRUCK', 'WALKING', 'OTHER')",
            name="ck_riders_vehicle_type",
        ),
        Index("ix_riders_organization_id", "organization_id"),
        Index("uq_riders_org_code", "organization_id", "rider_code", unique=True),
        Index("ix_riders_org_status", "organization_id", "status"),
        Index("ix_riders_org_created_at", "organization_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    rider_code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vehicle_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    vehicle_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=RiderStatus.ACTIVE.value)
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

    shipments = relationship("Shipment", back_populates="rider")
    assignments = relationship("ShipmentRiderAssignment", back_populates="rider")


class ShipmentRiderAssignment(Base):
    __tablename__ = "shipment_rider_assignments"
    __table_args__ = (
        Index("ix_assignments_org_shipment", "organization_id", "shipment_id"),
        Index("ix_assignments_org_rider", "organization_id", "rider_id"),
        Index(
            "uq_assignments_active_shipment",
            "shipment_id",
            unique=True,
            postgresql_where=text("unassigned_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    shipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shipments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    rider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("riders.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    unassigned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    unassigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    shipment = relationship("Shipment", back_populates="rider_assignments")
    rider = relationship("Rider", back_populates="assignments")
