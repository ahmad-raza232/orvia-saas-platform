"""Outbox worker hardening: processing lease timestamp.

Revision ID: 009_outbox_worker_hardening
Revises: 008_notifications_and_outbox
Create Date: 2026-08-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_outbox_worker_hardening"
down_revision: Union[str, Sequence[str], None] = "008_notifications_and_outbox"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "outbox_events",
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_outbox_processing_started_at",
        "outbox_events",
        ["processing_started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_outbox_processing_started_at", table_name="outbox_events")
    op.drop_column("outbox_events", "processing_started_at")
