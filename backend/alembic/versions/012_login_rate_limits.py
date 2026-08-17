"""Login attempt rate-limit windows.

Revision ID: 012_login_rate_limits
Revises: 011_pod_evidence_cleanup
Create Date: 2026-08-15

This is a production-hardening migration, not Module 12 product work.
Downgrade drops the table. Empty-DB round-trip is not a populated
production rollback guarantee. Prefer backup/PITR for live databases.
Known historical warnings remain:
- 005 downgrade is unsafe with operational shipment statuses.
- 011 downgrade maps EXPIRED evidence to FAILED.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012_login_rate_limits"
down_revision: Union[str, Sequence[str], None] = "011_pod_evidence_cleanup"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "login_attempt_windows",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash", name="uq_login_attempt_windows_key_hash"),
        sa.CheckConstraint("failed_count >= 0", name="ck_login_attempt_windows_failed_count"),
    )
    op.create_index(
        "ix_login_attempt_windows_locked_until",
        "login_attempt_windows",
        ["locked_until"],
    )


def downgrade() -> None:
    op.drop_index("ix_login_attempt_windows_locked_until", table_name="login_attempt_windows")
    op.drop_table("login_attempt_windows")
