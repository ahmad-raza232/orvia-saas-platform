from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.organization import InvitationAcceptRequest, MemberPublic
from app.services.member_service import MemberService

router = APIRouter(prefix="/invitations", tags=["invitations"])


@router.post("/accept", response_model=MemberPublic)
def accept_invitation(
    payload: InvitationAcceptRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MemberPublic:
    membership = MemberService(db).accept_invitation(user, payload.token)
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
