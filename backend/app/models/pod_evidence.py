import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class PodEvidenceType(str, enum.Enum):
    SIGNATURE = "SIGNATURE"
    DELIVERY_PHOTO = "DELIVERY_PHOTO"


class PodEvidenceStatus(str, enum.Enum):
    PENDING = "PENDING"
    UPLOADED = "UPLOADED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class PodEvidence(Base):
    __tablename__ = "pod_evidence"
    __table_args__ = (
        CheckConstraint(
            "evidence_type IN ('SIGNATURE', 'DELIVERY_PHOTO')",
            name="ck_pod_evidence_type",
        ),
        CheckConstraint(
            "status IN ('PENDING', 'UPLOADED', 'FAILED', 'EXPIRED')",
            name="ck_pod_evidence_status",
        ),
        CheckConstraint("size_bytes >= 1", name="ck_pod_evidence_size_positive"),
        Index("ix_pod_evidence_organization_id", "organization_id"),
        Index("ix_pod_evidence_pod_id", "pod_id"),
        Index("ix_pod_evidence_shipment_id", "shipment_id"),
        Index("ix_pod_evidence_status", "status"),
        Index("ix_pod_evidence_created_at", "created_at"),
        Index("ix_pod_evidence_status_created_at", "status", "created_at"),
        Index(
            "uq_pod_evidence_uploaded_type",
            "pod_id",
            "evidence_type",
            unique=True,
            postgresql_where=text("status = 'UPLOADED'"),
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
    pod_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("proof_of_deliveries.id", ondelete="RESTRICT"),
        nullable=False,
    )
    shipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shipments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    evidence_type: Mapped[str] = mapped_column(String(32), nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    uploaded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    pod = relationship("ProofOfDelivery", back_populates="evidence")
