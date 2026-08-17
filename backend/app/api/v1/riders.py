from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.v1.shipments import to_shipment_list_item
from app.core.deps import TenantContext, require_roles
from app.db.database import get_db
from app.models.rider import Rider, RiderStatus
from app.models.role import RIDER_READ_ROLES, RIDER_STATUS_ROLES, RIDER_WRITE_ROLES
from app.models.shipment import ShipmentStatus
from app.schemas.rider import (
    CreateRiderRequest,
    RiderListItem,
    RiderListResponse,
    RiderResponse,
    UpdateRiderRequest,
)
from app.schemas.shipment import ShipmentListResponse
from app.services.rider_service import RiderService
from app.services.shipment_service import ShipmentService

router = APIRouter(prefix="/riders", tags=["riders"])

require_rider_read = require_roles(*RIDER_READ_ROLES)
require_rider_write = require_roles(*RIDER_WRITE_ROLES)
require_rider_status = require_roles(*RIDER_STATUS_ROLES)


def to_rider_response(rider: Rider, summary: dict | None = None) -> RiderResponse:
    data = RiderResponse.model_validate(rider)
    if summary:
        data.assigned_shipment_count = summary["assigned_shipment_count"]
        data.out_for_delivery_count = summary["out_for_delivery_count"]
    return data


@router.post(
    "",
    response_model=RiderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a rider",
    description="Creates a tenant-owned rider. Organization is taken from membership context. STAFF cannot create.",
)
def create_rider(
    payload: CreateRiderRequest,
    ctx: TenantContext = Depends(require_rider_write),
    db: Session = Depends(get_db),
) -> RiderResponse:
    rider = RiderService(db).create(ctx.organization.id, ctx.user, payload)
    return to_rider_response(rider)


@router.get(
    "",
    response_model=RiderListResponse,
    summary="List riders",
    description="Returns riders for the current organization only.",
)
def list_riders(
    ctx: TenantContext = Depends(require_rider_read),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: RiderStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None),
    sort: Literal["created_at", "name", "rider_code"] = Query("created_at"),
    order: Literal["asc", "desc"] = Query("desc"),
) -> RiderListResponse:
    items, total = RiderService(db).list_for_organization(
        ctx.organization.id,
        page=page,
        page_size=page_size,
        status=status_filter.value if status_filter else None,
        search=q,
        sort=sort,
        order=order,
    )
    return RiderListResponse(
        items=[
            RiderListItem(
                id=item.id,
                rider_code=item.rider_code,
                name=item.name,
                phone=item.phone,
                email=item.email,
                vehicle_type=item.vehicle_type,
                vehicle_number=item.vehicle_number,
                status=item.status,
                created_at=item.created_at,
            )
            for item in items
        ],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get(
    "/{rider_id}",
    response_model=RiderResponse,
    summary="Get a rider",
)
def get_rider(
    rider_id: UUID,
    ctx: TenantContext = Depends(require_rider_read),
    db: Session = Depends(get_db),
) -> RiderResponse:
    service = RiderService(db)
    rider = service.get_for_organization(rider_id, ctx.organization.id)
    summary = service.assignment_summary(rider.id, ctx.organization.id)
    return to_rider_response(rider, summary)


@router.patch(
    "/{rider_id}",
    response_model=RiderResponse,
    summary="Update a rider",
)
def update_rider(
    rider_id: UUID,
    payload: UpdateRiderRequest,
    ctx: TenantContext = Depends(require_rider_write),
    db: Session = Depends(get_db),
) -> RiderResponse:
    rider = RiderService(db).update(rider_id, ctx.organization.id, ctx.user, payload)
    return to_rider_response(rider)


@router.post(
    "/{rider_id}/deactivate",
    response_model=RiderResponse,
    summary="Deactivate a rider",
    description="Soft-deactivates a rider. Current shipment assignments are left unchanged. New assignments are blocked.",
)
def deactivate_rider(
    rider_id: UUID,
    ctx: TenantContext = Depends(require_rider_status),
    db: Session = Depends(get_db),
) -> RiderResponse:
    rider = RiderService(db).deactivate(rider_id, ctx.organization.id, ctx.user)
    return to_rider_response(rider)


@router.post(
    "/{rider_id}/reactivate",
    response_model=RiderResponse,
    summary="Reactivate a rider",
)
def reactivate_rider(
    rider_id: UUID,
    ctx: TenantContext = Depends(require_rider_status),
    db: Session = Depends(get_db),
) -> RiderResponse:
    rider = RiderService(db).reactivate(rider_id, ctx.organization.id, ctx.user)
    return to_rider_response(rider)


@router.get(
    "/{rider_id}/shipments",
    response_model=ShipmentListResponse,
    summary="List shipments currently assigned to a rider",
    description="Returns current-assignment shipments for this rider in the current organization only.",
)
def list_rider_shipments(
    rider_id: UUID,
    ctx: TenantContext = Depends(require_rider_read),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: ShipmentStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None),
    sort: Literal["created_at", "tracking_number", "status"] = Query("created_at"),
    order: Literal["asc", "desc"] = Query("desc"),
) -> ShipmentListResponse:
    RiderService(db).get_for_organization(rider_id, ctx.organization.id)
    items, total = ShipmentService(db).list_for_rider(
        ctx.organization.id,
        rider_id,
        page=page,
        page_size=page_size,
        status=status_filter.value if status_filter else None,
        search=q,
        sort=sort,
        order=order,
    )
    return ShipmentListResponse(
        items=[to_shipment_list_item(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )
