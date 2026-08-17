"""Tenant-scoped customers and shipment customer ownership.

Revision ID: 004_customers
Revises: 003_shipments
Create Date: 2026-08-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_customers"
down_revision: Union[str, Sequence[str], None] = "003_shipments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("alternate_phone", sa.String(length=32), nullable=True),
        sa.Column("company_name", sa.String(length=160), nullable=True),
        sa.Column("address", sa.String(length=255), nullable=True),
        sa.Column("city", sa.String(length=80), nullable=True),
        sa.Column("state", sa.String(length=80), nullable=True),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="ACTIVE"),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE')", name="ck_customers_status"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customers_organization_id", "customers", ["organization_id"])
    op.create_index("uq_customers_org_code", "customers", ["organization_id", "customer_code"], unique=True)
    op.create_index("ix_customers_org_status", "customers", ["organization_id", "status"])
    op.create_index("ix_customers_org_email", "customers", ["organization_id", "email"])
    op.create_index("ix_customers_org_phone", "customers", ["organization_id", "phone"])
    op.create_index("ix_customers_org_created_at", "customers", ["organization_id", "created_at"])
    op.create_index("ix_customers_created_by_user_id", "customers", ["created_by_user_id"])
    op.create_index(
        "uq_customers_org_email",
        "customers",
        ["organization_id", "email"],
        unique=True,
        postgresql_where=sa.text("email IS NOT NULL"),
    )

    op.add_column(
        "shipments",
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_shipments_customer_id",
        "shipments",
        "customers",
        ["customer_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_shipments_customer_id", "shipments", ["customer_id"])
    op.create_index("ix_shipments_org_customer", "shipments", ["organization_id", "customer_id"])


def downgrade() -> None:
    op.drop_index("ix_shipments_org_customer", table_name="shipments")
    op.drop_index("ix_shipments_customer_id", table_name="shipments")
    op.drop_constraint("fk_shipments_customer_id", "shipments", type_="foreignkey")
    op.drop_column("shipments", "customer_id")

    op.drop_index("uq_customers_org_email", table_name="customers")
    op.drop_index("ix_customers_created_by_user_id", table_name="customers")
    op.drop_index("ix_customers_org_created_at", table_name="customers")
    op.drop_index("ix_customers_org_phone", table_name="customers")
    op.drop_index("ix_customers_org_email", table_name="customers")
    op.drop_index("ix_customers_org_status", table_name="customers")
    op.drop_index("uq_customers_org_code", table_name="customers")
    op.drop_index("ix_customers_organization_id", table_name="customers")
    op.drop_table("customers")
