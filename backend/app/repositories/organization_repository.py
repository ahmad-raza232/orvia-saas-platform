from uuid import UUID

from sqlalchemy.orm import Session

from app.models.organization import Organization


class OrganizationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, organization_id: UUID) -> Organization | None:
        return self.db.get(Organization, organization_id)

    def get_by_slug(self, slug: str) -> Organization | None:
        return self.db.query(Organization).filter(Organization.slug == slug).one_or_none()

    def create(self, organization: Organization) -> Organization:
        self.db.add(organization)
        self.db.flush()
        return organization

    def list_all(self, *, page: int = 1, page_size: int = 100) -> list[Organization]:
        page_size = min(max(page_size, 1), 100)
        page = max(page, 1)
        return (
            self.db.query(Organization)
            .order_by(Organization.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
