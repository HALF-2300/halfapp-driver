"""Driver-scoped ride transparency and claim-conflict response helpers."""

from __future__ import annotations

from typing import Any

from models.ride import Ride
from services.ledger import MarketplaceLedgerEventType
from services.metrics import DISPATCH_VISIBILITY_REASON

_DRIVER_AUDIT_MARKETPLACE_EVENT_TYPES = frozenset(
    {
        MarketplaceLedgerEventType.DISPATCH_RIDE_VISIBLE.value,
        MarketplaceLedgerEventType.DISPATCH_CLAIM_ATTEMPTED.value,
        MarketplaceLedgerEventType.DISPATCH_CLAIM_LOST.value,
        MarketplaceLedgerEventType.RIDE_HIDDEN.value,
    }
)
_VISIBILITY_SOURCE_OPEN_BOARD = "open_board"
_VISIBILITY_SOURCE_DISPATCH = "dispatch_policy"
_VISIBILITY_SOURCE_SIMULATION = "simulation"
_VISIBILITY_SOURCE_UNKNOWN = "unknown"


def claim_conflict_detail(
    *,
    ride_id: int,
    message: str = "Ride already claimed",
    claim_result: str = "lost",
    truth_status: str = "backend_conflict",
    current_status: str | None = None,
    assigned_driver_id: int | None = None,
    reason: str = "ride_already_claimed",
    state_changed: bool = False,
) -> dict[str, Any]:
    """Canonical 409 body for open-board claim conflicts (active /drivers/* path).

    FastAPI nests this dict under the top-level ``detail`` key. Tests in
    ``test_dispatch_auditability``, ``test_ride_lifecycle``, and
    ``test_ride_transparency_and_claim_conflict`` assert this shape.
    """
    body: dict[str, Any] = {
        "detail": message,
        "ride_id": ride_id,
        "claim_result": claim_result,
        "truth_status": truth_status,
        "reason": reason,
        "state_changed": state_changed,
    }
    if current_status is not None:
        body["current_status"] = current_status
    if assigned_driver_id is not None:
        body["assigned_driver_id"] = assigned_driver_id
    return body


def _visibility_source_for_record(
    record: dict[str, Any] | None,
    *,
    lifecycle_reason: str | None,
) -> str:
    if not record:
        return _VISIBILITY_SOURCE_UNKNOWN
    reason = (record.get("visibility_reason") or "").lower()
    if lifecycle_reason == "simulation" or "simulation" in reason:
        return _VISIBILITY_SOURCE_SIMULATION
    if record.get("dispatch_policy_id") or record.get("dispatch_policy_name"):
        return _VISIBILITY_SOURCE_DISPATCH
    if "open_board" in reason or reason == DISPATCH_VISIBILITY_REASON:
        return _VISIBILITY_SOURCE_OPEN_BOARD
    return _VISIBILITY_SOURCE_OPEN_BOARD


def build_driver_scoped_transparency(
    proof: dict[str, Any],
    *,
    driver_id: int,
    ride: Ride,
) -> dict[str, Any]:
    """Normalize raw dispatch proof for the authenticated driver only."""
    driver_visibility = next(
        (row for row in proof.get("driver_visibility", []) if row.get("driver_id") == driver_id),
        None,
    )
    driver_attempts = [
        row for row in proof.get("claim_attempts", []) if row.get("driver_id") == driver_id
    ]
    latest_attempt = driver_attempts[-1] if driver_attempts else None

    hidden = bool(
        driver_visibility
        and driver_visibility.get("status") == "hidden_by_driver"
    )
    visible = driver_visibility is not None and not hidden

    last_claim_result = "none"
    if latest_attempt:
        outcome = latest_attempt.get("outcome")
        if outcome == "won":
            last_claim_result = "won"
        elif outcome in ("conflict", "lost", "unavailable"):
            last_claim_result = "lost"

    assigned_id = proof.get("assigned_driver_id")
    claimable = (
        ride.status == "requested"
        and assigned_id is None
        and not hidden
        and last_claim_result != "won"
    )

    reason_codes: list[str] = []
    if driver_visibility:
        reason = driver_visibility.get("visibility_reason")
        if reason:
            reason_codes.append(reason)
        if driver_visibility.get("status"):
            reason_codes.append(f"visibility_status:{driver_visibility['status']}")
    if not claimable and assigned_id and assigned_id != driver_id:
        reason_codes.append("ride_claimed_by_another_driver")
    if hidden:
        reason_codes.append("hidden_by_driver")

    truth_labels = ["BACKEND_OWNED", "DISPATCH_BACKEND_OWNED", "NO_ETA_GUARANTEE", "NO_ROUTE_SNAPSHOT"]
    if hidden:
        truth_labels.append("RIDE_HIDDEN_FOR_DRIVER")
    if not claimable and assigned_id and assigned_id != driver_id:
        truth_labels.append("CLAIM_UNAVAILABLE")
    if last_claim_result == "lost":
        truth_labels.append("CLAIM_CONFLICT_PROOF")

    ledger_event_ids: list[str] = []
    seen_audit_ids: set[str] = set()
    for entry in proof.get("ledger_entries", []):
        entry_id = entry.get("ledger_entry_id")
        if entry_id is None:
            continue
        key = str(entry_id)
        if key not in seen_audit_ids:
            seen_audit_ids.add(key)
            ledger_event_ids.append(key)
    for event in proof.get("marketplace_ledger_events", []):
        if event.get("driver_id") != driver_id:
            continue
        if event.get("event_type") not in _DRIVER_AUDIT_MARKETPLACE_EVENT_TYPES:
            continue
        key = str(event["id"])
        if key not in seen_audit_ids:
            seen_audit_ids.add(key)
            ledger_event_ids.append(key)

    truth_status = "backend_conflict" if last_claim_result == "lost" else None

    return {
        "ride_id": str(proof["ride_id"]),
        "driver_id": str(driver_id),
        "visibility": {
            "visible": visible,
            "visible_at": driver_visibility.get("visible_from") if driver_visibility else None,
            "visibility_record_id": (
                str(driver_visibility["ride_visibility_id"]) if driver_visibility else None
            ),
            "source": _visibility_source_for_record(
                driver_visibility,
                lifecycle_reason=ride.lifecycle_reason,
            ),
            "policy_id": driver_visibility.get("dispatch_policy_id") if driver_visibility else None,
            "policy_name": driver_visibility.get("dispatch_policy_name") if driver_visibility else None,
            "policy_version": driver_visibility.get("dispatch_policy_id") if driver_visibility else None,
            "reason_codes": reason_codes,
            "ordering_rank": driver_visibility.get("ordering_rank") if driver_visibility else None,
        },
        "claim": {
            "claimable": claimable,
            "current_status": ride.status,
            "claimed_by_driver_id": str(assigned_id) if assigned_id is not None else None,
            "last_claim_attempt_id": (
                str(latest_attempt["claim_attempt_id"]) if latest_attempt else None
            ),
            "last_claim_result": last_claim_result,
            "truth_status": truth_status,
        },
        "dismissal": {
            "hidden_for_this_driver": hidden,
            "hidden_at": driver_visibility.get("dismissed_at") if hidden and driver_visibility else None,
            "expires_at": driver_visibility.get("expires_at") if driver_visibility else None,
            "reason": driver_visibility.get("hide_reason") if hidden and driver_visibility else None,
        },
        "audit": {
            "ledger_event_ids": ledger_event_ids,
            "correlation_id": driver_visibility.get("correlation_id") if driver_visibility else None,
            "idempotency_key": None,
        },
        "truth_labels": truth_labels,
    }
