"""Delivery API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DeliveryQuoteRequest(BaseModel):
    items_subtotal_cents: int = Field(ge=0)
    distance_km: float = Field(ge=0)
    tip_cents: int = Field(default=0, ge=0)


class DeliveryCreateRequest(DeliveryQuoteRequest):
    merchant_name: str = Field(min_length=1, max_length=160)
    pickup_address: str = Field(min_length=1, max_length=255)
    dropoff_address: str = Field(min_length=1, max_length=255)
    items_summary: str | None = Field(default=None, max_length=500)
    delivery_notes: str | None = Field(default=None, max_length=500)
    contactless: bool = True


class DeliveryActionBody(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class DeliveryAssignCourierBody(BaseModel):
    courier_id: int = Field(gt=0)


class DeliveryRefundBody(BaseModel):
    amount_cents: int = Field(gt=0)
    reason: str | None = Field(default=None, max_length=500)


class DeliveryProofBody(BaseModel):
    dropoff_note: str | None = Field(default=None, max_length=500)
    proof_reference: str | None = Field(default=None, max_length=200)


class DeliveryOrderResponse(BaseModel):
    message: str
    order: dict


class DeliveryOrderListResponse(BaseModel):
    orders: list[dict]


class DeliveryQuoteResponse(BaseModel):
    quote: dict


class DeliverySettlementResponse(BaseModel):
    order: dict
    settlement_entries: list[dict]
