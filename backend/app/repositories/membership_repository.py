from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.membership import MembershipStatus, OrganizationMembership
from app.models.role import TENANT_ADMIN, Role


class MembershipRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, user_id: UUID, organization_id: UUID) -> OrganizationMembership | None:
        return (
            self.db.query(OrganizationMembership)
            .options(joinedload(OrganizationMembership.role), joinedload(OrganizationMembership.user))
            .filter(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.organization_id == organization_id,
            )
            .one_or_none()
        )

    def get_by_id(self, membership_id: UUID) -> OrganizationMembership | None:
        return (
            self.db.query(OrganizationMembership)
            .options(joinedload(OrganizationMembership.role), joinedload(OrganizationMembership.user))
            .filter(OrganizationMembership.id == membership_id)
            .one_or_none()
        )

    def get_for_organization(
        self, membership_id: UUID, organization_id: UUID
    ) -> OrganizationMembership | None:
        return (
            self.db.query(OrganizationMembership)
            .options(joinedload(OrganizationMembership.role), joinedload(OrganizationMembership.user))
            .filter(
                OrganizationMembership.id == membership_id,
                OrganizationMembership.organization_id == organization_id,
            )
            .one_or_none()
        )

    def list_for_user(self, user_id: UUID) -> list[OrganizationMembership]:
        return (
            self.db.query(OrganizationMembership)
            .options(
                joinedload(OrganizationMembership.role),
                joinedload(OrganizationMembership.organization),
            )
            .filter(OrganizationMembership.user_id == user_id)
            .order_by(OrganizationMembership.created_at.desc())
            .all()
        )

    def list_active_for_user(self, user_id: UUID) -> list[OrganizationMembership]:
        return [
            membership
            for membership in self.list_for_user(user_id)
            if membership.status == MembershipStatus.ACTIVE
        ]

    def list_for_organization(
        self,
        organization_id: UUID,
        *,
        page: int = 1,
        page_size: int = 100,
    ) -> list[OrganizationMembership]:
        page_size = min(max(page_size, 1), 100)
        page = max(page, 1)
        return (
            self.db.query(OrganizationMembership)
            .options(joinedload(OrganizationMembership.role), joinedload(OrganizationMembership.user))
            .filter(OrganizationMembership.organization_id == organization_id)
            .order_by(OrganizationMembership.created_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

    def count_active_tenant_admins(self, organization_id: UUID) -> int:
        return (
            self.db.query(func.count(OrganizationMembership.id))
            .join(Role, OrganizationMembership.role_id == Role.id)
            .filter(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.status == MembershipStatus.ACTIVE,
                Role.code == TENANT_ADMIN,
            )
            .scalar()
            or 0
        )

    def create(self, membership: OrganizationMembership) -> OrganizationMembership:
        self.db.add(membership)
        self.db.flush()
        return membership

    def delete(self, membership: OrganizationMembership) -> None:
        self.db.delete(membership)
        self.db.flush()


class RoleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_code(self, code: str) -> Role | None:
        return self.db.query(Role).filter(Role.code == code).one_or_none()
