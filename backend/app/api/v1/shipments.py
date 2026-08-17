from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import TenantContext, require_roles
from app.db.database import get_db
from app.models.role import (
    POD_CREATE_ROLES,
    RIDER_ASSIGN_ROLES,
    SHIPMENT_CANCEL_ROLES,
    SHIPMENT_READ_ROLES,
    SHIPMENT_STATUS_ROLES,
    SHIPMENT_WRITE_ROLES,
)
from app.models.shipment import Shipment, ShipmentStatus
from app.models.pod_evidence import PodEvidenceStatus, PodEvidenceType
from app.schemas.pod import (
    CreateProofOfDeliveryRequest,
    PodFileMetadata,
    ProofOfDeliveryResponse,
    ProofOfDeliverySummary,
)
from app.schemas.pod_evidence import PodEvidenceSummary
from app.schemas.customer import ShipmentCustomerSummary
from app.schemas.rider import (
    AssignRiderRequest,
    RiderAssignmentHistoryResponse,
    RiderAssignmentResponse,
    ShipmentRiderSummary,
    UnassignRiderRequest,
)
from app.schemas.shipment import (
    CancelShipmentRequest,
    ChangeShipmentStatusRequest,
    CreateShipmentRequest,
    ParcelInfo,
    PartySnapshot,
    ShipmentHistoryListResponse,
    ShipmentListItem,
    ShipmentListResponse,
    ShipmentResponse,
    ShipmentStatusHistoryResponse,
    UpdateShipmentRequest,
)
from app.services.pod_service import ProofOfDeliveryService
from app.services.shipment_service import ShipmentService

router = APIRouter(prefix="/shipments", tags=["shipments"])

require_shipment_read = require_roles(*SHIPMENT_READ_ROLES)
require_shipment_write = require_roles(*SHIPMENT_WRITE_ROLES)
require_shipment_cancel = require_roles(*SHIPMENT_CANCEL_ROLES)
require_shipment_status = require_roles(*SHIPMENT_STATUS_ROLES)
require_rider_assign = require_roles(*RIDER_ASSIGN_ROLES)
require_pod_create = require_roles(*POD_CREATE_ROLES)


def to_shipment_list_item(item: Shipment) -> ShipmentListItem:
    return ShipmentListItem(
        id=item.id,
        tracking_number=item.tracking_number,
        reference_number=item.reference_number,
        receiver_name=item.receiver_name,
        receiver_city=item.receiver_city,
        service_type=item.service_type,
        status=item.status,
        customer_id=item.customer_id,
        customer_code=item.customer.customer_code if item.customer else None,
        customer_name=item.customer.name if item.customer else None,
        rider_id=item.rider_id,
        rider_code=item.rider.rider_code if item.rider else None,
        rider_name=item.rider.name if item.rider else None,
        created_at=item.created_at,
    )


def to_shipment_response(shipment: Shipment) -> ShipmentResponse:
    return ShipmentResponse(
        id=shipment.id,
        organization_id=shipment.organization_id,
        tracking_number=shipment.tracking_number,
        reference_number=shipment.reference_number,
        sender=PartySnapshot(
            name=shipment.sender_name,
            phone=shipment.sender_phone,
            email=shipment.sender_email,
            address=shipment.sender_address,
            city=shipment.sender_city,
            state=shipment.sender_state,
            country=shipment.sender_country,
            postal_code=shipment.sender_postal_code,
        ),
        receiver=PartySnapshot(
            name=shipment.receiver_name,
            phone=shipment.receiver_phone,
            email=shipment.receiver_email,
            address=shipment.receiver_address,
            city=shipment.receiver_city,
            state=shipment.receiver_state,
            country=shipment.receiver_country,
            postal_code=shipment.receiver_postal_code,
        ),
        parcel=ParcelInfo(
            weight_kg=shipment.weight_kg,
            length_cm=shipment.length_cm,
            width_cm=shipment.width_cm,
            height_cm=shipment.height_cm,
            package_type=shipment.package_type,
            description=shipment.description,
            quantity=shipment.quantity,
        ),
        service_type=shipment.service_type,
        status=shipment.status,
        cod_amount=shipment.cod_amount,
        currency=shipment.currency,
        notes=shipment.notes,
        pickup_at=shipment.pickup_at,
        picked_up_at=shipment.picked_up_at,
        in_transit_at=shipment.in_transit_at,
        out_for_delivery_at=shipment.out_for_delivery_at,
        delivered_at=shipment.delivered_at,
        cancelled_at=shipment.cancelled_at,
        customer_id=shipment.customer_id,
        customer=(
            ShipmentCustomerSummary(
                id=shipment.customer.id,
                customer_code=shipment.customer.customer_code,
                name=shipment.customer.name,
            )
            if shipment.customer
            else None
        ),
        rider_id=shipment.rider_id,
        rider=(
            ShipmentRiderSummary(
                id=shipment.rider.id,
                rider_code=shipment.rider.rider_code,
                name=shipment.rider.name,
            )
            if shipment.rider
            else None
        ),
        pod=(
            ProofOfDeliverySummary(
                pod_id=shipment.proof_of_delivery.id,
                recipient_name=shipment.proof_of_delivery.recipient_name,
                delivered_at=shipment.proof_of_delivery.delivered_at,
                has_signature=bool(shipment.proof_of_delivery.signature_storage_key),
                has_photo=bool(shipment.proof_of_delivery.photo_storage_key),
            )
            if shipment.proof_of_delivery
            else None
        ),
        created_by_user_id=shipment.created_by_user_id,
        created_at=shipment.created_at,
        updated_at=shipment.updated_at,
        status_history=[
            ShipmentStatusHistoryResponse.model_validate(item) for item in shipment.status_history
        ],
    )


@router.post(
    "",
    response_model=ShipmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a shipment",
    description=(
        "Creates a tenant-owned shipment. Organization is taken from the authenticated "
        "membership context, never from the request body. Default status is BOOKED; "
        "pass status=DRAFT to save without booking. CUSTOMER role is not permitted."
    ),
)
def create_shipment(
    payload: CreateShipmentRequest,
    ctx: TenantContext = Depends(require_shipment_write),
    db: Session = Depends(get_db),
) -> ShipmentResponse:
    shipment = ShipmentService(db).create(ctx.organization.id, ctx.user, payload)
    return to_shipment_response(shipment)


@router.get(
    "",
    response_model=ShipmentListResponse,
    summary="List shipments",
    description=(
        "Returns shipments for the current organization only. "
        "Supports pagination, status/tracking/reference filters, and a simple search "
        "across tracking number, reference number, receiver name, and receiver phone. "
        "Status filter accepts DRAFT, BOOKED, PICKED_UP, IN_TRANSIT, OUT_FOR_DELIVERY, "
        "DELIVERED, and CANCELLED."
    ),
)
def list_shipments(
    ctx: TenantContext = Depends(require_shipment_read),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: ShipmentStatus | None = Query(default=None, alias="status"),
    tracking_number: str | None = Query(default=None),
    reference_number: str | None = Query(default=None),
    q: str | None = Query(default=None, description="Search tracking, reference, receiver name, or phone"),
    rider_id: UUID | None = Query(default=None),
) -> ShipmentListResponse:
    items, total = ShipmentService(db).list_for_organization(
        ctx.organization.id,
        page=page,
        page_size=page_size,
        status=status_filter.value if status_filter else None,
        tracking_number=tracking_number,
        reference_number=reference_number,
        search=q,
        rider_id=rider_id,
    )
    return ShipmentListResponse(
        items=[to_shipment_list_item(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get(
    "/{shipment_id}",
    response_model=ShipmentResponse,
    summary="Get a shipment",
    description="Returns a shipment only if it belongs to the current organization. Other tenants receive 404.",
)
def get_shipment(
    shipment_id: UUID,
    ctx: TenantContext = Depends(require_shipment_read),
    db: Session = Depends(get_db),
) -> ShipmentResponse:
    shipment = ShipmentService(db).get_for_organization(shipment_id, ctx.organization.id)
    return to_shipment_response(shipment)


@router.patch(
    "/{shipment_id}",
    response_model=ShipmentResponse,
    summary="Update a shipment",
    description=(
        "DRAFT shipments are fully editable except organization, creator, and tracking number. "
        "BOOKED shipments allow notes, reference_number, customer_id, and receiver phone/email. "
        "Operational and delivered shipments allow notes and reference_number only. "
        "CANCELLED shipments cannot be edited. Status changes go through POST /status or /cancel."
    ),
)
def update_shipment(
    shipment_id: UUID,
    payload: UpdateShipmentRequest,
    ctx: TenantContext = Depends(require_shipment_write),
    db: Session = Depends(get_db),
) -> ShipmentResponse:
    shipment = ShipmentService(db).update(shipment_id, ctx.organization.id, ctx.user, payload)
    return to_shipment_response(shipment)


@router.post(
    "/{shipment_id}/cancel",
    response_model=ShipmentResponse,
    summary="Cancel a shipment",
    description="Cancels a DRAFT or BOOKED shipment via the shared transition service. STAFF cannot cancel.",
)
def cancel_shipment(
    shipment_id: UUID,
    payload: CancelShipmentRequest | None = None,
    ctx: TenantContext = Depends(require_shipment_cancel),
    db: Session = Depends(get_db),
) -> ShipmentResponse:
    note = payload.note if payload else None
    shipment = ShipmentService(db).cancel(shipment_id, ctx.organization.id, ctx.user, note)
    return to_shipment_response(shipment)


@router.post(
    "/{shipment_id}/status",
    response_model=ShipmentResponse,
    summary="Change shipment operational status",
    description=(
        "Advances a shipment along the operational lifecycle. Cancellation is not accepted here; "
        "use POST /cancel. Same-status requests are rejected. CUSTOMER cannot change status."
    ),
)
def change_shipment_status(
    shipment_id: UUID,
    payload: ChangeShipmentStatusRequest,
    ctx: TenantContext = Depends(require_shipment_status),
    db: Session = Depends(get_db),
) -> ShipmentResponse:
    shipment = ShipmentService(db).change_status(
        shipment_id,
        ctx.organization.id,
        ctx.user,
        payload.status.value,
        payload.note,
    )
    return to_shipment_response(shipment)


@router.get(
    "/{shipment_id}/history",
    response_model=ShipmentHistoryListResponse,
    summary="Get shipment status history",
    description="Returns append-only status history for a shipment in the current organization, oldest first.",
)
def get_shipment_history(
    shipment_id: UUID,
    ctx: TenantContext = Depends(require_shipment_read),
    db: Session = Depends(get_db),
) -> ShipmentHistoryListResponse:
    history = ShipmentService(db).list_history(shipment_id, ctx.organization.id)
    return ShipmentHistoryListResponse(
        items=[ShipmentStatusHistoryResponse.model_validate(item) for item in history]
    )


@router.post(
    "/{shipment_id}/assign-rider",
    response_model=ShipmentResponse,
    summary="Assign a rider",
    description="Assigns an ACTIVE tenant rider while the shipment is OUT_FOR_DELIVERY. STAFF cannot assign.",
)
def assign_rider(
    shipment_id: UUID,
    payload: AssignRiderRequest,
    ctx: TenantContext = Depends(require_rider_assign),
    db: Session = Depends(get_db),
) -> ShipmentResponse:
    shipment = ShipmentService(db).assign_rider(
        shipment_id,
        ctx.organization.id,
        ctx.user,
        payload.rider_id,
        payload.note,
    )
    return to_shipment_response(shipment)


@router.post(
    "/{shipment_id}/unassign-rider",
    response_model=ShipmentResponse,
    summary="Unassign the current rider",
    description="Clears the current rider while OUT_FOR_DELIVERY. Historical assignment rows are kept.",
)
def unassign_rider(
    shipment_id: UUID,
    payload: UnassignRiderRequest | None = None,
    ctx: TenantContext = Depends(require_rider_assign),
    db: Session = Depends(get_db),
) -> ShipmentResponse:
    note = payload.note if payload else None
    shipment = ShipmentService(db).unassign_rider(
        shipment_id, ctx.organization.id, ctx.user, note
    )
    return to_shipment_response(shipment)


@router.get(
    "/{shipment_id}/rider-history",
    response_model=RiderAssignmentHistoryResponse,
    summary="Get rider assignment history",
    description="Returns append-only rider assignments for a shipment in the current organization, oldest first.",
)
def get_rider_history(
    shipment_id: UUID,
    ctx: TenantContext = Depends(require_shipment_read),
    db: Session = Depends(get_db),
) -> RiderAssignmentHistoryResponse:
    rows = ShipmentService(db).list_rider_history(shipment_id, ctx.organization.id)
    return RiderAssignmentHistoryResponse(
        items=[
            RiderAssignmentResponse(
                id=row.id,
                shipment_id=row.shipment_id,
                rider_id=row.rider_id,
                rider_code=row.rider.rider_code,
                rider_name=row.rider.name,
                assigned_at=row.assigned_at,
                unassigned_at=row.unassigned_at,
                assigned_by_user_id=row.assigned_by_user_id,
                unassigned_by_user_id=row.unassigned_by_user_id,
                note=row.note,
            )
            for row in rows
        ]
    )


def _pod_file(prefix: str, pod) -> PodFileMetadata | None:
    file_name = getattr(pod, f"{prefix}_file_name")
    if not file_name:
        return None
    return PodFileMetadata(
        file_name=file_name,
        mime_type=getattr(pod, f"{prefix}_mime_type"),
        storage_key=getattr(pod, f"{prefix}_storage_key"),
        url=getattr(pod, f"{prefix}_url"),
        file_size=getattr(pod, f"{prefix}_file_size"),
        checksum=getattr(pod, f"{prefix}_checksum"),
    )


def to_pod_response(pod) -> ProofOfDeliveryResponse:
    signature = _pod_file("signature", pod)
    photo = _pod_file("photo", pod)
    evidence_items = [
        PodEvidenceSummary(
            id=item.id,
            type=item.evidence_type,
            status=item.status,
            content_type=item.content_type,
            size_bytes=item.size_bytes,
            original_filename=item.original_filename,
            uploaded_at=item.uploaded_at,
            expired_at=item.expired_at,
            created_at=item.created_at,
        )
        for item in (pod.evidence or [])
    ]
    uploaded_types = {
        item.evidence_type
        for item in (pod.evidence or [])
        if item.status == PodEvidenceStatus.UPLOADED.value
    }
    return ProofOfDeliveryResponse(
        id=pod.id,
        organization_id=pod.organization_id,
        shipment_id=pod.shipment_id,
        recipient_name=pod.recipient_name,
        delivery_note=pod.delivery_note,
        delivered_at=pod.delivered_at,
        recorded_by_user_id=pod.recorded_by_user_id,
        rider_id=pod.rider_id,
        rider_code=pod.rider.rider_code if pod.rider else None,
        rider_name=pod.rider.name if pod.rider else None,
        signature=signature,
        photo=photo,
        has_signature=signature is not None
        or PodEvidenceType.SIGNATURE.value in uploaded_types,
        has_photo=photo is not None
        or PodEvidenceType.DELIVERY_PHOTO.value in uploaded_types,
        evidence=evidence_items,
        created_at=pod.created_at,
    )


@router.post(
    "/{shipment_id}/pod",
    response_model=ProofOfDeliveryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record proof of delivery",
    description=(
        "Creates the immutable POD for a DELIVERED shipment. Organization, recorder, "
        "and delivered_at come from tenant context and shipment state. STAFF cannot create POD."
    ),
)
def create_proof_of_delivery(
    shipment_id: UUID,
    payload: CreateProofOfDeliveryRequest,
    ctx: TenantContext = Depends(require_pod_create),
    db: Session = Depends(get_db),
) -> ProofOfDeliveryResponse:
    pod = ProofOfDeliveryService(db).create(shipment_id, ctx.organization.id, ctx.user, payload)
    return to_pod_response(pod)


@router.get(
    "/{shipment_id}/pod",
    response_model=ProofOfDeliveryResponse,
    summary="Get proof of delivery",
    description="Returns the POD for a shipment in the current organization. Other tenants receive 404.",
)
def get_proof_of_delivery(
    shipment_id: UUID,
    ctx: TenantContext = Depends(require_shipment_read),
    db: Session = Depends(get_db),
) -> ProofOfDeliveryResponse:
    pod = ProofOfDeliveryService(db).get_for_organization(shipment_id, ctx.organization.id)
    return to_pod_response(pod)
