"""Abandoned POD evidence TTL cleanup.

Revision ID: 011_pod_evidence_cleanup
Revises: 010_pod_object_storage
Create Date: 2026-08-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011_pod_evidence_cleanup"
down_revision: Union[str, Sequence[str], None] = "010_pod_object_storage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pod_evidence",
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.drop_constraint("ck_pod_evidence_status", "pod_evidence", type_="check")
    op.create_check_constraint(
        "ck_pod_evidence_status",
        "pod_evidence",
        "status IN ('PENDING', 'UPLOADED', 'FAILED', 'EXPIRED')",
    )
    op.create_index(
        "ix_pod_evidence_status_created_at",
        "pod_evidence",
        ["status", "created_at"],
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE pod_evidence SET status = 'FAILED', expired_at = NULL "
            "WHERE status = 'EXPIRED'"
        )
    )
    op.drop_index("ix_pod_evidence_status_created_at", table_name="pod_evidence")
    op.drop_constraint("ck_pod_evidence_status", "pod_evidence", type_="check")
    op.create_check_constraint(
        "ck_pod_evidence_status",
        "pod_evidence",
        "status IN ('PENDING', 'UPLOADED', 'FAILED')",
    )
    op.drop_column("pod_evidence", "expired_at")
