"""Delivery marketplace API surface."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models.delivery import DeliveryOrder
from models.user import UserRole
from schemas.delivery import (
    DeliveryActionBody,
    DeliveryAssignCourierBody,
    DeliveryCreateRequest,
    DeliveryOrderListResponse,
    DeliveryOrderResponse,
    DeliveryProofBody,
    DeliveryQuoteRequest,
    DeliveryQuoteResponse,
    DeliveryRefundBody,
    DeliverySettlementResponse,
)
from services.delivery_lifecycle import (
    ACTOR_CUSTOMER,
    ACTOR_OPS,
    InvalidDeliveryTransition,
)
from services.delivery_orders import (
    DeliveryOrderAccessError,
    DeliveryOrderNotFound,
    assign_courier,
    cancel_delivery_order,
    courier_deliver_order,
    courier_pickup_order,
    courier_start_delivery,
    create_paid_delivery_order,
    delivery_order_to_dict,
    ensure_delivery_settlement_entries,
    get_delivery_order_or_404,
    merchant_accept_order,
    merchant_can_access,
    merchant_mark_ready,
    merchant_reject_order,
    merchant_start_preparing,
    price_breakdown_to_dict,
    refund_delivery_order,
    settlement_entries_to_dict,
)
from services.delivery_pricing import DeliveryPricingInput
from services.rbac import AuthPrincipal, load_principal_user, require_role


router = APIRouter(prefix="/delivery", tags=["delivery"])
CUSTOMER_ACCESS = require_role("rider")
DRIVER_ACCESS = require_role("driver")
ADMIN_ACCESS = require_role("admin")


def _not_found_or_invalid(exc: Exception) -> HTTPException:
    if isinstance(exc, DeliveryOrderNotFound):
        return HTTPException(status_code=404, detail="Delivery order not found")
    if isinstance(exc, DeliveryOrderAccessError):
        return HTTPException(status_code=403, detail=str(exc))
    if isinstance(exc, InvalidDeliveryTransition):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "invalid_delivery_transition", "message": str(exc)},
        )
    return HTTPException(status_code=400, detail=str(exc))


def _merchant_key_or_403(order: DeliveryOrder, key: str | None) -> None:
    if not merchant_can_access(order, key):
        raise HTTPException(status_code=403, detail="Invalid merchant access code")


@router.post("/quote", response_model=DeliveryQuoteResponse)
def quote_delivery(
    body: DeliveryQuoteRequest,
    customer: AuthPrincipal = Depends(CUSTOMER_ACCESS),
    db: Session = Depends(get_db),
):
    load_principal_user(db, customer)
    quote = price_breakdown_to_dict(
        DeliveryPricingInput(
            items_subtotal_cents=body.items_subtotal_cents,
            distance_km=body.distance_km,
            tip_cents=body.tip_cents,
        )
    )
    return {"quote": quote}


@router.post("/orders", response_model=DeliveryOrderResponse)
def create_delivery_order(
    body: DeliveryCreateRequest,
    customer: AuthPrincipal = Depends(CUSTOMER_ACCESS),
    db: Session = Depends(get_db),
):
    user = load_principal_user(db, customer)
    try:
        order = create_paid_delivery_order(
            db,
            customer_id=user.id,
            merchant_name=body.merchant_name,
            pickup_address=body.pickup_address,
            dropoff_address=body.dropoff_address,
            items_subtotal_cents=body.items_subtotal_cents,
            distance_km=body.distance_km,
            tip_cents=body.tip_cents,
            items_summary=body.items_summary,
            delivery_notes=body.delivery_notes,
            contactless=body.contactless,
        )
    except (ValueError, InvalidDeliveryTransition) as exc:
        raise _not_found_or_invalid(exc) from exc
    db.commit()
    db.refresh(order)
    return {"message": f"Delivery order {order.id} created", "order": delivery_order_to_dict(order, include_sensitive=True)}


@router.get("/orders/customer", response_model=DeliveryOrderListResponse)
def list_customer_delivery_orders(
    customer: AuthPrincipal = Depends(CUSTOMER_ACCESS),
    db: Session = Depends(get_db),
):
    user = load_principal_user(db, customer)
    orders = (
        db.query(DeliveryOrder)
        .filter(DeliveryOrder.customer_id == user.id)
        .order_by(DeliveryOrder.id.desc())
        .all()
    )
    return {"orders": [delivery_order_to_dict(order, include_sensitive=True) for order in orders]}


@router.get("/orders/{order_id}", response_model=DeliveryOrderResponse)
def get_delivery_order(
    order_id: int,
    customer: AuthPrincipal = Depends(CUSTOMER_ACCESS),
    db: Session = Depends(get_db),
):
    user = load_principal_user(db, customer)
    order = get_delivery_order_or_404(db, order_id)
    if order.customer_id != user.id:
        raise HTTPException(status_code=403, detail="Not your delivery order")
    return {"message": f"Delivery order {order_id}", "order": delivery_order_to_dict(order, include_sensitive=True)}


@router.post("/orders/{order_id}/cancel", response_model=DeliveryOrderResponse)
def cancel_customer_delivery_order(
    order_id: int,
    body: DeliveryActionBody | None = None,
    customer: AuthPrincipal = Depends(CUSTOMER_ACCESS),
    db: Session = Depends(get_db),
):
    user = load_principal_user(db, customer)
    order = get_delivery_order_or_404(db, order_id)
    if order.customer_id != user.id:
        raise HTTPException(status_code=403, detail="Not your delivery order")
    try:
        cancel_delivery_order(order, actor=ACTOR_CUSTOMER, reason=body.reason if body else None)
    except InvalidDeliveryTransition as exc:
        raise _not_found_or_invalid(exc) from exc
    db.commit()
    db.refresh(order)
    return {"message": f"Delivery order {order_id} cancelled", "order": delivery_order_to_dict(order, include_sensitive=True)}


@router.get("/courier/offers", response_model=DeliveryOrderListResponse)
def list_courier_delivery_offers(
    driver: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    load_principal_user(db, driver)
    orders = (
        db.query(DeliveryOrder)
        .filter(DeliveryOrder.status == "ready_for_pickup", DeliveryOrder.courier_id.is_(None))
        .order_by(DeliveryOrder.ready_for_pickup_at.asc(), DeliveryOrder.id.asc())
        .limit(50)
        .all()
    )
    return {"orders": [delivery_order_to_dict(order) for order in orders]}


@router.get("/courier/orders", response_model=DeliveryOrderListResponse)
def list_my_courier_delivery_orders(
    driver: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    user = load_principal_user(db, driver)
    orders = (
        db.query(DeliveryOrder)
        .filter(DeliveryOrder.courier_id == user.id)
        .order_by(DeliveryOrder.id.desc())
        .limit(100)
        .all()
    )
    return {"orders": [delivery_order_to_dict(order) for order in orders]}


@router.post("/courier/orders/{order_id}/accept", response_model=DeliveryOrderResponse)
def courier_accept_delivery_order(
    order_id: int,
    driver: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    user = load_principal_user(db, driver)
    order = get_delivery_order_or_404(db, order_id)
    try:
        assign_courier(order, user.id)
    except InvalidDeliveryTransition as exc:
        raise _not_found_or_invalid(exc) from exc
    db.commit()
    db.refresh(order)
    return {"message": f"Delivery order {order_id} accepted", "order": delivery_order_to_dict(order)}


@router.post("/courier/orders/{order_id}/pickup", response_model=DeliveryOrderResponse)
def courier_pickup_delivery_order(
    order_id: int,
    driver: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    user = load_principal_user(db, driver)
    order = get_delivery_order_or_404(db, order_id)
    try:
        courier_pickup_order(order, user.id)
    except (DeliveryOrderAccessError, InvalidDeliveryTransition) as exc:
        raise _not_found_or_invalid(exc) from exc
    db.commit()
    db.refresh(order)
    return {"message": f"Delivery order {order_id} picked up", "order": delivery_order_to_dict(order)}


@router.post("/courier/orders/{order_id}/en-route", response_model=DeliveryOrderResponse)
def courier_start_delivery_order(
    order_id: int,
    driver: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    user = load_principal_user(db, driver)
    order = get_delivery_order_or_404(db, order_id)
    try:
        courier_start_delivery(order, user.id)
    except (DeliveryOrderAccessError, InvalidDeliveryTransition) as exc:
        raise _not_found_or_invalid(exc) from exc
    db.commit()
    db.refresh(order)
    return {"message": f"Delivery order {order_id} en route", "order": delivery_order_to_dict(order)}


@router.post("/courier/orders/{order_id}/delivered", response_model=DeliveryOrderResponse)
def courier_deliver_delivery_order(
    order_id: int,
    body: DeliveryProofBody | None = None,
    driver: AuthPrincipal = Depends(DRIVER_ACCESS),
    db: Session = Depends(get_db),
):
    user = load_principal_user(db, driver)
    order = get_delivery_order_or_404(db, order_id)
    try:
        courier_deliver_order(
            order,
            user.id,
            proof=(body.model_dump(exclude_none=True) if body else {"proof_reference": "courier_confirmed"}),
        )
        ensure_delivery_settlement_entries(db, order)
    except (DeliveryOrderAccessError, InvalidDeliveryTransition) as exc:
        raise _not_found_or_invalid(exc) from exc
    db.commit()
    db.refresh(order)
    return {"message": f"Delivery order {order_id} delivered", "order": delivery_order_to_dict(order)}


@router.get("/merchant/orders", response_model=DeliveryOrderListResponse)
def list_merchant_delivery_orders(
    merchant_access_code: str = Query(...),
    db: Session = Depends(get_db),
):
    orders = (
        db.query(DeliveryOrder)
        .filter(DeliveryOrder.merchant_access_code == merchant_access_code)
        .order_by(DeliveryOrder.id.desc())
        .limit(100)
        .all()
    )
    return {"orders": [delivery_order_to_dict(order) for order in orders]}


@router.get("/merchant/orders/{order_id}", response_model=DeliveryOrderResponse)
def get_merchant_delivery_order(
    order_id: int,
    merchant_access_code: str = Query(...),
    db: Session = Depends(get_db),
):
    order = get_delivery_order_or_404(db, order_id)
    _merchant_key_or_403(order, merchant_access_code)
    return {"message": f"Merchant delivery order {order_id}", "order": delivery_order_to_dict(order)}


@router.post("/merchant/orders/{order_id}/accept", response_model=DeliveryOrderResponse)
def merchant_accept_delivery_order(
    order_id: int,
    merchant_access_code: str = Query(...),
    db: Session = Depends(get_db),
):
    order = get_delivery_order_or_404(db, order_id)
    _merchant_key_or_403(order, merchant_access_code)
    try:
        merchant_accept_order(order)
    except InvalidDeliveryTransition as exc:
        raise _not_found_or_invalid(exc) from exc
    db.commit()
    db.refresh(order)
    return {"message": f"Delivery order {order_id} accepted by merchant", "order": delivery_order_to_dict(order)}


@router.post("/merchant/orders/{order_id}/reject", response_model=DeliveryOrderResponse)
def merchant_reject_delivery_order(
    order_id: int,
    body: DeliveryActionBody | None = None,
    merchant_access_code: str = Query(...),
    db: Session = Depends(get_db),
):
    order = get_delivery_order_or_404(db, order_id)
    _merchant_key_or_403(order, merchant_access_code)
    try:
        merchant_reject_order(order, reason=body.reason if body else "merchant_rejected")
    except InvalidDeliveryTransition as exc:
        raise _not_found_or_invalid(exc) from exc
    db.commit()
    db.refresh(order)
    return {"message": f"Delivery order {order_id} rejected by merchant", "order": delivery_order_to_dict(order)}


@router.post("/merchant/orders/{order_id}/preparing", response_model=DeliveryOrderResponse)
def merchant_prepare_delivery_order(
    order_id: int,
    merchant_access_code: str = Query(...),
    db: Session = Depends(get_db),
):
    order = get_delivery_order_or_404(db, order_id)
    _merchant_key_or_403(order, merchant_access_code)
    try:
        merchant_start_preparing(order)
    except InvalidDeliveryTransition as exc:
        raise _not_found_or_invalid(exc) from exc
    db.commit()
    db.refresh(order)
    return {"message": f"Delivery order {order_id} preparing", "order": delivery_order_to_dict(order)}


@router.post("/merchant/orders/{order_id}/ready", response_model=DeliveryOrderResponse)
def merchant_ready_delivery_order(
    order_id: int,
    merchant_access_code: str = Query(...),
    db: Session = Depends(get_db),
):
    order = get_delivery_order_or_404(db, order_id)
    _merchant_key_or_403(order, merchant_access_code)
    try:
        merchant_mark_ready(order)
    except InvalidDeliveryTransition as exc:
        raise _not_found_or_invalid(exc) from exc
    db.commit()
    db.refresh(order)
    return {"message": f"Delivery order {order_id} ready for pickup", "order": delivery_order_to_dict(order)}


@router.get("/ops/orders", response_model=DeliveryOrderListResponse)
def ops_list_delivery_orders(
    status_filter: str | None = Query(default=None, alias="status"),
    admin: AuthPrincipal = Depends(ADMIN_ACCESS),
    db: Session = Depends(get_db),
):
    load_principal_user(db, admin)
    query = db.query(DeliveryOrder)
    if status_filter:
        query = query.filter(DeliveryOrder.status == status_filter)
    orders = query.order_by(DeliveryOrder.id.desc()).limit(200).all()
    return {"orders": [delivery_order_to_dict(order, include_sensitive=True) for order in orders]}


@router.get("/ops/orders/{order_id}", response_model=DeliverySettlementResponse)
def ops_get_delivery_order(
    order_id: int,
    admin: AuthPrincipal = Depends(ADMIN_ACCESS),
    db: Session = Depends(get_db),
):
    load_principal_user(db, admin)
    order = get_delivery_order_or_404(db, order_id)
    entries = ensure_delivery_settlement_entries(db, order)
    db.commit()
    return {
        "order": delivery_order_to_dict(order, include_sensitive=True),
        "settlement_entries": settlement_entries_to_dict(entries),
    }


@router.post("/ops/orders/{order_id}/assign", response_model=DeliveryOrderResponse)
def ops_assign_delivery_order(
    order_id: int,
    body: DeliveryAssignCourierBody,
    admin: AuthPrincipal = Depends(ADMIN_ACCESS),
    db: Session = Depends(get_db),
):
    load_principal_user(db, admin)
    order = get_delivery_order_or_404(db, order_id)
    try:
        assign_courier(order, body.courier_id, actor=ACTOR_OPS)
    except InvalidDeliveryTransition as exc:
        raise _not_found_or_invalid(exc) from exc
    db.commit()
    db.refresh(order)
    return {"message": f"Delivery order {order_id} assigned", "order": delivery_order_to_dict(order, include_sensitive=True)}


@router.post("/ops/orders/{order_id}/refund", response_model=DeliverySettlementResponse)
def ops_refund_delivery_order(
    order_id: int,
    body: DeliveryRefundBody,
    admin: AuthPrincipal = Depends(ADMIN_ACCESS),
    db: Session = Depends(get_db),
):
    load_principal_user(db, admin)
    order = get_delivery_order_or_404(db, order_id)
    try:
        refund_delivery_order(order, amount_cents=body.amount_cents, reason=body.reason)
        entries = ensure_delivery_settlement_entries(db, order)
    except (ValueError, InvalidDeliveryTransition) as exc:
        raise _not_found_or_invalid(exc) from exc
    db.commit()
    db.refresh(order)
    return {
        "order": delivery_order_to_dict(order, include_sensitive=True),
        "settlement_entries": settlement_entries_to_dict(entries),
    }


@router.get("/orders/{order_id}/refund-eligibility")
def get_delivery_refund_eligibility(
    order_id: int,
    authorization: str | None = Header(default=None),
    customer: AuthPrincipal = Depends(CUSTOMER_ACCESS),
    db: Session = Depends(get_db),
):
    _ = authorization
    user = load_principal_user(db, customer)
    order = get_delivery_order_or_404(db, order_id)
    if order.customer_id != user.id:
        raise HTTPException(status_code=403, detail="Not your delivery order")
    return delivery_order_to_dict(order)["refund"]
