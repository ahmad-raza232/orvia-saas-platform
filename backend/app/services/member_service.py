from datetime import datetime, timedelta, timezone
import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    DuplicateInvitationError,
    DuplicateMembershipError,
    InvitationExpiredError,
    InvitationInvalidError,
    InvalidRoleError,
    LastTenantAdminError,
    NotFoundError,
    OrganizationSuspendedError,
)
from app.core.security import generate_invitation_token, hash_invitation_token
from app.models.invitation import InvitationStatus, OrganizationInvitation
from app.models.membership import MembershipStatus, OrganizationMembership
from app.models.organization import Organization, OrganizationStatus
from app.models.role import TENANT_ADMIN, TENANT_ASSIGNABLE_ROLES
from app.models.user import User
from app.repositories.invitation_repository import InvitationRepository
from app.repositories.membership_repository import MembershipRepository, RoleRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.organization import MemberInviteRequest, MemberUpdateRequest
from app.services.audit_service import AuditService
from app.services.email_provider import EmailDeliveryError, get_email_provider

logger = logging.getLogger("orvia.members")


class MemberService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.memberships = MembershipRepository(db)
        self.invitations = InvitationRepository(db)
        self.organizations = OrganizationRepository(db)
        self.users = UserRepository(db)
        self.roles = RoleRepository(db)
        self.audit = AuditService(db)

    def _assignable_role(self, role_code: str):
        if role_code not in TENANT_ASSIGNABLE_ROLES:
            raise InvalidRoleError("Tenant admins can only assign organization roles.")
        role = self.roles.get_by_code(role_code)
        if role is None:
            raise InvalidRoleError()
        return role

    def _guard_last_admin(
        self,
        organization: Organization,
        membership: OrganizationMembership,
        *,
        new_role_code: str | None = None,
        new_status: MembershipStatus | None = None,
        removing: bool = False,
    ) -> None:
        if membership.role.code != TENANT_ADMIN:
            return
        if membership.status != MembershipStatus.ACTIVE:
            return
        demoting = new_role_code is not None and new_role_code != TENANT_ADMIN
        deactivating = new_status is not None and new_status != MembershipStatus.ACTIVE
        if not (removing or demoting or deactivating):
            return
        if self.memberships.count_active_tenant_admins(organization.id) <= 1:
            raise LastTenantAdminError()

    def list_members(
        self,
        organization: Organization,
        *,
        page: int = 1,
        page_size: int = 100,
    ) -> list[OrganizationMembership]:
        return self.memberships.list_for_organization(
            organization.id, page=page, page_size=page_size
        )

    def invite(
        self, organization: Organization, actor: User, payload: MemberInviteRequest
    ) -> OrganizationInvitation:
        role = self._assignable_role(payload.role_code)
        if self.invitations.get_pending(organization.id, payload.email):
            raise DuplicateInvitationError()

        existing_user = self.users.get_by_email(payload.email)
        if existing_user is not None:
            membership = self.memberships.get(existing_user.id, organization.id)
            if membership is not None:
                raise DuplicateMembershipError()

        raw_token = generate_invitation_token()
        invitation = OrganizationInvitation(
            organization_id=organization.id,
            email=payload.email,
            role_id=role.id,
            invited_by_user_id=actor.id,
            token_hash=hash_invitation_token(raw_token),
            status=InvitationStatus.PENDING,
            expires_at=datetime.now(timezone.utc)
            + timedelta(hours=settings.invitation_expire_hours),
        )
        self.invitations.create(invitation)

        if existing_user is not None:
            self.memberships.create(
                OrganizationMembership(
                    user_id=existing_user.id,
                    organization_id=organization.id,
                    role_id=role.id,
                    status=MembershipStatus.INVITED,
                )
            )

        self.audit.record(
            action="MEMBER_INVITED",
            resource_type="invitation",
            resource_id=invitation.id,
            organization_id=organization.id,
            actor_user_id=actor.id,
            details={"email": payload.email, "role_code": payload.role_code},
        )
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateInvitationError() from exc
        invitation = self.invitations.get_by_id(invitation.id)
        self._deliver_invitation_out_of_band(organization, invitation, raw_token)
        return invitation

    def _deliver_invitation_out_of_band(
        self,
        organization: Organization,
        invitation: OrganizationInvitation,
        raw_token: str,
    ) -> None:
        """Send the one-time token via email. Never include the token in HTTP responses."""
        body = (
            f"You have been invited to join {organization.name} on Softorica.\n\n"
            "1. Sign in (or register) with this email address.\n"
            "2. Open Softorica onboarding or Organization → Accept invitation.\n"
            "3. Paste this one-time invitation token:\n\n"
            f"{raw_token}\n\n"
            f"This token expires at {invitation.expires_at.isoformat()}.\n"
        )
        metadata: dict = {
            "kind": "organization_invitation",
            "invitation_id": str(invitation.id),
        }
        try:
            get_email_provider().send(
                recipient=invitation.email,
                subject=f"Softorica invitation — {organization.name}",
                body=body,
                metadata=metadata,
            )
        except EmailDeliveryError:
            logger.warning(
                "invitation.email_failed invitation_id=%s",
                invitation.id,
            )

    def update_member(
        self,
        organization: Organization,
        actor: User,
        membership_id,
        payload: MemberUpdateRequest,
    ) -> OrganizationMembership:
        membership = self.memberships.get_for_organization(membership_id, organization.id)
        if membership is None:
            raise NotFoundError("Membership not found.")

        if payload.role_code is not None:
            role = self._assignable_role(payload.role_code)
            self._guard_last_admin(organization, membership, new_role_code=payload.role_code)
            if membership.role_id != role.id:
                self.audit.record(
                    action="MEMBER_ROLE_CHANGED",
                    resource_type="membership",
                    resource_id=membership.id,
                    organization_id=organization.id,
                    actor_user_id=actor.id,
                    details={
                        "from": membership.role.code,
                        "to": payload.role_code,
                        "user_id": str(membership.user_id),
                    },
                )
                membership.role_id = role.id

        if payload.status is not None:
            new_status = MembershipStatus(payload.status)
            self._guard_last_admin(organization, membership, new_status=new_status)
            if membership.status != new_status:
                action = (
                    "MEMBER_SUSPENDED"
                    if new_status == MembershipStatus.SUSPENDED
                    else "MEMBER_REACTIVATED"
                )
                self.audit.record(
                    action=action,
                    resource_type="membership",
                    resource_id=membership.id,
                    organization_id=organization.id,
                    actor_user_id=actor.id,
                    details={"user_id": str(membership.user_id), "status": new_status.value},
                )
                membership.status = new_status

        self.db.commit()
        return self.memberships.get_for_organization(membership.id, organization.id)

    def remove_member(
        self, organization: Organization, actor: User, membership_id
    ) -> None:
        membership = self.memberships.get_for_organization(membership_id, organization.id)
        if membership is None:
            raise NotFoundError("Membership not found.")
        self._guard_last_admin(organization, membership, removing=True)
        user_id = membership.user_id
        self.memberships.delete(membership)
        self.audit.record(
            action="MEMBER_REMOVED",
            resource_type="membership",
            resource_id=membership_id,
            organization_id=organization.id,
            actor_user_id=actor.id,
            details={"user_id": str(user_id)},
        )
        self.db.commit()

    def accept_invitation(self, user: User, token: str) -> OrganizationMembership:
        invitation = self.invitations.get_by_token_hash(hash_invitation_token(token))
        if invitation is None or invitation.status == InvitationStatus.REVOKED:
            raise InvitationInvalidError()
        if invitation.status == InvitationStatus.ACCEPTED:
            raise InvitationInvalidError("This invitation has already been accepted.")
        if invitation.expires_at <= datetime.now(timezone.utc):
            invitation.status = InvitationStatus.EXPIRED
            self.db.commit()
            raise InvitationExpiredError()
        if invitation.email != user.email:
            raise InvitationInvalidError("This invitation was issued to a different email address.")

        organization = self.organizations.get_by_id(invitation.organization_id)
        if organization is None or organization.status != OrganizationStatus.ACTIVE:
            raise OrganizationSuspendedError()

        role = invitation.role
        membership = self.memberships.get(user.id, invitation.organization_id)
        if membership is None:
            membership = self.memberships.create(
                OrganizationMembership(
                    user_id=user.id,
                    organization_id=invitation.organization_id,
                    role_id=role.id,
                    status=MembershipStatus.ACTIVE,
                )
            )
        elif membership.status == MembershipStatus.ACTIVE:
            raise DuplicateMembershipError()
        else:
            membership.role_id = role.id
            membership.status = MembershipStatus.ACTIVE

        invitation.status = InvitationStatus.ACCEPTED
        invitation.accepted_at = datetime.now(timezone.utc)
        self.audit.record(
            action="INVITATION_ACCEPTED",
            resource_type="invitation",
            resource_id=invitation.id,
            organization_id=invitation.organization_id,
            actor_user_id=user.id,
            details={"email": user.email, "role_code": role.code},
        )
        try:
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise DuplicateMembershipError() from exc
        return self.memberships.get(user.id, invitation.organization_id)

    def list_invitations(
        self,
        organization: Organization,
        *,
        page: int = 1,
        page_size: int = 100,
    ) -> list[OrganizationInvitation]:
        return self.invitations.list_for_organization(
            organization.id, page=page, page_size=page_size
        )

    def revoke_invitation(
        self, organization: Organization, actor: User, invitation_id
    ) -> OrganizationInvitation:
        invitation = self.invitations.get_for_organization(invitation_id, organization.id)
        if invitation is None:
            raise NotFoundError("Invitation not found.")
        if invitation.status != InvitationStatus.PENDING:
            raise InvitationInvalidError("Only pending invitations can be revoked.")
        invitation.status = InvitationStatus.REVOKED
        self.audit.record(
            action="INVITATION_REVOKED",
            resource_type="invitation",
            resource_id=invitation.id,
            organization_id=organization.id,
            actor_user_id=actor.id,
            details={"email": invitation.email},
        )
        self.db.commit()
        self.db.refresh(invitation)
        return invitation
