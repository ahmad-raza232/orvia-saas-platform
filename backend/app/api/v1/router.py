from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.customers import router as customers_router
from app.api.v1.invitations import router as invitations_router
from app.api.v1.members import router as members_router
from app.api.v1.memory_storage import router as memory_storage_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.platform import router as platform_router
from app.api.v1.public_tracking import router as public_tracking_router
from app.api.v1.riders import router as riders_router
from app.api.v1.pod_evidence import router as pod_evidence_router
from app.api.v1.shipments import router as shipments_router

api_router = APIRouter()
api_router.include_router(public_tracking_router)
api_router.include_router(auth_router)
api_router.include_router(organizations_router)
api_router.include_router(members_router)
api_router.include_router(invitations_router)
api_router.include_router(platform_router)
api_router.include_router(shipments_router)
api_router.include_router(pod_evidence_router)
api_router.include_router(customers_router)
api_router.include_router(riders_router)
api_router.include_router(notifications_router)
api_router.include_router(memory_storage_router)
