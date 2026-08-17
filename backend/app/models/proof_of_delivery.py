import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.pod_evidence import PodEvidence  # noqa: F401


class ProofOfDelivery(Base):
    __tablename__ = "proof_of_deliveries"
    __table_args__ = (
        Index("ix_pod_organization_id", "organization_id"),
        Index("uq_pod_shipment_id", "shipment_id", unique=True),
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
    recipient_name: Mapped[str] = mapped_column(String(120), nullable=False)
    delivery_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    rider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("riders.id", ondelete="RESTRICT"),
        nullable=True,
    )

    signature_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    signature_mime_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    signature_storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    signature_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    signature_file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    signature_checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)

    photo_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    photo_mime_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    photo_storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    photo_file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    photo_checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    shipment = relationship("Shipment", back_populates="proof_of_delivery")
    rider = relationship("Rider")
    evidence = relationship(
        "PodEvidence",
        back_populates="pod",
        order_by="PodEvidence.created_at",
    )
