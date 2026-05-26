# HalfApp System Truth (Authoritative)

Date: 2026-05-25  
Status: **Non-negotiable ground truth** for engineers, agents, reviewers, and investors.

**Updated 2026-05-25** to match `HALFAPP_TWO_SIDED_EXECUTION_CHECKLIST_01.md` Phase 1–4 **SHIPPED** (code). P0 technical runtime proofs G1/G2/G7 are **GO**; owner courier day G3 remains **PENDING_OWNER** — see `docs/HALFAPP_AI_AGENT_COMPLETION_DIRECTIVES_01.md`.

This document supersedes stale assumptions that HalfApp has **no** rider or ops product. It does **not** claim a complete DoorDash/Lyft-class marketplace.

Operational detail: `docs/CURRENT_TRUTH.md` · Stage 0 lock: `docs/PRODUCT_BOUNDARY_STAGE0.md` · Delivery framing: `docs/HALFAPP_PROGRAM_BRAIN_COMPREHENSIVE_REPORT_06.md`

---

## What this system is

> **A delivery-driver execution application** with a thin requester loop, simulated payment records, and a minimal ops console.

It is **not**:

- a complete last-mile logistics marketplace (no merchant portal, POD, batching)
- a production PSP / bank-payout product
- a city-scale mobility operating system

Legacy code and docs say **ride** / **rider**; product meaning is **delivery job** / **customer requester** (Report 05 §0.3).

---

## Production path (active surfaces)

| Surface | Path | Status |
|---------|------|--------|
| Courier (driver) app | `driver-app/` | **Real** — map cockpit, lifecycle, earnings |
| Requester app | `rider-app/` | **SHIPPED** (Phase 1–3) — request, status, estimate, receipt, history |
| Backend API | `backend/` | **Real** — `/drivers/*`, `/rides/*`, `/admin/*`, notifications |
| Ops console | `ops-app/` | **SHIPPED** (Phase 4) — list/cancel/assign, drivers |

`frontend/` and `rider-stub/` are **not** product evidence.

---

## Four-surface model (marketplace completeness)

| Surface | Required for full marketplace | Current status |
|---------|------------------------------|----------------|
| Requester (demand) | Yes | **SHIPPED** — `rider-app/` (no merchant/SKU checkout) |
| Courier (supply) | Yes | **Partial but real** — `driver-app/` |
| Money loop UX | Yes | **Partial** — simulated `ride_payments` + `ride_pricing` ledger; **no** bank payout product |
| Ops control plane | Yes | **SHIPPED (minimal)** — `ops-app/` + mounted `/admin/rides`, `/admin/drivers` |

**Verdict:** Demonstrable **requester → courier → complete → receipt → ops** on local/staging; **not** production-hardened marketplace.

---

## Shipped capabilities (may claim with tests)

| Capability | Proof |
|------------|-------|
| Requester auth + `POST /rides/` | `tests/test_rider_auth.py`, `rider-app` E2E |
| Courier open-board + claim lock | `tests/test_ride_claim_lock_concurrency.py` |
| Auto-assign (optional flag) | `tests/test_ride_auto_assign.py` |
| Lifecycle through completed | `tests/test_ride_flow_ui_proof.py`, `test_stable_car_p0_01.py` |
| Simulated payments (Phase 3) | `ride_payments` migration `0032`, `tests/test_ride_payment_phase3.py` |
| Ops list/detail/cancel/assign | `tests/test_ops_phase4.py` |
| Session recovery API | `tests/test_active_ride_recovery.py` |
| Integer-cent pricing ledger | `tests/test_pricing_ledger_v01.py` |

---

## Partial / not production

| Area | Status |
|------|--------|
| PostgreSQL default dev + claim-race | **GO** — fresh PostgreSQL 16 Alembic + claim-race proof passed |
| OSRM runtime | **GO** — `scripts/prove_osrm_runtime.py` exit 0 on this host |
| Real Stripe / bank payout UX | **NOT** product — flags + schema only |
| Push notifications | **NOT** shipped |
| Proof of delivery | **NOT** shipped |
| Nearest-driver marketing as default | **NOT** — open board default; auto-assign flag optional |

---

## What is NOT product (unchanged)

| Surface | Classification |
|---------|----------------|
| `frontend/` | **ARCHIVE · NOT WIRED** |
| `rider-stub/` | **DEMO ONLY** |
| `video-gate/` | Isolated tooling |
| Dossier `/supply`, `/demand`, `/trip` | **PARALLEL_NOT_WIRED** to driver-app — see `DOSSIER_PATH_DECISION_01.md` |
| Dormant `routes/admin.py` (legacy) | Superseded by `admin_driver_approval` routes in `main.py` |

---

## Agent and reviewer rules

- Do not describe the system as "almost DoorDash" or "strongest delivery platform."
- Do not use `frontend/` or `rider-stub/` as rider/ops proof.
- Do not equate `ride_pricing` or `ride_payments` with money in the bank.
- Product behavior must be reachable from `backend/main.py` and active app entry points with tests.
- Honest framing until P0 gates close: **auditable partial delivery execution with explicit blocked states.**

---

## Summary

| Area | Status |
|------|--------|
| Courier side | Exists (real, partial) |
| Requester side | **Shipped** (minimal app) |
| Simulated payments + ledger | **Shipped** (not PSP product) |
| Ops console | **Shipped** (minimal) |
| Staging hardening (PG + OSRM + owner day) | **In progress** — PG + OSRM GO; owner day pending |

**A full production marketplace loop is demonstrable in dev; production GO requires closed P0 gates in `HALFAPP_AI_AGENT_COMPLETION_DIRECTIVES_01.md`.**
