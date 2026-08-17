import uuid
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicateMembershipError,
    DuplicateSlugError,
    OrganizationSuspendedError,
    ReservedSlugError,
)
from app.core.slugs import is_reserved_slug, slugify
from app.models.membership import MembershipStatus, OrganizationMembership
from app.models.organization import Organization, OrganizationStatus
from app.models.role import TENANT_ADMIN
from app.models.user import User
from app.repositories.membership_repository import MembershipRepository, RoleRepository
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.organization import OrganizationCreate, OrganizationUpdate
from app.services.audit_service import AuditService


class OrganizationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.organizations = OrganizationRepository(db)
        self.memberships = MembershipRepository(db)
        self.roles = RoleRepository(db)
        self.audit = AuditService(db)

    def _unique_slug(self, requested: str, *, exclude_id: uuid.UUID | None = None) -> str:
        base = slugify(requested)
        if is_reserved_slug(base):
            base = f"{base}-org"
        slug = base
        while True:
            existing = self.organizations.get_by_slug(slug)
            if existing is None or existing.id == exclude_id:
                return slug
            suffix = uuid.uuid4().hex[:6]
            slug = f"{base[:73]}-{suffix}"

    def _assert_slug_available(self, slug: str, *, exclude_id: uuid.UUID | None = None) -> None:
        if is_reserved_slug(slug):
            raise ReservedSlugError()
        other = self.organizations.get_by_slug(slug)
        if other and other.id != exclude_id:
            raise DuplicateSlugError()

    def create_for_user(self, user: User, payload: OrganizationCreate) -> Organization:
        existing = self.memberships.list_active_for_user(user.id)
        if existing:
            raise DuplicateMembershipError()

        role = self.roles.get_by_code(TENANT_ADMIN)
        if role is None:
            raise RuntimeError("TENANT_ADMIN role is not seeded")

        requested_slug = payload.slug or payload.name
        if payload.slug:
            self._assert_slug_available(payload.slug)

        organization = Organization(
            name=payload.name,
            slug=self._unique_slug(requested_slug) if not payload.slug else payload.slug,
            status=OrganizationStatus.ACTIVE,
        )
        self.organizations.create(organization)
        membership = OrganizationMembership(
            user_id=user.id,
            organization_id=organization.id,
            role_id=role.id,
            status=MembershipStatus.ACTIVE,
        )
        self.memberships.create(membership)
        self.audit.record(
            action="ORGANIZATION_CREATED",
            resource_type="organization",
            resource_id=organization.id,
            organization_id=organization.id,
            actor_user_id=user.id,
            details={"name": organization.name, "slug": organization.slug},
        )
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            message = str(exc.orig) if getattr(exc, "orig", None) else str(exc)
            if "uq_membership_user_organization" in message:
                raise DuplicateMembershipError() from exc
            if "slug" in message.lower():
                raise DuplicateSlugError() from exc
            raise
        self.db.refresh(organization)
        return organization

    def update(
        self, organization: Organization, payload: OrganizationUpdate, *, actor: User
    ) -> Organization:
        changes: dict = {}
        if payload.name is not None and payload.name != organization.name:
            changes["name"] = {"from": organization.name, "to": payload.name}
            organization.name = payload.name
        if payload.slug is not None and payload.slug != organization.slug:
            self._assert_slug_available(payload.slug, exclude_id=organization.id)
            changes["slug"] = {"from": organization.slug, "to": payload.slug}
            organization.slug = payload.slug
        organization.updated_at = datetime.now(timezone.utc)
        if changes:
            self.audit.record(
                action="ORGANIZATION_UPDATED",
                resource_type="organization",
                resource_id=organization.id,
                organization_id=organization.id,
                actor_user_id=actor.id,
                details=changes,
            )
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateSlugError() from exc
        self.db.refresh(organization)
        return organization

    def suspend(self, organization: Organization, *, actor: User) -> Organization:
        if organization.status == OrganizationStatus.SUSPENDED:
            return organization
        organization.status = OrganizationStatus.SUSPENDED
        organization.updated_at = datetime.now(timezone.utc)
        self.audit.record(
            action="ORGANIZATION_SUSPENDED",
            resource_type="organization",
            resource_id=organization.id,
            organization_id=organization.id,
            actor_user_id=actor.id,
        )
        self.db.commit()
        self.db.refresh(organization)
        return organization

    def reactivate(self, organization: Organization, *, actor: User) -> Organization:
        if organization.status == OrganizationStatus.ACTIVE:
            return organization
        organization.status = OrganizationStatus.ACTIVE
        organization.updated_at = datetime.now(timezone.utc)
        self.audit.record(
            action="ORGANIZATION_REACTIVATED",
            resource_type="organization",
            resource_id=organization.id,
            organization_id=organization.id,
            actor_user_id=actor.id,
        )
        self.db.commit()
        self.db.refresh(organization)
        return organization

    def require_active(self, organization: Organization) -> Organization:
        if organization.status != OrganizationStatus.ACTIVE:
            raise OrganizationSuspendedError()
        return organization
