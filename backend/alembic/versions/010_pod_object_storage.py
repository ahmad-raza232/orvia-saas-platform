"""POD object-storage evidence metadata.

Revision ID: 010_pod_object_storage
Revises: 009_outbox_worker_hardening
Create Date: 2026-08-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010_pod_object_storage"
down_revision: Union[str, Sequence[str], None] = "009_outbox_worker_hardening"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pod_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pod_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evidence_type", sa.String(length=32), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint(
            "evidence_type IN ('SIGNATURE', 'DELIVERY_PHOTO')",
            name="ck_pod_evidence_type",
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'UPLOADED', 'FAILED')",
            name="ck_pod_evidence_status",
        ),
        sa.CheckConstraint("size_bytes >= 1", name="ck_pod_evidence_size_positive"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["pod_id"], ["proof_of_deliveries.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["shipment_id"], ["shipments.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pod_evidence_organization_id", "pod_evidence", ["organization_id"]
    )
    op.create_index("ix_pod_evidence_pod_id", "pod_evidence", ["pod_id"])
    op.create_index("ix_pod_evidence_shipment_id", "pod_evidence", ["shipment_id"])
    op.create_index("ix_pod_evidence_status", "pod_evidence", ["status"])
    op.create_index("ix_pod_evidence_created_at", "pod_evidence", ["created_at"])
    op.create_index(
        "uq_pod_evidence_uploaded_type",
        "pod_evidence",
        ["pod_id", "evidence_type"],
        unique=True,
        postgresql_where=sa.text("status = 'UPLOADED'"),
    )


def downgrade() -> None:
    op.drop_index("uq_pod_evidence_uploaded_type", table_name="pod_evidence")
    op.drop_index("ix_pod_evidence_created_at", table_name="pod_evidence")
    op.drop_index("ix_pod_evidence_status", table_name="pod_evidence")
    op.drop_index("ix_pod_evidence_shipment_id", table_name="pod_evidence")
    op.drop_index("ix_pod_evidence_pod_id", table_name="pod_evidence")
    op.drop_index("ix_pod_evidence_organization_id", table_name="pod_evidence")
    op.drop_table("pod_evidence")
