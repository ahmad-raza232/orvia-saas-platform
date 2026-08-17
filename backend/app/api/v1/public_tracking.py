"""Unauthenticated Softorica SaaS public tracking (ORVIA-XXXXXXXXXX).

Legacy GoBurq GBQ tracking remains on the separate goburq.com API.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import InvalidTrackingNumberError, NotFoundError
from app.core.tracking import is_orvia_tracking_number, normalize_tracking_number
from app.db.database import get_db
from app.models.shipment import Shipment
from app.schemas.public_tracking import PublicTrackingHistoryItem, PublicTrackingResponse

router = APIRouter(prefix="/public", tags=["public-tracking"])


@router.get(
    "/tracking/{tracking_number}",
    response_model=PublicTrackingResponse,
    summary="Public Softorica shipment tracking",
    description=(
        "Lookup a SaaS shipment by ORVIA-XXXXXXXXXX tracking number. "
        "No authentication required. Returns sanitized operational fields only. "
        "Legacy GBQ IDs are not served here."
    ),
)
def public_track_shipment(
    tracking_number: str,
    db: Session = Depends(get_db),
) -> PublicTrackingResponse:
    cleaned = normalize_tracking_number(tracking_number)
    if cleaned.startswith("ORVIA-") and not is_orvia_tracking_number(cleaned):
        raise InvalidTrackingNumberError()
    if not is_orvia_tracking_number(cleaned):
        raise NotFoundError("Shipment not found.")

    shipment = (
        db.query(Shipment)
        .options(
            joinedload(Shipment.status_history),
            joinedload(Shipment.proof_of_delivery),
        )
        .filter(Shipment.tracking_number == cleaned)
        .one_or_none()
    )
    if shipment is None:
        raise NotFoundError("Shipment not found.")

    history_rows = sorted(shipment.status_history or [], key=lambda row: row.created_at)
    return PublicTrackingResponse(
        tracking_number=shipment.tracking_number,
        status=shipment.status,
        service_type=shipment.service_type,
        origin_city=shipment.sender_city,
        destination_city=shipment.receiver_city,
        receiver_name=shipment.receiver_name,
        reference_number=shipment.reference_number,
        pieces=shipment.quantity,
        package_type=shipment.package_type,
        created_at=shipment.created_at,
        picked_up_at=shipment.picked_up_at,
        in_transit_at=shipment.in_transit_at,
        out_for_delivery_at=shipment.out_for_delivery_at,
        delivered_at=shipment.delivered_at,
        cancelled_at=shipment.cancelled_at,
        has_pod=shipment.proof_of_delivery is not None,
        history=[
            PublicTrackingHistoryItem(
                status=row.new_status,
                previous_status=row.previous_status,
                note=row.note,
                created_at=row.created_at,
            )
            for row in history_rows
        ],
    )
