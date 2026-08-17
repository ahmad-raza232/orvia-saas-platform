import secrets
from uuid import UUID


def generate_pod_object_key(
    organization_id: UUID,
    shipment_id: UUID,
    pod_id: UUID,
) -> str:
    """Build a private object key that never includes user filenames or PII."""
    token = secrets.token_urlsafe(24)
    return (
        f"organizations/{organization_id}/shipments/{shipment_id}/"
        f"pod/{pod_id}/{token}"
    )
