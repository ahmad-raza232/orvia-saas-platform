"""Proof of delivery metadata for delivered shipments.

Revision ID: 007_proof_of_delivery
Revises: 006_riders_and_assignments
Create Date: 2026-08-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007_proof_of_delivery"
down_revision: Union[str, Sequence[str], None] = "006_riders_and_assignments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "proof_of_deliveries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_name", sa.String(length=120), nullable=False),
        sa.Column("delivery_note", sa.Text(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rider_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("signature_file_name", sa.String(length=255), nullable=True),
        sa.Column("signature_mime_type", sa.String(length=64), nullable=True),
        sa.Column("signature_storage_key", sa.String(length=512), nullable=True),
        sa.Column("signature_url", sa.String(length=1024), nullable=True),
        sa.Column("signature_file_size", sa.Integer(), nullable=True),
        sa.Column("signature_checksum", sa.String(length=128), nullable=True),
        sa.Column("photo_file_name", sa.String(length=255), nullable=True),
        sa.Column("photo_mime_type", sa.String(length=64), nullable=True),
        sa.Column("photo_storage_key", sa.String(length=512), nullable=True),
        sa.Column("photo_url", sa.String(length=1024), nullable=True),
        sa.Column("photo_file_size", sa.Integer(), nullable=True),
        sa.Column("photo_checksum", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recorded_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rider_id"], ["riders.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pod_organization_id", "proof_of_deliveries", ["organization_id"])
    op.create_index("uq_pod_shipment_id", "proof_of_deliveries", ["shipment_id"], unique=True)
    op.create_index("ix_pod_recorded_by_user_id", "proof_of_deliveries", ["recorded_by_user_id"])
    op.create_index("ix_pod_rider_id", "proof_of_deliveries", ["rider_id"])


def downgrade() -> None:
    op.drop_index("ix_pod_rider_id", table_name="proof_of_deliveries")
    op.drop_index("ix_pod_recorded_by_user_id", table_name="proof_of_deliveries")
    op.drop_index("uq_pod_shipment_id", table_name="proof_of_deliveries")
    op.drop_index("ix_pod_organization_id", table_name="proof_of_deliveries")
    op.drop_table("proof_of_deliveries")
