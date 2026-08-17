from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import TenantContext, get_current_user, get_tenant_context, require_tenant_admin
from app.db.database import get_db
from app.models.user import User
from app.schemas.organization import OrganizationCreate, OrganizationPublic, OrganizationUpdate
from app.services.organization_service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("", response_model=OrganizationPublic, status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: OrganizationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrganizationPublic:
    organization = OrganizationService(db).create_for_user(user, payload)
    return OrganizationPublic.model_validate(organization)


@router.get("/me", response_model=OrganizationPublic)
def get_my_organization(ctx: TenantContext = Depends(get_tenant_context)) -> OrganizationPublic:
    return OrganizationPublic.model_validate(ctx.organization)


@router.patch("/me", response_model=OrganizationPublic)
def update_my_organization(
    payload: OrganizationUpdate,
    ctx: TenantContext = Depends(require_tenant_admin),
    db: Session = Depends(get_db),
) -> OrganizationPublic:
    organization = OrganizationService(db).update(ctx.organization, payload, actor=ctx.user)
    return OrganizationPublic.model_validate(organization)
