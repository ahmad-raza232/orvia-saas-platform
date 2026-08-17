import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.events import DOMAIN_EVENT_TYPES
from app.db.database import Base

OUTBOX_STATUSES = ("PENDING", "PROCESSING", "PROCESSED", "FAILED")
_EVENT_IN = ", ".join(f"'{item}'" for item in DOMAIN_EVENT_TYPES)
_STATUS_IN = ", ".join(f"'{item}'" for item in OUTBOX_STATUSES)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        CheckConstraint(f"status IN ({_STATUS_IN})", name="ck_outbox_events_status"),
        CheckConstraint(f"event_type IN ({_EVENT_IN})", name="ck_outbox_events_event_type"),
        CheckConstraint("attempts >= 0", name="ck_outbox_events_attempts"),
        Index("ix_outbox_organization_id", "organization_id"),
        Index("ix_outbox_status", "status"),
        Index("ix_outbox_event_type", "event_type"),
        Index("ix_outbox_aggregate_id", "aggregate_id"),
        Index("ix_outbox_available_at", "available_at"),
        Index("ix_outbox_created_at", "created_at"),
        Index("ix_outbox_org_status_available", "organization_id", "status", "available_at"),
        Index("ix_outbox_processing_started_at", "processing_started_at"),
        UniqueConstraint(
            "organization_id",
            "event_type",
            "aggregate_type",
            "aggregate_id",
            name="uq_outbox_org_event_aggregate",
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
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
