"""Domain event types for the tenant-scoped outbox.

These are asynchronous operational events, distinct from audit-log actions.
"""

SHIPMENT_BOOKED = "SHIPMENT_BOOKED"
SHIPMENT_PICKED_UP = "SHIPMENT_PICKED_UP"
SHIPMENT_IN_TRANSIT = "SHIPMENT_IN_TRANSIT"
SHIPMENT_OUT_FOR_DELIVERY = "SHIPMENT_OUT_FOR_DELIVERY"
SHIPMENT_DELIVERED = "SHIPMENT_DELIVERED"
SHIPMENT_CANCELLED = "SHIPMENT_CANCELLED"
POD_CREATED = "POD_CREATED"

DOMAIN_EVENT_TYPES = (
    SHIPMENT_BOOKED,
    SHIPMENT_PICKED_UP,
    SHIPMENT_IN_TRANSIT,
    SHIPMENT_OUT_FOR_DELIVERY,
    SHIPMENT_DELIVERED,
    SHIPMENT_CANCELLED,
    POD_CREATED,
)

TEMPLATE_KEYS = {
    SHIPMENT_BOOKED: "shipment.booked",
    SHIPMENT_PICKED_UP: "shipment.picked_up",
    SHIPMENT_IN_TRANSIT: "shipment.in_transit",
    SHIPMENT_OUT_FOR_DELIVERY: "shipment.out_for_delivery",
    SHIPMENT_DELIVERED: "shipment.delivered",
    SHIPMENT_CANCELLED: "shipment.cancelled",
    POD_CREATED: "pod.created",
}

TEMPLATE_KEY_TO_EVENT = {value: key for key, value in TEMPLATE_KEYS.items()}

STATUS_TO_EVENT = {
    "BOOKED": SHIPMENT_BOOKED,
    "PICKED_UP": SHIPMENT_PICKED_UP,
    "IN_TRANSIT": SHIPMENT_IN_TRANSIT,
    "OUT_FOR_DELIVERY": SHIPMENT_OUT_FOR_DELIVERY,
    "DELIVERED": SHIPMENT_DELIVERED,
    "CANCELLED": SHIPMENT_CANCELLED,
}

AGGREGATE_SHIPMENT = "shipment"
AGGREGATE_PROOF_OF_DELIVERY = "proof_of_delivery"

CHANNEL_EMAIL = "EMAIL"

MAX_NOTIFICATION_ATTEMPTS = 3

SENSITIVE_PAYLOAD_KEYS = {
    "password",
    "token",
    "secret",
    "address",
    "sender_address",
    "receiver_address",
    "postal_code",
    "cod_amount",
    "signature",
    "photo",
    "storage_key",
    "file_contents",
    "upload_url",
    "download_url",
    "access_key",
}
