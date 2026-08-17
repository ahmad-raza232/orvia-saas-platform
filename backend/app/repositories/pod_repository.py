from uuid import UUID

from sqlalchemy.orm import Session, selectinload

from app.models.proof_of_delivery import ProofOfDelivery


class ProofOfDeliveryRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_shipment_id(self, shipment_id: UUID) -> ProofOfDelivery | None:
        return (
            self.db.query(ProofOfDelivery)
            .options(
                selectinload(ProofOfDelivery.rider),
                selectinload(ProofOfDelivery.evidence),
            )
            .filter(ProofOfDelivery.shipment_id == shipment_id)
            .one_or_none()
        )

    def get_for_organization(
        self, shipment_id: UUID, organization_id: UUID
    ) -> ProofOfDelivery | None:
        return (
            self.db.query(ProofOfDelivery)
            .options(
                selectinload(ProofOfDelivery.rider),
                selectinload(ProofOfDelivery.evidence),
            )
            .filter(
                ProofOfDelivery.shipment_id == shipment_id,
                ProofOfDelivery.organization_id == organization_id,
            )
            .one_or_none()
        )

    def create(self, pod: ProofOfDelivery) -> ProofOfDelivery:
        self.db.add(pod)
        self.db.flush()
        return pod
