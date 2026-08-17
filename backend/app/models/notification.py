import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.events import DOMAIN_EVENT_TYPES
from app.db.database import Base

NOTIFICATION_CHANNELS = ("EMAIL",)
NOTIFICATION_STATUSES = ("PENDING", "SENDING", "SENT", "FAILED", "SKIPPED")
_CHANNEL_IN = ", ".join(f"'{item}'" for item in NOTIFICATION_CHANNELS)
_STATUS_IN = ", ".join(f"'{item}'" for item in NOTIFICATION_STATUSES)
_EVENT_IN = ", ".join(f"'{item}'" for item in DOMAIN_EVENT_TYPES)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(f"channel IN ({_CHANNEL_IN})", name="ck_notifications_channel"),
        CheckConstraint(f"status IN ({_STATUS_IN})", name="ck_notifications_status"),
        CheckConstraint(f"event_type IN ({_EVENT_IN})", name="ck_notifications_event_type"),
        CheckConstraint("attempts >= 0", name="ck_notifications_attempts"),
        Index("ix_notifications_organization_id", "organization_id"),
        Index("ix_notifications_status", "status"),
        Index("ix_notifications_channel", "channel"),
        Index("ix_notifications_event_type", "event_type"),
        Index("ix_notifications_shipment_id", "shipment_id"),
        Index("ix_notifications_created_at", "created_at"),
        Index("ix_notifications_org_created", "organization_id", "created_at"),
        UniqueConstraint("outbox_event_id", "channel", name="uq_notifications_outbox_channel"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    outbox_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("outbox_events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    shipment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shipments.id", ondelete="RESTRICT"),
        nullable=True,
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
    )
    channel: Mapped[str] = mapped_column(String(16), nullable=False, default="EMAIL")
    recipient: Mapped[str | None] = mapped_column(String(255), nullable=True)
    template_key: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    tracking_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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


class NotificationSetting(Base):
    __tablename__ = "notification_settings"
    __table_args__ = (
        CheckConstraint(f"event_type IN ({_EVENT_IN})", name="ck_notification_settings_event_type"),
        Index("ix_notification_settings_organization_id", "organization_id"),
        UniqueConstraint("organization_id", "event_type", name="uq_notification_settings_org_event"),
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
    email_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
