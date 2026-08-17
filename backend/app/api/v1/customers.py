from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import TenantContext, require_roles
from app.db.database import get_db
from app.models.customer import Customer, CustomerStatus
from app.models.role import CUSTOMER_READ_ROLES, CUSTOMER_STATUS_ROLES, CUSTOMER_WRITE_ROLES
from app.schemas.customer import (
    CreateCustomerRequest,
    CustomerListItem,
    CustomerListResponse,
    CustomerResponse,
    UpdateCustomerRequest,
)
from app.api.v1.shipments import to_shipment_list_item
from app.schemas.shipment import CustomerShipmentListResponse
from app.services.customer_service import CustomerService
from app.services.shipment_service import ShipmentService

router = APIRouter(prefix="/customers", tags=["customers"])

require_customer_read = require_roles(*CUSTOMER_READ_ROLES)
require_customer_write = require_roles(*CUSTOMER_WRITE_ROLES)
require_customer_status = require_roles(*CUSTOMER_STATUS_ROLES)


def to_customer_response(customer: Customer, summary: dict | None = None) -> CustomerResponse:
    data = CustomerResponse.model_validate(customer)
    if summary:
        data.shipment_count = summary["shipment_count"]
        data.active_shipment_count = summary["active_shipment_count"]
        data.latest_shipment_at = summary["latest_shipment_at"]
    return data


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a customer",
    description="Creates a tenant-owned customer. Organization is taken from membership context.",
)
def create_customer(
    payload: CreateCustomerRequest,
    ctx: TenantContext = Depends(require_customer_write),
    db: Session = Depends(get_db),
) -> CustomerResponse:
    customer = CustomerService(db).create(ctx.organization.id, ctx.user, payload)
    return to_customer_response(customer)


@router.get(
    "",
    response_model=CustomerListResponse,
    summary="List customers",
    description="Returns customers for the current organization only. Supports pagination, status filter, and search.",
)
def list_customers(
    ctx: TenantContext = Depends(require_customer_read),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: CustomerStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None),
    sort: Literal["created_at", "name", "customer_code"] = Query("created_at"),
    order: Literal["asc", "desc"] = Query("desc"),
) -> CustomerListResponse:
    items, total = CustomerService(db).list_for_organization(
        ctx.organization.id,
        page=page,
        page_size=page_size,
        status=status_filter.value if status_filter else None,
        search=q,
        sort=sort,
        order=order,
    )
    return CustomerListResponse(
        items=[
            CustomerListItem(
                id=item.id,
                customer_code=item.customer_code,
                name=item.name,
                email=item.email,
                phone=item.phone,
                company_name=item.company_name,
                city=item.city,
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
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Get a customer",
    description="Returns a customer only if it belongs to the current organization.",
)
def get_customer(
    customer_id: UUID,
    ctx: TenantContext = Depends(require_customer_read),
    db: Session = Depends(get_db),
) -> CustomerResponse:
    service = CustomerService(db)
    customer = service.get_for_organization(customer_id, ctx.organization.id)
    summary = service.shipment_summary(customer.id, ctx.organization.id)
    return to_customer_response(customer, summary)


@router.patch(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Update a customer",
)
def update_customer(
    customer_id: UUID,
    payload: UpdateCustomerRequest,
    ctx: TenantContext = Depends(require_customer_write),
    db: Session = Depends(get_db),
) -> CustomerResponse:
    customer = CustomerService(db).update(customer_id, ctx.organization.id, ctx.user, payload)
    return to_customer_response(customer)


@router.post(
    "/{customer_id}/deactivate",
    response_model=CustomerResponse,
    summary="Deactivate a customer",
    description="Soft-deactivates a customer. Existing shipments remain. STAFF cannot deactivate.",
)
def deactivate_customer(
    customer_id: UUID,
    ctx: TenantContext = Depends(require_customer_status),
    db: Session = Depends(get_db),
) -> CustomerResponse:
    customer = CustomerService(db).deactivate(customer_id, ctx.organization.id, ctx.user)
    return to_customer_response(customer)


@router.post(
    "/{customer_id}/reactivate",
    response_model=CustomerResponse,
    summary="Reactivate a customer",
)
def reactivate_customer(
    customer_id: UUID,
    ctx: TenantContext = Depends(require_customer_status),
    db: Session = Depends(get_db),
) -> CustomerResponse:
    customer = CustomerService(db).reactivate(customer_id, ctx.organization.id, ctx.user)
    return to_customer_response(customer)


@router.get(
    "/{customer_id}/shipments",
    response_model=CustomerShipmentListResponse,
    summary="List shipments for a customer",
    description="Returns shipments for this customer in the current organization only.",
)
def list_customer_shipments(
    customer_id: UUID,
    ctx: TenantContext = Depends(require_customer_read),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> CustomerShipmentListResponse:
    CustomerService(db).get_for_organization(customer_id, ctx.organization.id)
    items, total = ShipmentService(db).list_for_customer(
        ctx.organization.id,
        customer_id,
        page=page,
        page_size=page_size,
    )
    return CustomerShipmentListResponse(
        items=[to_shipment_list_item(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )
