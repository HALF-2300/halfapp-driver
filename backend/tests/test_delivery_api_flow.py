import uuid

from fastapi.testclient import TestClient

from main import app
from models.user import UserRole
from services.auth import create_access_token, create_user
from database import SessionLocal


def _create_user_token(role: UserRole):
    db = SessionLocal()
    try:
        uid = uuid.uuid4().hex[:10]
        kwargs = {}
        license_no = None
        if role == UserRole.DRIVER:
            license_no = f"DLV{uid}"
            kwargs["driver_approval_status"] = "approved"
        user = create_user(
            db,
            f"delivery_{role.value}_{uid}@example.com",
            f"Delivery {role.value}",
            "pw12345",
            role,
            license_no,
            **kwargs,
        )
        return user.id, create_access_token(sub=user.email, role=user.role.value)
    finally:
        db.close()


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _delivery_payload() -> dict:
    return {
        "merchant_name": "Pearl Market",
        "pickup_address": "10 Market St",
        "dropoff_address": "88 Local Ave",
        "items_summary": "Noodle bowl, sparkling water",
        "delivery_notes": "Contactless at lobby shelf",
        "items_subtotal_cents": 2400,
        "distance_km": 3.2,
        "tip_cents": 500,
        "contactless": True,
    }


def test_delivery_marketplace_api_happy_path_customer_merchant_courier_ops():
    _, customer_token = _create_user_token(UserRole.CUSTOMER)
    courier_id, courier_token = _create_user_token(UserRole.DRIVER)
    _, admin_token = _create_user_token(UserRole.ADMIN)

    with TestClient(app) as client:
        quote = client.post("/delivery/quote", headers=_headers(customer_token), json=_delivery_payload())
        assert quote.status_code == 200, quote.text
        assert quote.json()["quote"]["customer_charge_cents"] == 4052

        created = client.post("/delivery/orders", headers=_headers(customer_token), json=_delivery_payload())
        assert created.status_code == 200, created.text
        created_order = created.json()["order"]
        order_id = created_order["id"]
        merchant_access_code = created_order["merchant_access_code"]
        assert created_order["status"] == "paid"
        assert created_order["pricing"]["courier_payout_cents"] == 1202
        assert created_order["pricing"]["merchant_payout_cents"] == 2040

        listed = client.get("/delivery/orders/customer", headers=_headers(customer_token))
        assert listed.status_code == 200, listed.text
        assert [order["id"] for order in listed.json()["orders"]] == [order_id]

        merchant_accept = client.post(
            f"/delivery/merchant/orders/{order_id}/accept?merchant_access_code={merchant_access_code}"
        )
        assert merchant_accept.status_code == 200, merchant_accept.text
        assert merchant_accept.json()["order"]["status"] == "merchant_accepted"

        merchant_prepare = client.post(
            f"/delivery/merchant/orders/{order_id}/preparing?merchant_access_code={merchant_access_code}"
        )
        assert merchant_prepare.status_code == 200, merchant_prepare.text
        assert merchant_prepare.json()["order"]["status"] == "preparing"

        merchant_ready = client.post(
            f"/delivery/merchant/orders/{order_id}/ready?merchant_access_code={merchant_access_code}"
        )
        assert merchant_ready.status_code == 200, merchant_ready.text
        assert merchant_ready.json()["order"]["status"] == "ready_for_pickup"

        offers = client.get("/delivery/courier/offers", headers=_headers(courier_token))
        assert offers.status_code == 200, offers.text
        assert [order["id"] for order in offers.json()["orders"]] == [order_id]

        accepted = client.post(f"/delivery/courier/orders/{order_id}/accept", headers=_headers(courier_token))
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["order"]["status"] == "courier_assigned"
        assert accepted.json()["order"]["courier_id"] == courier_id

        picked_up = client.post(f"/delivery/courier/orders/{order_id}/pickup", headers=_headers(courier_token))
        assert picked_up.status_code == 200, picked_up.text
        assert picked_up.json()["order"]["status"] == "picked_up"

        en_route = client.post(f"/delivery/courier/orders/{order_id}/en-route", headers=_headers(courier_token))
        assert en_route.status_code == 200, en_route.text
        assert en_route.json()["order"]["status"] == "en_route"

        delivered = client.post(
            f"/delivery/courier/orders/{order_id}/delivered",
            headers=_headers(courier_token),
            json={"proof_reference": "pod://local-test/42", "dropoff_note": "Left on shelf"},
        )
        assert delivered.status_code == 200, delivered.text
        assert delivered.json()["order"]["status"] == "delivered"
        assert delivered.json()["order"]["evidence"]["proof_reference"] == "pod://local-test/42"

        ops_detail = client.get(f"/delivery/ops/orders/{order_id}", headers=_headers(admin_token))
        assert ops_detail.status_code == 200, ops_detail.text
        settlement_types = {entry["entry_type"] for entry in ops_detail.json()["settlement_entries"]}
        assert {
            "customer_charge",
            "merchant_payout",
            "courier_payout",
            "platform_fee",
            "tax_liability",
        }.issubset(settlement_types)
        assert ops_detail.json()["order"]["refund"]["eligible"] is True

        refunded = client.post(
            f"/delivery/ops/orders/{order_id}/refund",
            headers=_headers(admin_token),
            json={"amount_cents": 300, "reason": "missing item"},
        )
        assert refunded.status_code == 200, refunded.text
        assert refunded.json()["order"]["status"] == "refunded"
        assert refunded.json()["order"]["pricing"]["refunded_cents"] == 300
        refund_entries = [entry for entry in refunded.json()["settlement_entries"] if entry["entry_type"] == "refund"]
        assert refund_entries and refund_entries[0]["amount_cents"] == 300


def test_delivery_api_blocks_invalid_transitions_and_lane_swaps():
    _, customer_token = _create_user_token(UserRole.CUSTOMER)
    _, courier_token = _create_user_token(UserRole.DRIVER)

    with TestClient(app) as client:
        created = client.post("/delivery/orders", headers=_headers(customer_token), json=_delivery_payload())
        order_id = created.json()["order"]["id"]

        early_pickup = client.post(f"/delivery/courier/orders/{order_id}/pickup", headers=_headers(courier_token))
        assert early_pickup.status_code == 403, early_pickup.text

        courier_customer_list = client.get("/delivery/orders/customer", headers=_headers(courier_token))
        assert courier_customer_list.status_code == 403, courier_customer_list.text

        wrong_merchant = client.post(
            f"/delivery/merchant/orders/{order_id}/accept?merchant_access_code=not-the-code"
        )
        assert wrong_merchant.status_code == 403, wrong_merchant.text
