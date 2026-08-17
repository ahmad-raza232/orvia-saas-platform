from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import require_platform_admin
from app.core.exceptions import NotFoundError
from app.db.database import get_db
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.organization import OrganizationPublic
from app.services.organization_service import OrganizationService

router = APIRouter(prefix="/platform", tags=["platform"])


@router.get("/organizations", response_model=list[OrganizationPublic])
def list_organizations(
    _: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=100),
) -> list[OrganizationPublic]:
    return [
        OrganizationPublic.model_validate(item)
        for item in OrganizationRepository(db).list_all(page=page, page_size=page_size)
    ]


@router.get("/organizations/{organization_id}", response_model=OrganizationPublic)
def get_organization(
    organization_id: UUID,
    _: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> OrganizationPublic:
    organization = OrganizationRepository(db).get_by_id(organization_id)
    if organization is None:
        raise NotFoundError("Organization not found.")
    return OrganizationPublic.model_validate(organization)


@router.post("/organizations/{organization_id}/suspend", response_model=OrganizationPublic)
def suspend_organization(
    organization_id: UUID,
    actor: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> OrganizationPublic:
    organization = OrganizationRepository(db).get_by_id(organization_id)
    if organization is None:
        raise NotFoundError("Organization not found.")
    return OrganizationPublic.model_validate(
        OrganizationService(db).suspend(organization, actor=actor)
    )


@router.post("/organizations/{organization_id}/reactivate", response_model=OrganizationPublic)
def reactivate_organization(
    organization_id: UUID,
    actor: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> OrganizationPublic:
    organization = OrganizationRepository(db).get_by_id(organization_id)
    if organization is None:
        raise NotFoundError("Organization not found.")
    return OrganizationPublic.model_validate(
        OrganizationService(db).reactivate(organization, actor=actor)
    )
