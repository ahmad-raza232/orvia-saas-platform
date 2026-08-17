"""Tenant-scoped outbox, notifications, and email settings.

Revision ID: 008_notifications_and_outbox
Revises: 007_proof_of_delivery
Create Date: 2026-08-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008_notifications_and_outbox"
down_revision: Union[str, Sequence[str], None] = "007_proof_of_delivery"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EVENT_TYPES = (
    "SHIPMENT_BOOKED",
    "SHIPMENT_PICKED_UP",
    "SHIPMENT_IN_TRANSIT",
    "SHIPMENT_OUT_FOR_DELIVERY",
    "SHIPMENT_DELIVERED",
    "SHIPMENT_CANCELLED",
    "POD_CREATED",
)
EVENT_IN = ", ".join(f"'{item}'" for item in EVENT_TYPES)


def upgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_type", sa.String(length=64), nullable=False),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PENDING"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('PENDING', 'PROCESSING', 'PROCESSED', 'FAILED')", name="ck_outbox_events_status"),
        sa.CheckConstraint(f"event_type IN ({EVENT_IN})", name="ck_outbox_events_event_type"),
        sa.CheckConstraint("attempts >= 0", name="ck_outbox_events_attempts"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "event_type",
            "aggregate_type",
            "aggregate_id",
            name="uq_outbox_org_event_aggregate",
        ),
    )
    op.create_index("ix_outbox_organization_id", "outbox_events", ["organization_id"])
    op.create_index("ix_outbox_status", "outbox_events", ["status"])
    op.create_index("ix_outbox_event_type", "outbox_events", ["event_type"])
    op.create_index("ix_outbox_aggregate_id", "outbox_events", ["aggregate_id"])
    op.create_index("ix_outbox_available_at", "outbox_events", ["available_at"])
    op.create_index("ix_outbox_created_at", "outbox_events", ["created_at"])
    op.create_index(
        "ix_outbox_org_status_available",
        "outbox_events",
        ["organization_id", "status", "available_at"],
    )

    op.create_table(
        "notification_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(f"event_type IN ({EVENT_IN})", name="ck_notification_settings_event_type"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "event_type", name="uq_notification_settings_org_event"),
    )
    op.create_index("ix_notification_settings_organization_id", "notification_settings", ["organization_id"])

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("outbox_event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("channel", sa.String(length=16), nullable=False, server_default="EMAIL"),
        sa.Column("recipient", sa.String(length=255), nullable=True),
        sa.Column("template_key", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("tracking_number", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="PENDING"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("channel IN ('EMAIL')", name="ck_notifications_channel"),
        sa.CheckConstraint(
            "status IN ('PENDING', 'SENDING', 'SENT', 'FAILED', 'SKIPPED')",
            name="ck_notifications_status",
        ),
        sa.CheckConstraint(f"event_type IN ({EVENT_IN})", name="ck_notifications_event_type"),
        sa.CheckConstraint("attempts >= 0", name="ck_notifications_attempts"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["outbox_event_id"], ["outbox_events.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("outbox_event_id", "channel", name="uq_notifications_outbox_channel"),
    )
    op.create_index("ix_notifications_organization_id", "notifications", ["organization_id"])
    op.create_index("ix_notifications_status", "notifications", ["status"])
    op.create_index("ix_notifications_channel", "notifications", ["channel"])
    op.create_index("ix_notifications_event_type", "notifications", ["event_type"])
    op.create_index("ix_notifications_shipment_id", "notifications", ["shipment_id"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])
    op.create_index("ix_notifications_org_created", "notifications", ["organization_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_notifications_org_created", table_name="notifications")
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_shipment_id", table_name="notifications")
    op.drop_index("ix_notifications_event_type", table_name="notifications")
    op.drop_index("ix_notifications_channel", table_name="notifications")
    op.drop_index("ix_notifications_status", table_name="notifications")
    op.drop_index("ix_notifications_organization_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_notification_settings_organization_id", table_name="notification_settings")
    op.drop_table("notification_settings")
    op.drop_index("ix_outbox_org_status_available", table_name="outbox_events")
    op.drop_index("ix_outbox_created_at", table_name="outbox_events")
    op.drop_index("ix_outbox_available_at", table_name="outbox_events")
    op.drop_index("ix_outbox_aggregate_id", table_name="outbox_events")
    op.drop_index("ix_outbox_event_type", table_name="outbox_events")
    op.drop_index("ix_outbox_status", table_name="outbox_events")
    op.drop_index("ix_outbox_organization_id", table_name="outbox_events")
    op.drop_table("outbox_events")
