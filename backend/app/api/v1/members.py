from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import TenantContext, require_tenant_admin
from app.db.database import get_db
from app.models.invitation import OrganizationInvitation
from app.models.membership import OrganizationMembership
from app.schemas.organization import (
    InvitationCreatedResponse,
    InvitationPublic,
    MemberInviteRequest,
    MemberPublic,
    MemberUpdateRequest,
)
from app.services.member_service import MemberService

router = APIRouter(prefix="/organizations/me", tags=["members"])


def _member_public(membership: OrganizationMembership) -> MemberPublic:
    return MemberPublic(
        id=membership.id,
        user_id=membership.user_id,
        email=membership.user.email,
        first_name=membership.user.first_name,
        last_name=membership.user.last_name,
        role_code=membership.role.code,
        status=membership.status.value,
        created_at=membership.created_at,
    )


def _invitation_public(invitation: OrganizationInvitation) -> InvitationPublic:
    return InvitationPublic(
        id=invitation.id,
        organization_id=invitation.organization_id,
        email=invitation.email,
        role_code=invitation.role.code,
        status=invitation.status.value,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
    )


@router.get("/members", response_model=list[MemberPublic])
def list_members(
    ctx: TenantContext = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
) -> list[MemberPublic]:
    return [
        _member_public(item)
        for item in MemberService(db).list_members(
            ctx.organization, page=page, page_size=page_size
        )
    ]


@router.post("/members", response_model=InvitationCreatedResponse, status_code=status.HTTP_201_CREATED)
def invite_member(
    payload: MemberInviteRequest,
    ctx: TenantContext = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
) -> InvitationCreatedResponse:
    invitation = MemberService(db).invite(ctx.organization, ctx.user, payload)
    return InvitationCreatedResponse(**_invitation_public(invitation).model_dump())


@router.patch("/members/{membership_id}", response_model=MemberPublic)
def update_member(
    membership_id: UUID,
    payload: MemberUpdateRequest,
    ctx: TenantContext = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
) -> MemberPublic:
    membership = MemberService(db).update_member(ctx.organization, ctx.user, membership_id, payload)
    return _member_public(membership)


@router.delete("/members/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    membership_id: UUID,
    ctx: TenantContext = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
) -> None:
    MemberService(db).remove_member(ctx.organization, ctx.user, membership_id)


@router.get("/invitations", response_model=list[InvitationPublic])
def list_invitations(
    ctx: TenantContext = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
) -> list[InvitationPublic]:
    return [
        _invitation_public(item)
        for item in MemberService(db).list_invitations(
            ctx.organization, page=page, page_size=page_size
        )
    ]
