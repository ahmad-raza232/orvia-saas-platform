from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.rider import Rider, ShipmentRiderAssignment

SORTABLE_COLUMNS = {
    "created_at": Rider.created_at,
    "name": Rider.name,
    "rider_code": Rider.rider_code,
}


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class RiderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, rider_id: UUID) -> Rider | None:
        return self.db.get(Rider, rider_id)

    def get_for_organization(self, rider_id: UUID, organization_id: UUID) -> Rider | None:
        return (
            self.db.query(Rider)
            .filter(Rider.id == rider_id, Rider.organization_id == organization_id)
            .one_or_none()
        )

    def get_by_code(self, organization_id: UUID, rider_code: str) -> Rider | None:
        return (
            self.db.query(Rider)
            .filter(Rider.organization_id == organization_id, Rider.rider_code == rider_code)
            .one_or_none()
        )

    def create(self, rider: Rider) -> Rider:
        self.db.add(rider)
        self.db.flush()
        return rider

    def list_for_organization(
        self,
        organization_id: UUID,
        *,
        page: int,
        page_size: int,
        status: str | None = None,
        search: str | None = None,
        sort: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[Rider], int]:
        stmt: Select[tuple[Rider]] = select(Rider).where(Rider.organization_id == organization_id)
        if status:
            stmt = stmt.where(Rider.status == status)
        if search:
            term = f"%{_escape_like(search.strip())}%"
            stmt = stmt.where(
                or_(
                    Rider.rider_code.ilike(term, escape="\\"),
                    Rider.name.ilike(term, escape="\\"),
                    Rider.phone.ilike(term, escape="\\"),
                    Rider.email.ilike(term, escape="\\"),
                    Rider.vehicle_number.ilike(term, escape="\\"),
                )
            )
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()
        column = SORTABLE_COLUMNS.get(sort, Rider.created_at)
        ordering = column.asc() if order == "asc" else column.desc()
        rows = (
            self.db.execute(
                stmt.order_by(ordering).offset((page - 1) * page_size).limit(page_size)
            )
            .scalars()
            .all()
        )
        return list(rows), int(total)

    def get_active_assignment(self, shipment_id: UUID) -> ShipmentRiderAssignment | None:
        return (
            self.db.query(ShipmentRiderAssignment)
            .filter(
                ShipmentRiderAssignment.shipment_id == shipment_id,
                ShipmentRiderAssignment.unassigned_at.is_(None),
            )
            .one_or_none()
        )

    def add_assignment(self, assignment: ShipmentRiderAssignment) -> ShipmentRiderAssignment:
        self.db.add(assignment)
        self.db.flush()
        return assignment

    def list_assignments(self, organization_id: UUID, shipment_id: UUID) -> list[ShipmentRiderAssignment]:
        return (
            self.db.query(ShipmentRiderAssignment)
            .options(selectinload(ShipmentRiderAssignment.rider))
            .filter(
                ShipmentRiderAssignment.organization_id == organization_id,
                ShipmentRiderAssignment.shipment_id == shipment_id,
            )
            .order_by(ShipmentRiderAssignment.assigned_at.asc())
            .all()
        )
