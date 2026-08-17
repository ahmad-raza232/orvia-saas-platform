from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.pod_evidence import PodEvidence, PodEvidenceStatus


class PodEvidenceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, evidence_id: UUID) -> PodEvidence | None:
        return (
            self.db.query(PodEvidence)
            .filter(PodEvidence.id == evidence_id)
            .one_or_none()
        )

    def get_for_organization(
        self, evidence_id: UUID, organization_id: UUID
    ) -> PodEvidence | None:
        return (
            self.db.query(PodEvidence)
            .filter(
                PodEvidence.id == evidence_id,
                PodEvidence.organization_id == organization_id,
            )
            .one_or_none()
        )

    def get_by_id_for_update(self, evidence_id: UUID) -> PodEvidence | None:
        return (
            self.db.query(PodEvidence)
            .filter(PodEvidence.id == evidence_id)
            .with_for_update()
            .one_or_none()
        )

    def get_for_organization_for_update(
        self, evidence_id: UUID, organization_id: UUID
    ) -> PodEvidence | None:
        return (
            self.db.query(PodEvidence)
            .filter(
                PodEvidence.id == evidence_id,
                PodEvidence.organization_id == organization_id,
            )
            .with_for_update()
            .one_or_none()
        )

    def list_for_pod(self, pod_id: UUID, organization_id: UUID | None = None) -> list[PodEvidence]:
        query = self.db.query(PodEvidence).filter(PodEvidence.pod_id == pod_id)
        if organization_id is not None:
            query = query.filter(PodEvidence.organization_id == organization_id)
        return query.order_by(PodEvidence.created_at.asc()).all()

    def get_uploaded_for_type(self, pod_id: UUID, evidence_type: str) -> PodEvidence | None:
        return (
            self.db.query(PodEvidence)
            .filter(
                PodEvidence.pod_id == pod_id,
                PodEvidence.evidence_type == evidence_type,
                PodEvidence.status == PodEvidenceStatus.UPLOADED.value,
            )
            .one_or_none()
        )

    def claim_stale_pending(self, *, cutoff: datetime, limit: int) -> list[PodEvidence]:
        return (
            self.db.query(PodEvidence)
            .filter(
                PodEvidence.status == PodEvidenceStatus.PENDING.value,
                PodEvidence.created_at <= cutoff,
            )
            .order_by(PodEvidence.created_at.asc(), PodEvidence.id.asc())
            .with_for_update(skip_locked=True)
            .limit(limit)
            .all()
        )

    def create(self, evidence: PodEvidence) -> PodEvidence:
        self.db.add(evidence)
        self.db.flush()
        return evidence
