"""Operational shipment timestamps and expanded status constraint.

Revision ID: 005_shipment_operations
Revises: 004_customers
Create Date: 2026-08-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_shipment_operations"
down_revision: Union[str, Sequence[str], None] = "004_customers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("shipments", sa.Column("picked_up_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("shipments", sa.Column("in_transit_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("shipments", sa.Column("out_for_delivery_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("shipments", sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("shipments", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))

    op.drop_constraint("ck_shipments_status", "shipments", type_="check")
    op.create_check_constraint(
        "ck_shipments_status",
        "shipments",
        "status IN ('DRAFT', 'BOOKED', 'PICKED_UP', 'IN_TRANSIT', "
        "'OUT_FOR_DELIVERY', 'DELIVERED', 'CANCELLED')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_shipments_status", "shipments", type_="check")
    op.create_check_constraint(
        "ck_shipments_status",
        "shipments",
        "status IN ('DRAFT', 'BOOKED', 'CANCELLED')",
    )
    op.drop_column("shipments", "cancelled_at")
    op.drop_column("shipments", "delivered_at")
    op.drop_column("shipments", "out_for_delivery_at")
    op.drop_column("shipments", "in_transit_at")
    op.drop_column("shipments", "picked_up_at")
