import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class RoleScope(str, enum.Enum):
    PLATFORM = "PLATFORM"
    ORGANIZATION = "ORGANIZATION"


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("code", name="uq_roles_code"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    scope: Mapped[RoleScope] = mapped_column(
        Enum(RoleScope, name="role_scope"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    memberships = relationship("OrganizationMembership", back_populates="role")


PLATFORM_SUPER_ADMIN = "PLATFORM_SUPER_ADMIN"
TENANT_ADMIN = "TENANT_ADMIN"
OPERATIONS_MANAGER = "OPERATIONS_MANAGER"
STAFF = "STAFF"
CUSTOMER = "CUSTOMER"

TENANT_ASSIGNABLE_ROLES = (
    TENANT_ADMIN,
    OPERATIONS_MANAGER,
    STAFF,
    CUSTOMER,
)

SHIPMENT_READ_ROLES = (TENANT_ADMIN, OPERATIONS_MANAGER, STAFF)
SHIPMENT_WRITE_ROLES = (TENANT_ADMIN, OPERATIONS_MANAGER, STAFF)
SHIPMENT_CANCEL_ROLES = (TENANT_ADMIN, OPERATIONS_MANAGER)
SHIPMENT_STATUS_ROLES = (TENANT_ADMIN, OPERATIONS_MANAGER, STAFF)

CUSTOMER_READ_ROLES = (TENANT_ADMIN, OPERATIONS_MANAGER, STAFF)
CUSTOMER_WRITE_ROLES = (TENANT_ADMIN, OPERATIONS_MANAGER, STAFF)
CUSTOMER_STATUS_ROLES = (TENANT_ADMIN, OPERATIONS_MANAGER)

RIDER_READ_ROLES = (TENANT_ADMIN, OPERATIONS_MANAGER, STAFF)
RIDER_WRITE_ROLES = (TENANT_ADMIN, OPERATIONS_MANAGER)
RIDER_STATUS_ROLES = (TENANT_ADMIN, OPERATIONS_MANAGER)
RIDER_ASSIGN_ROLES = (TENANT_ADMIN, OPERATIONS_MANAGER)
POD_CREATE_ROLES = (TENANT_ADMIN, OPERATIONS_MANAGER)
NOTIFICATION_READ_ROLES = (TENANT_ADMIN, OPERATIONS_MANAGER)
NOTIFICATION_SETTINGS_WRITE_ROLES = (TENANT_ADMIN,)

SEED_ROLES = (
    (PLATFORM_SUPER_ADMIN, "Platform Super Admin", RoleScope.PLATFORM),
    (TENANT_ADMIN, "Tenant Admin", RoleScope.ORGANIZATION),
    (OPERATIONS_MANAGER, "Operations Manager", RoleScope.ORGANIZATION),
    (STAFF, "Staff", RoleScope.ORGANIZATION),
    (CUSTOMER, "Customer", RoleScope.ORGANIZATION),
)
