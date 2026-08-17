from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models.customer import Customer

SORTABLE_COLUMNS = {
    "created_at": Customer.created_at,
    "name": Customer.name,
    "customer_code": Customer.customer_code,
}


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class CustomerRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, customer_id: UUID) -> Customer | None:
        return self.db.get(Customer, customer_id)

    def get_for_organization(self, customer_id: UUID, organization_id: UUID) -> Customer | None:
        return (
            self.db.query(Customer)
            .filter(Customer.id == customer_id, Customer.organization_id == organization_id)
            .one_or_none()
        )

    def get_by_code(self, organization_id: UUID, customer_code: str) -> Customer | None:
        return (
            self.db.query(Customer)
            .filter(
                Customer.organization_id == organization_id,
                Customer.customer_code == customer_code,
            )
            .one_or_none()
        )

    def get_by_email(self, organization_id: UUID, email: str) -> Customer | None:
        return (
            self.db.query(Customer)
            .filter(Customer.organization_id == organization_id, Customer.email == email)
            .one_or_none()
        )

    def create(self, customer: Customer) -> Customer:
        self.db.add(customer)
        self.db.flush()
        return customer

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
    ) -> tuple[list[Customer], int]:
        stmt: Select[tuple[Customer]] = select(Customer).where(
            Customer.organization_id == organization_id
        )
        if status:
            stmt = stmt.where(Customer.status == status)
        if search:
            term = f"%{_escape_like(search.strip())}%"
            stmt = stmt.where(
                or_(
                    Customer.customer_code.ilike(term, escape="\\"),
                    Customer.name.ilike(term, escape="\\"),
                    Customer.email.ilike(term, escape="\\"),
                    Customer.phone.ilike(term, escape="\\"),
                    Customer.company_name.ilike(term, escape="\\"),
                )
            )
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.execute(count_stmt).scalar_one()
        column = SORTABLE_COLUMNS.get(sort, Customer.created_at)
        ordering = column.asc() if order == "asc" else column.desc()
        rows = (
            self.db.execute(
                stmt.order_by(ordering)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .scalars()
            .all()
        )
        return list(rows), int(total)
