from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from app.models.invitation import InvitationStatus, OrganizationInvitation
from app.models.platform_admin import PlatformAdminGrant


class InvitationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, invitation_id: UUID) -> OrganizationInvitation | None:
        return (
            self.db.query(OrganizationInvitation)
            .options(joinedload(OrganizationInvitation.role))
            .filter(OrganizationInvitation.id == invitation_id)
            .one_or_none()
        )

    def get_for_organization(
        self, invitation_id: UUID, organization_id: UUID
    ) -> OrganizationInvitation | None:
        return (
            self.db.query(OrganizationInvitation)
            .options(joinedload(OrganizationInvitation.role))
            .filter(
                OrganizationInvitation.id == invitation_id,
                OrganizationInvitation.organization_id == organization_id,
            )
            .one_or_none()
        )

    def get_by_token_hash(self, token_hash: str) -> OrganizationInvitation | None:
        return (
            self.db.query(OrganizationInvitation)
            .options(joinedload(OrganizationInvitation.role))
            .filter(OrganizationInvitation.token_hash == token_hash)
            .one_or_none()
        )

    def get_pending(self, organization_id: UUID, email: str) -> OrganizationInvitation | None:
        return (
            self.db.query(OrganizationInvitation)
            .filter(
                OrganizationInvitation.organization_id == organization_id,
                OrganizationInvitation.email == email,
                OrganizationInvitation.status == InvitationStatus.PENDING,
            )
            .one_or_none()
        )

    def list_for_organization(
        self,
        organization_id: UUID,
        *,
        page: int = 1,
        page_size: int = 100,
    ) -> list[OrganizationInvitation]:
        page_size = min(max(page_size, 1), 100)
        page = max(page, 1)
        return (
            self.db.query(OrganizationInvitation)
            .options(joinedload(OrganizationInvitation.role))
            .filter(OrganizationInvitation.organization_id == organization_id)
            .order_by(OrganizationInvitation.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

    def create(self, invitation: OrganizationInvitation) -> OrganizationInvitation:
        self.db.add(invitation)
        self.db.flush()
        return invitation


class PlatformAdminRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_user_id(self, user_id: UUID) -> PlatformAdminGrant | None:
        return (
            self.db.query(PlatformAdminGrant)
            .filter(PlatformAdminGrant.user_id == user_id)
            .one_or_none()
        )
