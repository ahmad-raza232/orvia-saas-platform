from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from jwt import ExpiredSignatureError, InvalidTokenError as JWTInvalidTokenError
from sqlalchemy.orm import Session

from app.core.deps import bearer_scheme, get_current_user
from app.core.exceptions import (
    ForbiddenError,
    InvalidCredentialsError,
    InvalidTokenError,
    OrganizationSuspendedError,
    TooManyRequestsError,
)
from app.core.security import create_access_token, decode_access_token
from app.db.database import get_db
from app.models.membership import MembershipStatus
from app.models.organization import OrganizationStatus
from app.models.user import User
from app.repositories.membership_repository import MembershipRepository
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    MembershipPublic,
    RegisterRequest,
    TokenResponse,
    UserPublic,
)
from app.schemas.organization import (
    SwitchOrganizationRequest,
    UserOrganizationMembership,
    UserOrganizationPublic,
)
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService
from app.services.login_rate_limiter import LoginRateLimiter

router = APIRouter(prefix="/auth", tags=["auth"])


def _primary_org_id(user: User, db: Session) -> str | None:
    memberships = MembershipRepository(db).list_active_for_user(user.id)
    if len(memberships) == 1:
        return str(memberships[0].organization_id)
    return None


def _token_org_id(credentials: HTTPAuthorizationCredentials | None) -> str | None:
    if credentials is None:
        return None
    try:
        return decode_access_token(credentials.credentials).get("org")
    except (ExpiredSignatureError, JWTInvalidTokenError):
        raise InvalidTokenError() from None


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    return AuthService(db).register(payload)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    limiter = LoginRateLimiter(db)
    limiter.precheck(payload.email)
    user = AuthService(db).authenticate(payload.email, payload.password)
    if user is None:
        AuditService(db).record(
            action="LOGIN_FAILED",
            resource_type="auth",
            details={"email": payload.email},
        )
        try:
            limiter.register_failure(payload.email)
        except TooManyRequestsError:
            raise
        db.commit()
        raise InvalidCredentialsError()
    limiter.clear(payload.email)
    AuditService(db).record(
        action="LOGIN_SUCCEEDED",
        resource_type="auth",
        resource_id=user.id,
        actor_user_id=user.id,
        details={"email": payload.email},
    )
    db.commit()
    token = create_access_token(subject=str(user.id), organization_id=_primary_org_id(user, db))
    return TokenResponse(access_token=token)


@router.get("/me", response_model=MeResponse)
def me(
    user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> MeResponse:
    memberships = MembershipRepository(db).list_for_user(user.id)
    active = [item for item in memberships if item.status == MembershipStatus.ACTIVE]
    claimed = _token_org_id(credentials)
    current_org = None
    if claimed:
        current_org = next(
            (item.organization_id for item in active if str(item.organization_id) == claimed),
            None,
        )
    if current_org is None and len(active) == 1:
        current_org = active[0].organization_id
    return MeResponse(
        user=UserPublic.model_validate(user),
        memberships=[
            MembershipPublic(
                id=item.id,
                organization_id=item.organization_id,
                role_code=item.role.code,
                status=item.status.value,
            )
            for item in memberships
        ],
        current_organization_id=current_org,
    )


@router.get("/organizations", response_model=list[UserOrganizationPublic])
def list_my_organizations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    memberships = MembershipRepository(db).list_for_user(user.id)
    return [
        UserOrganizationPublic(
            id=item.organization.id,
            name=item.organization.name,
            slug=item.organization.slug,
            status=item.organization.status,
            membership=UserOrganizationMembership(
                id=item.id,
                role_code=item.role.code,
                status=item.status.value,
            ),
        )
        for item in memberships
    ]


@router.post("/switch-organization", response_model=TokenResponse)
def switch_organization(
    payload: SwitchOrganizationRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TokenResponse:
    membership = MembershipRepository(db).get(user.id, payload.organization_id)
    if membership is None or membership.status != MembershipStatus.ACTIVE:
        raise ForbiddenError("You are not an active member of this organization.")
    organization = OrganizationRepository(db).get_by_id(payload.organization_id)
    if organization is None:
        raise ForbiddenError("You are not an active member of this organization.")
    if organization.status != OrganizationStatus.ACTIVE:
        raise OrganizationSuspendedError()
    AuditService(db).record(
        action="ORGANIZATION_SWITCHED",
        resource_type="organization",
        resource_id=organization.id,
        organization_id=organization.id,
        actor_user_id=user.id,
        details={"slug": organization.slug},
    )
    db.commit()
    token = create_access_token(subject=str(user.id), organization_id=str(organization.id))
    return TokenResponse(access_token=token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout() -> None:
    """Stateless JWT logout. Clients must discard the access token."""
    return None
