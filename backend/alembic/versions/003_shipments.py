"""Tenant-scoped shipments and status history.

Revision ID: 003_shipments
Revises: 002_org_management
Create Date: 2026-08-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_shipments"
down_revision: Union[str, Sequence[str], None] = "002_org_management"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shipments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tracking_number", sa.String(length=32), nullable=False),
        sa.Column("reference_number", sa.String(length=80), nullable=True),
        sa.Column("sender_name", sa.String(length=120), nullable=False),
        sa.Column("sender_phone", sa.String(length=32), nullable=False),
        sa.Column("sender_email", sa.String(length=255), nullable=True),
        sa.Column("sender_address", sa.String(length=255), nullable=False),
        sa.Column("sender_city", sa.String(length=80), nullable=False),
        sa.Column("sender_state", sa.String(length=80), nullable=True),
        sa.Column("sender_country", sa.String(length=2), nullable=True),
        sa.Column("sender_postal_code", sa.String(length=20), nullable=True),
        sa.Column("receiver_name", sa.String(length=120), nullable=False),
        sa.Column("receiver_phone", sa.String(length=32), nullable=False),
        sa.Column("receiver_email", sa.String(length=255), nullable=True),
        sa.Column("receiver_address", sa.String(length=255), nullable=False),
        sa.Column("receiver_city", sa.String(length=80), nullable=False),
        sa.Column("receiver_state", sa.String(length=80), nullable=True),
        sa.Column("receiver_country", sa.String(length=2), nullable=True),
        sa.Column("receiver_postal_code", sa.String(length=20), nullable=True),
        sa.Column("weight_kg", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("length_cm", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("width_cm", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("height_cm", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("package_type", sa.String(length=32), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("service_type", sa.String(length=32), nullable=False, server_default="STANDARD"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="BOOKED"),
        sa.Column("cod_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("pickup_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("weight_kg > 0", name="ck_shipments_weight_positive"),
        sa.CheckConstraint("quantity >= 1", name="ck_shipments_quantity_min"),
        sa.CheckConstraint("length_cm IS NULL OR length_cm >= 0", name="ck_shipments_length_non_negative"),
        sa.CheckConstraint("width_cm IS NULL OR width_cm >= 0", name="ck_shipments_width_non_negative"),
        sa.CheckConstraint("height_cm IS NULL OR height_cm >= 0", name="ck_shipments_height_non_negative"),
        sa.CheckConstraint("cod_amount IS NULL OR cod_amount >= 0", name="ck_shipments_cod_non_negative"),
        sa.CheckConstraint("status IN ('DRAFT', 'BOOKED', 'CANCELLED')", name="ck_shipments_status"),
        sa.CheckConstraint(
            "service_type IN ('STANDARD', 'EXPRESS', 'SAME_DAY')",
            name="ck_shipments_service_type",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shipments_organization_id", "shipments", ["organization_id"])
    op.create_index("ix_shipments_org_reference", "shipments", ["organization_id", "reference_number"])
    op.create_index("ix_shipments_org_status", "shipments", ["organization_id", "status"])
    op.create_index("ix_shipments_org_created_at", "shipments", ["organization_id", "created_at"])
    op.create_index("uq_shipments_tracking_number", "shipments", ["tracking_number"], unique=True)
    op.create_index("ix_shipments_org_tracking", "shipments", ["organization_id", "tracking_number"])
    op.create_index("ix_shipments_created_by_user_id", "shipments", ["created_by_user_id"])

    op.create_table(
        "shipment_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("previous_status", sa.String(length=32), nullable=True),
        sa.Column("new_status", sa.String(length=32), nullable=False),
        sa.Column("changed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_shipment_status_history_shipment_id",
        "shipment_status_history",
        ["shipment_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_shipment_status_history_shipment_id", table_name="shipment_status_history")
    op.drop_table("shipment_status_history")
    op.drop_index("ix_shipments_created_by_user_id", table_name="shipments")
    op.drop_index("ix_shipments_org_tracking", table_name="shipments")
    op.drop_index("uq_shipments_tracking_number", table_name="shipments")
    op.drop_index("ix_shipments_org_created_at", table_name="shipments")
    op.drop_index("ix_shipments_org_status", table_name="shipments")
    op.drop_index("ix_shipments_org_reference", table_name="shipments")
    op.drop_index("ix_shipments_organization_id", table_name="shipments")
    op.drop_table("shipments")
