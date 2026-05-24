# Owner-car day — pre-flight and proof checklist

Use this on the day a real vehicle exercises the Portland staging stack end-to-end.

## Pre-flight (must be green)

- [ ] `BASE=https://staging.halfapp.app bash infra/staging/scripts/03_health_check.sh` exits 0
- [ ] OSRM: five sample Portland routes each respond in **under 100 ms** (use `03_health_check.sh` route + four more coords from `backend/scripts/proof_osrm_portland_routes.py`)
- [ ] Postgres claim-race proof green on Neon (`backend/tests/test_postgres_claim_race_proof_01.py` with `DATABASE_URL` set)
- [ ] No `ERROR` / `CRITICAL` in API logs for the last 24h (`docker compose -f infra/staging/docker-compose.yml logs --since 24h api`)
- [ ] Driver app build points at `https://staging.halfapp.app/api`
- [ ] Rider stub points at the same API base

## Devices

- [ ] Driver app installed on phone; driver JWT acquired; presence **online**
- [ ] Rider stub on second phone or laptop; can request a **real Portland address**

## Scenarios (execute in order)

1. [ ] **Solo ride** — rider creates ride, driver claims, full lifecycle to completed
2. [ ] **Two simultaneous claims** — same open ride, two drivers; exactly one winner, one conflict response
3. [ ] **Network drop mid-ride** — airplane mode ~30s, restore; state consistent on refresh
4. [ ] **Mid-ride refresh** — reload driver cockpit; active ride still bound to same driver

## Post-flight

- [ ] Export all `marketplace_ledger_events` for the session window from Neon
- [ ] Attach logs, health-check output, and ledger export to `docs/OWNER_DAY_<YYYY-MM-DD>_PROOF.md`
- [ ] Note any NO_GO items in `docs/CURRENT_TRUTH.md` follow-up

## Human gate reminder

VPS must exist before this day (`GATE-VPS-1`). See `infra/staging/README.md`.
