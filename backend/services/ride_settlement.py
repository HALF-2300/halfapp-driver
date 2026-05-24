"""Settlement boundary ledger — immutable obligations from locked ride_pricing."""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from sqlalchemy.orm import Session

from models.ride import Ride
from models.ride_pricing import RidePricing
from models.route_snapshot import SNAPSHOT_ROLE_COMPLETE, RouteSnapshot
from models.settlement_entry import (
    ALLOWED_ENTRY_TYPES,
    ENTRY_TYPE_ACCESSIBILITY_LIABILITY,
    ENTRY_TYPE_AIRPORT_LIABILITY,
    ENTRY_TYPE_CITY_LIABILITY,
    ENTRY_TYPE_CUSTOMER_CHARGE,
    ENTRY_TYPE_DRIVER_PAYOUT,
    ENTRY_TYPE_PLATFORM_COMMISSION,
    ENTRY_TYPE_PLATFORM_REVENUE,
    ENTRY_TYPE_PLATFORM_SERVICE_FEE,
    ENTRY_TYPE_TAX_LIABILITY,
    ENTRY_TYPE_TIP_DRIVER,
    ENTRY_TYPE_TOLL_LIABILITY,
    PARTY_AIRPORT,
    PARTY_CITY,
    PARTY_DRIVER,
    PARTY_PLATFORM,
    PARTY_RIDER,
    PARTY_TAX_AUTHORITY,
    PARTY_TOLL_AUTHORITY,
    SETTLEMENT_STATUS_READY,
    SOURCE_RIDE_PRICING_LOCKED,
    SettlementEntry,
)
from services.datetime_utils import utc_now_naive
from services.lifecycle import RideStatus, to_storage_ride_status
from services.route_snapshots import stable_hash, sanitize_provenance

_SECRET_KEY_PATTERN = re.compile(
    r"(api[_-]?key|secret|authorization|password|token|access[_-]?token|bearer)",
    re.IGNORECASE,
)


class SettlementGenerationError(ValueError):
    pass


class SettlementImmutableError(ValueError):
    pass


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def entry_checksum(
    *,
    ride_id: int,
    pricing_id: int,
    entry_type: str,
    party: str,
    amount_cents: int,
    currency: str,
) -> str:
    return stable_hash(
        {
            "ride_id": ride_id,
            "pricing_id": pricing_id,
            "entry_type": entry_type,
            "party": party,
            "amount_cents": amount_cents,
            "currency": currency,
            "source": SOURCE_RIDE_PRICING_LOCKED,
        }
    )


def sanitize_settlement_metadata(metadata: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not metadata:
        return {}
    cleaned = sanitize_provenance(metadata)
    return {k: v for k, v in cleaned.items() if not _SECRET_KEY_PATTERN.search(k)}


def get_complete_route_snapshot_id(db: Session, ride_id: int) -> Optional[int]:
    row = (
        db.query(RouteSnapshot)
        .filter(
            RouteSnapshot.ride_id == ride_id,
            RouteSnapshot.snapshot_role == SNAPSHOT_ROLE_COMPLETE,
        )
        .order_by(RouteSnapshot.id.desc())
        .first()
    )
    return row.id if row else None


def list_settlement_entries(db: Session, *, ride_id: int) -> list[SettlementEntry]:
    return (
        db.query(SettlementEntry)
        .filter(SettlementEntry.ride_id == ride_id)
        .order_by(SettlementEntry.id.asc())
        .all()
    )


def settlement_already_generated(db: Session, *, ride_id: int) -> bool:
    return db.query(SettlementEntry.id).filter(SettlementEntry.ride_id == ride_id).first() is not None


def _locked_pricing_amounts(pricing: RidePricing) -> dict[str, int]:
    driver_ride_payout = pricing.driver_ride_payout_cents or pricing.driver_commission_cents or 0
    platform_rev = pricing.platform_revenue_cents or pricing.platform_earnings_cents or 0
    customer_total = pricing.customer_total_cents or pricing.total_rider_charge_cents or 0
    return {
        "customer_total_cents": max(0, int(customer_total)),
        "driver_ride_payout_cents": max(0, int(driver_ride_payout)),
        "driver_total_payout_cents": max(0, int(pricing.driver_earnings_cents or 0)),
        "platform_commission_cents": max(0, int(pricing.platform_commission_cents or 0)),
        "platform_service_fee_cents": max(0, int(pricing.platform_service_fee_cents or 0)),
        "platform_revenue_cents": max(0, int(platform_rev)),
        "tip_cents": max(0, int(pricing.tip_cents or 0)),
        "city_fee_cents": max(0, int(pricing.city_fee_cents or 0)),
        "airport_fee_cents": max(0, int(pricing.airport_fee_cents or 0)),
        "toll_cents": max(0, int(pricing.toll_cents or 0)),
        "accessibility_fee_cents": max(0, int(pricing.accessibility_fee_cents or 0)),
        "tax_cents": max(0, int(pricing.tax_cents or 0)),
        "driver_shareable_fare_cents": max(0, int(pricing.driver_shareable_fare_cents or 0)),
    }


def _build_entry_specs(amounts: dict[str, int]) -> list[tuple[str, str, int]]:
    """Return (entry_type, party, amount_cents) rows for a completed ride."""
    specs: list[tuple[str, str, int]] = [
        (ENTRY_TYPE_CUSTOMER_CHARGE, PARTY_RIDER, amounts["customer_total_cents"]),
        (ENTRY_TYPE_DRIVER_PAYOUT, PARTY_DRIVER, amounts["driver_ride_payout_cents"]),
        (ENTRY_TYPE_PLATFORM_COMMISSION, PARTY_PLATFORM, amounts["platform_commission_cents"]),
        (ENTRY_TYPE_PLATFORM_SERVICE_FEE, PARTY_PLATFORM, amounts["platform_service_fee_cents"]),
        (ENTRY_TYPE_PLATFORM_REVENUE, PARTY_PLATFORM, amounts["platform_revenue_cents"]),
    ]
    if amounts["tip_cents"] > 0:
        specs.append((ENTRY_TYPE_TIP_DRIVER, PARTY_DRIVER, amounts["tip_cents"]))
    if amounts["city_fee_cents"] > 0:
        specs.append((ENTRY_TYPE_CITY_LIABILITY, PARTY_CITY, amounts["city_fee_cents"]))
    if amounts["airport_fee_cents"] > 0:
        specs.append((ENTRY_TYPE_AIRPORT_LIABILITY, PARTY_AIRPORT, amounts["airport_fee_cents"]))
    if amounts["toll_cents"] > 0:
        specs.append((ENTRY_TYPE_TOLL_LIABILITY, PARTY_TOLL_AUTHORITY, amounts["toll_cents"]))
    if amounts["accessibility_fee_cents"] > 0:
        specs.append(
            (ENTRY_TYPE_ACCESSIBILITY_LIABILITY, "accessibility_authority", amounts["accessibility_fee_cents"])
        )
    if amounts["tax_cents"] > 0:
        specs.append((ENTRY_TYPE_TAX_LIABILITY, PARTY_TAX_AUTHORITY, amounts["tax_cents"]))
    return specs


def generate_settlement_entries(
    db: Session,
    *,
    ride_id: int,
    settlement_status: str = SETTLEMENT_STATUS_READY,
) -> list[SettlementEntry]:
    """
    Idempotent: returns existing locked entries if already generated.
    Requires completed ride + financial_locked ride_pricing.
    """
    if settlement_already_generated(db, ride_id=ride_id):
        return list_settlement_entries(db, ride_id=ride_id)

    ride = db.query(Ride).filter(Ride.id == ride_id).first()
    if not ride:
        raise SettlementGenerationError("Ride not found")
    if ride.status != to_storage_ride_status(RideStatus.COMPLETED):
        raise SettlementGenerationError("Settlement requires a completed ride")
    if ride.status == to_storage_ride_status(RideStatus.CANCELLED):
        raise SettlementGenerationError("Cancelled rides do not generate settlement")

    pricing = db.query(RidePricing).filter(RidePricing.ride_id == ride_id).first()
    if not pricing or not pricing.financial_locked:
        raise SettlementGenerationError("Settlement requires financially locked ride_pricing")

    amounts = _locked_pricing_amounts(pricing)
    route_snapshot_id = get_complete_route_snapshot_id(db, ride_id)
    now = utc_now_naive()
    currency = "USD"
    metadata = sanitize_settlement_metadata(
        {
            "driver_shareable_fare_cents": amounts["driver_shareable_fare_cents"],
            "driver_total_payout_cents": amounts["driver_total_payout_cents"],
            "pass_through_total_cents": pricing.pass_through_total_cents,
            "fare_amount_display_note": (
                "Ride.fare_amount and CompleteRideResponse.fare_earned are driver earnings "
                "(driver_total_payout_cents), not customer_total_cents."
            ),
        }
    )
    metadata_blob = _canonical_json(metadata) if metadata else None

    rows: list[SettlementEntry] = []
    for entry_type, party, amount_cents in _build_entry_specs(amounts):
        if entry_type not in ALLOWED_ENTRY_TYPES:
            raise SettlementGenerationError(f"Unknown entry_type: {entry_type}")
        checksum = entry_checksum(
            ride_id=ride_id,
            pricing_id=pricing.ride_id,
            entry_type=entry_type,
            party=party,
            amount_cents=amount_cents,
            currency=currency,
        )
        row = SettlementEntry(
            ride_id=ride_id,
            pricing_id=pricing.ride_id,
            route_snapshot_id=route_snapshot_id,
            settlement_status=settlement_status,
            entry_type=entry_type,
            party=party,
            amount_cents=amount_cents,
            currency=currency,
            source=SOURCE_RIDE_PRICING_LOCKED,
            entry_checksum=checksum,
            metadata_json=metadata_blob,
            created_at=now,
            locked_at=now,
        )
        db.add(row)
        rows.append(row)

    db.flush()
    return rows


def settlement_public_view(row: SettlementEntry) -> dict[str, Any]:
    created = row.created_at
    locked = row.locked_at
    return {
        "id": row.id,
        "entry_type": row.entry_type,
        "party": row.party,
        "amount_cents": row.amount_cents,
        "currency": row.currency,
        "settlement_status": row.settlement_status,
        "source": row.source,
        "pricing_id": row.pricing_id,
        "route_snapshot_id": row.route_snapshot_id,
        "entry_checksum": row.entry_checksum,
        "created_at": (created.isoformat() + "Z") if created and created.tzinfo is None else (
            created.isoformat() if created else None
        ),
        "locked_at": (locked.isoformat() + "Z") if locked and locked.tzinfo is None else (
            locked.isoformat() if locked else None
        ),
    }


def settlement_summary_for_ride(db: Session, *, ride_id: int) -> dict[str, Any]:
    rows = list_settlement_entries(db, ride_id=ride_id)
    if not rows:
        return {
            "ride_id": ride_id,
            "settlement_status": None,
            "entries": [],
            "totals": {},
        }
    by_type = {row.entry_type: row for row in rows}
    return {
        "ride_id": ride_id,
        "settlement_status": rows[0].settlement_status,
        "pricing_id": rows[0].pricing_id,
        "route_snapshot_id": rows[0].route_snapshot_id,
        "source": rows[0].source,
        "entries": [settlement_public_view(row) for row in rows],
        "totals": {
            "customer_charge_obligation_cents": by_type.get(ENTRY_TYPE_CUSTOMER_CHARGE).amount_cents
            if ENTRY_TYPE_CUSTOMER_CHARGE in by_type
            else 0,
            "driver_payout_obligation_cents": by_type.get(ENTRY_TYPE_DRIVER_PAYOUT).amount_cents
            if ENTRY_TYPE_DRIVER_PAYOUT in by_type
            else 0,
            "platform_revenue_cents": by_type.get(ENTRY_TYPE_PLATFORM_REVENUE).amount_cents
            if ENTRY_TYPE_PLATFORM_REVENUE in by_type
            else 0,
            "tip_payable_to_driver_cents": by_type.get(ENTRY_TYPE_TIP_DRIVER).amount_cents
            if ENTRY_TYPE_TIP_DRIVER in by_type
            else 0,
        },
        "display_field_meanings": {
            "fare_amount": "driver earnings display (driver_total_payout_cents), not customer charge",
            "fare_earned": "same as driver_total_payout_cents on complete response",
            "customer_total_cents": "rider charge obligation source in ride_pricing",
        },
    }
