from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record(
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: UUID | str | None = None,
        organization_id: UUID | None = None,
        actor_user_id: UUID | None = None,
        details: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            details=details,
        )
        self.db.add(entry)
        self.db.flush()
        return entry

    def get_for_organization(self, audit_id: UUID, organization_id: UUID) -> AuditLog | None:
        row = self.db.get(AuditLog, audit_id)
        if row is None or row.organization_id != organization_id:
            return None
        return row

    def list_for_organization(
        self,
        organization_id: UUID,
        *,
        page: int = 1,
        page_size: int = 100,
    ) -> list[AuditLog]:
        page_size = min(max(page_size, 1), 100)
        page = max(page, 1)
        return (
            self.db.query(AuditLog)
            .filter(AuditLog.organization_id == organization_id)
            .order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
