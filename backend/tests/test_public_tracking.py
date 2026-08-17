from app.core.tracking import (
    generate_tracking_number,
    is_gbq_tracking_number,
    is_orvia_tracking_number,
    normalize_tracking_number,
)
from tests.test_shipments import auth_header, create_org


def test_orvia_tracking_format_helpers() -> None:
    sample = generate_tracking_number()
    assert sample.startswith("ORVIA-")
    assert is_orvia_tracking_number(sample)
    assert not is_gbq_tracking_number(sample)
    assert not is_orvia_tracking_number("GBQ12345678")
    assert is_gbq_tracking_number("GBQ12345678")
    assert not is_gbq_tracking_number("GBQ12")
    assert normalize_tracking_number(" orvia-abcdefghjk ") == "ORVIA-ABCDEFGHJK"
    assert is_orvia_tracking_number("ORVIA-ABCDEFGHJK")  # 10 valid alphabet chars
    assert not is_orvia_tracking_number("ORVIA-ABCDEFGHJKL")  # 11 chars
    assert not is_orvia_tracking_number("ORVIA-SHORT")
    assert not is_orvia_tracking_number("ORVIA-0000000000")  # 0 not in alphabet


def test_created_shipment_uses_orvia_and_public_track(client) -> None:
    token, _org = create_org(client, "pubtrack@example.com", "Pub Track Co", "pub-track-co")
    created = client.post(
        "/api/v1/shipments",
        headers=auth_header(token),
        json={
            "status": "BOOKED",
            "service_type": "STANDARD",
            "sender": {
                "name": "Sender",
                "phone": "03001111111",
                "address": "A Street",
                "city": "Lahore",
                "country": "PK",
            },
            "receiver": {
                "name": "Receiver",
                "phone": "03002222222",
                "address": "B Street",
                "city": "Karachi",
                "country": "PK",
            },
            "parcel": {"weight_kg": "1.5", "quantity": 1, "package_type": "BOX"},
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    tracking = body["tracking_number"]
    assert tracking.startswith("ORVIA-")
    assert is_orvia_tracking_number(tracking)
    assert "GBQ" not in tracking

    public = client.get(f"/api/v1/public/tracking/{tracking}")
    assert public.status_code == 200, public.text
    payload = public.json()
    assert payload["tracking_number"] == tracking
    assert payload["status"] == "BOOKED"
    assert payload["origin_city"] == "Lahore"
    assert payload["destination_city"] == "Karachi"
    assert payload["receiver_name"] == "Receiver"
    assert "organization_id" not in payload
    assert "sender" not in payload
    assert isinstance(payload["history"], list)

    missing = client.get("/api/v1/public/tracking/ORVIA-ZZZZZZZZZZ")
    assert missing.status_code == 404

    gbq_rejected = client.get("/api/v1/public/tracking/GBQ12345678")
    assert gbq_rejected.status_code == 404
