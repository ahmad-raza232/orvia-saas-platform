from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, InvalidTokenError as JWTInvalidTokenError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ForbiddenError,
    InvalidTokenError,
    MissingMembershipError,
    OrganizationSuspendedError,
    UnauthorizedError,
)
from app.core.security import decode_access_token
from app.db.database import get_db
from app.models.membership import MembershipStatus, OrganizationMembership
from app.models.organization import Organization, OrganizationStatus
from app.models.role import TENANT_ADMIN
from app.models.user import User
from app.repositories.invitation_repository import PlatformAdminRepository
from app.repositories.membership_repository import MembershipRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class TenantContext:
    user: User
    organization: Organization
    membership: OrganizationMembership

    @property
    def role_code(self) -> str:
        return self.membership.role.code


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise UnauthorizedError()
    try:
        payload = decode_access_token(credentials.credentials)
    except (ExpiredSignatureError, JWTInvalidTokenError):
        raise InvalidTokenError() from None
    subject = payload.get("sub")
    if not subject:
        raise InvalidTokenError()
    try:
        user_id = UUID(str(subject))
    except ValueError as exc:
        raise InvalidTokenError() from exc
    user = UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise InvalidTokenError()
    return user


def _resolve_organization_id(
    user: User,
    token_org: str | None,
    header_org: str | None,
    db: Session,
) -> UUID:
    """
    Organization is resolved from authenticated membership, never from
    untrusted client input such as query parameters or localStorage.

    Optional X-Organization-Id is only accepted when the caller already has
    an active membership in that organization (multi-org users).
    """
    memberships = MembershipRepository(db).list_active_for_user(user.id)
    if not memberships:
        raise MissingMembershipError()

    allowed = {membership.organization_id: membership for membership in memberships}

    if header_org:
        try:
            requested = UUID(header_org)
        except ValueError as exc:
            raise ForbiddenError("Invalid organization context.") from exc
        if requested not in allowed:
            raise ForbiddenError("You are not a member of this organization.")
        return requested

    if token_org:
        try:
            claimed = UUID(token_org)
        except ValueError as exc:
            raise InvalidTokenError() from exc
        if claimed in allowed:
            return claimed

    if len(memberships) == 1:
        return memberships[0].organization_id

    raise ForbiddenError("Organization context could not be determined from membership.")


def get_tenant_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_organization_id: str | None = Header(default=None, alias="X-Organization-Id"),
    db: Session = Depends(get_db),
) -> TenantContext:
    user = get_current_user(credentials=credentials, db=db)
    token_org = None
    if credentials is not None:
        try:
            token_org = decode_access_token(credentials.credentials).get("org")
        except (ExpiredSignatureError, JWTInvalidTokenError):
            raise InvalidTokenError() from None

    organization_id = _resolve_organization_id(user, token_org, x_organization_id, db)
    membership = MembershipRepository(db).get(user.id, organization_id)
    if membership is None or membership.status != MembershipStatus.ACTIVE:
        raise MissingMembershipError()

    organization = OrganizationRepository(db).get_by_id(organization_id)
    if organization is None:
        raise ForbiddenError("Organization is not available.")
    if organization.status != OrganizationStatus.ACTIVE:
        raise OrganizationSuspendedError()

    return TenantContext(user=user, organization=organization, membership=membership)


def require_roles(*role_codes: str):
    def dependency(ctx: TenantContext = Depends(get_tenant_context)) -> TenantContext:
        if ctx.role_code not in role_codes:
            raise ForbiddenError()
        return ctx

    return dependency


require_tenant_admin = require_roles(TENANT_ADMIN)


def require_platform_admin(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    grant = PlatformAdminRepository(db).get_by_user_id(user.id)
    if grant is None:
        raise ForbiddenError("Platform administrator access is required.")
    return user
