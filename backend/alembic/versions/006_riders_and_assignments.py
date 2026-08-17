"""Tenant-scoped riders and shipment rider assignments.

Revision ID: 006_riders_and_assignments
Revises: 005_shipment_operations
Create Date: 2026-08-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006_riders_and_assignments"
down_revision: Union[str, Sequence[str], None] = "005_shipment_operations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "riders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rider_code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("vehicle_type", sa.String(length=32), nullable=True),
        sa.Column("vehicle_number", sa.String(length=32), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_riders_status"),
        sa.CheckConstraint(
            "vehicle_type IS NULL OR vehicle_type IN "
            "('MOTORCYCLE', 'BICYCLE', 'CAR', 'VAN', 'TRUCK', 'WALKING', 'OTHER')",
            name="ck_riders_vehicle_type",
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_riders_organization_id", "riders", ["organization_id"])
    op.create_index("uq_riders_org_code", "riders", ["organization_id", "rider_code"], unique=True)
    op.create_index("ix_riders_org_status", "riders", ["organization_id", "status"])
    op.create_index("ix_riders_org_created_at", "riders", ["organization_id", "created_at"])
    op.create_index("ix_riders_created_by_user_id", "riders", ["created_by_user_id"])

    op.add_column("shipments", sa.Column("rider_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_shipments_rider_id",
        "shipments",
        "riders",
        ["rider_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_shipments_rider_id", "shipments", ["rider_id"])
    op.create_index("ix_shipments_org_rider", "shipments", ["organization_id", "rider_id"])

    op.create_table(
        "shipment_rider_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("unassigned_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("unassigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["assigned_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["rider_id"], ["riders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["unassigned_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_assignments_org_shipment",
        "shipment_rider_assignments",
        ["organization_id", "shipment_id"],
    )
    op.create_index(
        "ix_assignments_org_rider",
        "shipment_rider_assignments",
        ["organization_id", "rider_id"],
    )
    op.create_index(
        "uq_assignments_active_shipment",
        "shipment_rider_assignments",
        ["shipment_id"],
        unique=True,
        postgresql_where=sa.text("unassigned_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_assignments_active_shipment", table_name="shipment_rider_assignments")
    op.drop_index("ix_assignments_org_rider", table_name="shipment_rider_assignments")
    op.drop_index("ix_assignments_org_shipment", table_name="shipment_rider_assignments")
    op.drop_table("shipment_rider_assignments")

    op.drop_index("ix_shipments_org_rider", table_name="shipments")
    op.drop_index("ix_shipments_rider_id", table_name="shipments")
    op.drop_constraint("fk_shipments_rider_id", "shipments", type_="foreignkey")
    op.drop_column("shipments", "rider_id")

    op.drop_index("ix_riders_created_by_user_id", table_name="riders")
    op.drop_index("ix_riders_org_created_at", table_name="riders")
    op.drop_index("ix_riders_org_status", table_name="riders")
    op.drop_index("uq_riders_org_code", table_name="riders")
    op.drop_index("ix_riders_organization_id", table_name="riders")
    op.drop_table("riders")
