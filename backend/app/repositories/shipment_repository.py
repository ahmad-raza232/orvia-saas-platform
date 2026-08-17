from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.shipment import Shipment, ShipmentStatusHistory


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class ShipmentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, shipment_id: UUID) -> Shipment | None:
        return (
            self.db.query(Shipment)
            .options(
                selectinload(Shipment.status_history),
                selectinload(Shipment.customer),
                selectinload(Shipment.rider),
                selectinload(Shipment.proof_of_delivery),
            )
            .filter(Shipment.id == shipment_id)
            .one_or_none()
        )

    def get_for_organization(self, shipment_id: UUID, organization_id: UUID) -> Shipment | None:
        return (
            self.db.query(Shipment)
            .options(
                selectinload(Shipment.status_history),
                selectinload(Shipment.customer),
                selectinload(Shipment.rider),
                selectinload(Shipment.proof_of_delivery),
            )
            .filter(Shipment.id == shipment_id, Shipment.organization_id == organization_id)
            .one_or_none()
        )

    def get_by_id_for_update(self, shipment_id: UUID) -> Shipment | None:
        return (
            self.db.query(Shipment)
            .filter(Shipment.id == shipment_id)
            .with_for_update()
            .one_or_none()
        )

    def get_for_organization_for_update(
        self, shipment_id: UUID, organization_id: UUID
    ) -> Shipment | None:
        return (
            self.db.query(Shipment)
            .filter(Shipment.id == shipment_id, Shipment.organization_id == organization_id)
            .with_for_update()
            .one_or_none()
        )

    def get_by_tracking_number(self, tracking_number: str) -> Shipment | None:
        return (
            self.db.query(Shipment)
            .filter(Shipment.tracking_number == tracking_number)
            .one_or_none()
        )

    def create(self, shipment: Shipment) -> Shipment:
        self.db.add(shipment)
        self.db.flush()
        return shipment

    def add_history(self, history: ShipmentStatusHistory) -> ShipmentStatusHistory:
        self.db.add(history)
        self.db.flush()
        return history

    def list_for_organization(
        self,
        organization_id: UUID,
        *,
        page: int,
        page_size: int,
        status: str | None = None,
        tracking_number: str | None = None,
        reference_number: str | None = None,
        search: str | None = None,
        rider_id: UUID | None = None,
    ) -> tuple[list[Shipment], int]:
        stmt: Select[tuple[Shipment]] = (
            select(Shipment)
            .options(selectinload(Shipment.customer), selectinload(Shipment.rider))
            .where(Shipment.organization_id == organization_id)
        )
        if status:
            stmt = stmt.where(Shipment.status == status)
        if rider_id:
            stmt = stmt.where(Shipment.rider_id == rider_id)
        if tracking_number:
            stmt = stmt.where(Shipment.tracking_number == tracking_number.strip())
        if reference_number:
            stmt = stmt.where(Shipment.reference_number == reference_number.strip())
        if search:
            term = f"%{_escape_like(search.strip())}%"
            stmt = stmt.where(
                or_(
                    Shipment.tracking_number.ilike(term, escape="\\"),
                    Shipment.reference_number.ilike(term, escape="\\"),
                    Shipment.receiver_name.ilike(term, escape="\\"),
                    Shipment.receiver_phone.ilike(term, escape="\\"),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()
        rows = (
            self.db.execute(
                stmt.order_by(Shipment.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .scalars()
            .all()
        )
        return list(rows), int(total)

    def list_for_customer(
        self,
        organization_id: UUID,
        customer_id: UUID,
        *,
        page: int,
        page_size: int,
    ) -> tuple[list[Shipment], int]:
        stmt: Select[tuple[Shipment]] = (
            select(Shipment)
            .options(selectinload(Shipment.customer), selectinload(Shipment.rider))
            .where(
                Shipment.organization_id == organization_id,
                Shipment.customer_id == customer_id,
            )
        )
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()
        rows = (
            self.db.execute(
                stmt.order_by(Shipment.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .scalars()
            .all()
        )
        return list(rows), int(total)

    def list_for_rider(
        self,
        organization_id: UUID,
        rider_id: UUID,
        *,
        page: int,
        page_size: int,
        status: str | None = None,
        search: str | None = None,
        sort: str = "created_at",
        order: str = "desc",
    ) -> tuple[list[Shipment], int]:
        stmt: Select[tuple[Shipment]] = (
            select(Shipment)
            .options(selectinload(Shipment.customer), selectinload(Shipment.rider))
            .where(
                Shipment.organization_id == organization_id,
                Shipment.rider_id == rider_id,
            )
        )
        if status:
            stmt = stmt.where(Shipment.status == status)
        if search:
            term = f"%{_escape_like(search.strip())}%"
            stmt = stmt.where(
                or_(
                    Shipment.tracking_number.ilike(term, escape="\\"),
                    Shipment.reference_number.ilike(term, escape="\\"),
                    Shipment.receiver_name.ilike(term, escape="\\"),
                    Shipment.receiver_phone.ilike(term, escape="\\"),
                )
            )
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()
        columns = {
            "created_at": Shipment.created_at,
            "tracking_number": Shipment.tracking_number,
            "status": Shipment.status,
        }
        column = columns.get(sort, Shipment.created_at)
        ordering = column.asc() if order == "asc" else column.desc()
        rows = (
            self.db.execute(
                stmt.order_by(ordering).offset((page - 1) * page_size).limit(page_size)
            )
            .scalars()
            .all()
        )
        return list(rows), int(total)
