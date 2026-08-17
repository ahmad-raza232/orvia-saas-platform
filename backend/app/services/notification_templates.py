import re
from datetime import datetime

from app.core.events import DOMAIN_EVENT_TYPES, TEMPLATE_KEYS

_TOKEN = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")

ALLOWED_VARIABLES = {
    "tracking_number",
    "customer_name",
    "shipment_status",
    "delivered_at",
}

TEMPLATES: dict[str, dict[str, str]] = {
    "shipment.booked": {
        "subject": "Shipment {{tracking_number}} is booked",
        "body": (
            "Hello {{customer_name}},\n\n"
            "Your shipment {{tracking_number}} has been booked.\n"
            "Current status: {{shipment_status}}.\n"
        ),
    },
    "shipment.picked_up": {
        "subject": "Shipment {{tracking_number}} has been picked up",
        "body": (
            "Hello {{customer_name}},\n\n"
            "Shipment {{tracking_number}} has been picked up.\n"
            "Current status: {{shipment_status}}.\n"
        ),
    },
    "shipment.in_transit": {
        "subject": "Shipment {{tracking_number}} is in transit",
        "body": (
            "Hello {{customer_name}},\n\n"
            "Shipment {{tracking_number}} is in transit.\n"
            "Current status: {{shipment_status}}.\n"
        ),
    },
    "shipment.out_for_delivery": {
        "subject": "Shipment {{tracking_number}} is out for delivery",
        "body": (
            "Hello {{customer_name}},\n\n"
            "Shipment {{tracking_number}} is out for delivery.\n"
            "Current status: {{shipment_status}}.\n"
        ),
    },
    "shipment.delivered": {
        "subject": "Shipment {{tracking_number}} has been delivered",
        "body": (
            "Hello {{customer_name}},\n\n"
            "Shipment {{tracking_number}} was delivered at {{delivered_at}}.\n"
            "Current status: {{shipment_status}}.\n"
        ),
    },
    "shipment.cancelled": {
        "subject": "Shipment {{tracking_number}} was cancelled",
        "body": (
            "Hello {{customer_name}},\n\n"
            "Shipment {{tracking_number}} has been cancelled.\n"
            "Current status: {{shipment_status}}.\n"
        ),
    },
    "pod.created": {
        "subject": "Proof of delivery recorded for {{tracking_number}}",
        "body": (
            "Hello {{customer_name}},\n\n"
            "Proof of delivery has been recorded for shipment {{tracking_number}}.\n"
            "Delivered at: {{delivered_at}}.\n"
            "Current status: {{shipment_status}}.\n"
        ),
    },
}


def _render(template: str, variables: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in ALLOWED_VARIABLES:
            return ""
        return variables.get(key, "")

    return _TOKEN.sub(replace, template)


def template_variables(
    *,
    tracking_number: str,
    customer_name: str | None,
    shipment_status: str,
    delivered_at: datetime | str | None,
) -> dict[str, str]:
    delivered = ""
    if isinstance(delivered_at, datetime):
        delivered = delivered_at.strftime("%Y-%m-%d %H:%M UTC")
    elif delivered_at:
        delivered = str(delivered_at)
    return {
        "tracking_number": tracking_number,
        "customer_name": customer_name or "Customer",
        "shipment_status": shipment_status,
        "delivered_at": delivered or "n/a",
    }


def render_email(event_type: str, variables: dict[str, str]) -> tuple[str, str]:
    if event_type not in DOMAIN_EVENT_TYPES:
        raise ValueError("Unknown event type")
    key = TEMPLATE_KEYS[event_type]
    template = TEMPLATES[key]
    return _render(template["subject"], variables), _render(template["body"], variables)
