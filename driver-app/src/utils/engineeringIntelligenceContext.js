/**
 * HalfApp Engineering Intelligence — LOCAL_CONTEXT_ONLY guidance from Report 03.
 * No external AI providers. No network calls to model APIs.
 */

export const ENGINEERING_INTELLIGENCE_MODE = 'LOCAL_CONTEXT_ONLY'

export const REPORT_ID = 'HALFAPP_COMPREHENSIVE_PROGRAM_REPORT_03'

export const STATUS_CHIPS = [
  { id: 'report', label: 'Report 03 loaded', tone: 'ok' },
  { id: 'ai_off', label: 'AI connection OFF', tone: 'warn' },
  { id: 'no_external', label: 'No external provider calls', tone: 'ok' },
  { id: 'osrm', label: 'OSRM runtime NO_GO', tone: 'warn' },
  { id: 'payments', label: 'Payments NO_GO', tone: 'warn' },
  { id: 'dual_spine', label: 'Dual spine risk', tone: 'warn' },
  { id: 'secret_key', label: 'SECRET_KEY needs prod guard', tone: 'warn' },
]

/** @typedef {{ files: string[], direction: string, forbiddenClaims: string[], proofCommands: string[], expectedVerdict: string }} QuickActionGuidance */

/** @type {Record<string, { id: string, label: string, guidance: QuickActionGuidance }>} */
export const QUICK_ACTIONS = {
  build_next: {
    id: 'build_next',
    label: 'What should I build next?',
    guidance: {
      files: [
        'docs/HALFAPP_COMPREHENSIVE_PROGRAM_REPORT_03.md',
        'docs/HALFAPP_AGENT_ACTION_DIRECTIVES.md',
        'docs/CURRENT_TRUTH.md',
        'docs/PRODUCT_BOUNDARY_STAGE0.md',
        'backend/main.py',
      ],
      direction:
        'Close proof gaps before surface expansion: OSRM runtime proof on Docker/VPS, production SECRET_KEY guard, Postgres claim-race suite, dossier Path A vs Path B decision, then read-only audit UI (ledger + settlement + route snapshots). Do not revive legacy frontend or dual-write dossier from UI.',
      forbiddenClaims: [
        'Nearest-driver matching is live',
        'Payments or payouts execute',
        'OSRM is production-proven on this host',
        'Dossier spine is wired to driver-app',
        'Full dispatch readiness without scheduler proof',
      ],
      proofCommands: [
        'cd backend && python -m pytest tests/ -q',
        'cd driver-app && npm run build && npm test',
      ],
      expectedVerdict:
        'PARTIAL_GO overall until OSRM runtime, Postgres races, and dossier fate are resolved; individual P0 lanes (AUTH-001, RIDE-001/002/003, DRIVER-002) remain GO.',
    },
  },
  osrm_runtime: {
    id: 'osrm_runtime',
    label: 'OSRM runtime proof',
    guidance: {
      files: [
        'docs/SELF_HOSTED_ROUTING_PROOF_V0_1_STATUS.md',
        'docker/osrm-portland/',
        'backend/services/osrm_self_hosted_provider.py',
        'backend/services/routing_service.py',
      ],
      direction:
        'Run HALFAPP_OSRM_RUNTIME_PROOF on a Docker-capable host (Linux/VPS). Prove live OSRM on port 5000 returns road-network geometry; until then UI and APIs must honestly show haversine_fallback when OSRM is unavailable.',
      forbiddenClaims: [
        'Production routing uses live OSRM',
        'Road-network ETA is guaranteed',
        'Mapbox/Google traffic is enabled by default',
      ],
      proofCommands: [
        'cd docker/osrm-portland && docker compose up -d',
        'cd backend && python -m pytest tests/test_routing* -q',
      ],
      expectedVerdict: 'Code GO / runtime NO_GO until container proof passes on target host.',
    },
  },
  secret_key_guard: {
    id: 'secret_key_guard',
    label: 'Production SECRET_KEY guard',
    guidance: {
      files: [
        'backend/config.py',
        'backend/production_guards.py',
        'docs/HALFAPP_COMPREHENSIVE_PROGRAM_REPORT_03.md',
      ],
      direction:
        'Enforce non-default SECRET_KEY at boot in production (fail fast if change_me). Document env requirements in deploy checklist. Do not commit secrets.',
      forbiddenClaims: [
        'Production is safe with default SECRET_KEY',
        'JWT forgery is impossible without env review',
      ],
      proofCommands: [
        'cd backend && HALFAPP_ENV=production SECRET_KEY=change_me python -c "from production_guards import assert_production_config; assert_production_config()"',
      ],
      expectedVerdict: 'GO when production boot rejects default secret; PARTIAL_GO until enforced in CI/deploy.',
    },
  },
  reconcile_backlog: {
    id: 'reconcile_backlog',
    label: 'Reconcile BACKLOG + CURRENT_TRUTH',
    guidance: {
      files: [
        'docs/CURRENT_TRUTH.md',
        'docs/PRODUCT_BOUNDARY_STAGE0.md',
        'docs/BACKLOG.md',
        'docs/HALFAPP_AGENT_ACTION_DIRECTIVES.md',
      ],
      direction:
        'Mark closed P0 lanes GO in BACKLOG; strike stale tickets that claim unmounted routers or legacy frontend as active. CURRENT_TRUTH wins over older overview docs.',
      forbiddenClaims: [
        'BACKLOG ticket status overrides green tests',
        'Legacy frontend is active product path',
      ],
      proofCommands: ['grep -R "NOT BUILT\\|GO" docs/HALFAPP_AGENT_ACTION_DIRECTIVES.md'],
      expectedVerdict: 'GO when BACKLOG and CURRENT_TRUTH agree on active spine and closed P0 lanes.',
    },
  },
  dossier_path: {
    id: 'dossier_path',
    label: 'Dossier Path A vs Path B',
    guidance: {
      files: [
        'docs/HALFAPP_DOSSIER_SPINE_RECONCILIATION_01.md',
        'docs/HALFAPP_COMPREHENSIVE_PROGRAM_REPORT_03.md',
        'backend/routes/dossier_marketplace.py',
        'backend/main.py',
      ],
      direction:
        'Path A: evolve active spine (open board + ride_pricing + settlement_entries). Path B: merge dossier IDs/presence/dispatch into one spine. Decide before new marketplace features; never dual-write from driver-app UI.',
      forbiddenClaims: [
        'Dossier marketplace is wired to MapHome',
        'Two spines are safe for production UI',
        'ledger_* is the active driver earnings truth',
      ],
      proofCommands: [
        'grep dossier_marketplace backend/main.py',
        'cd driver-app && grep -R dossier src || true',
      ],
      expectedVerdict:
        'PARALLEL_NOT_WIRED until explicit merge or permanent quarantine decision is documented and enforced.',
    },
  },
  driver_audit_ui: {
    id: 'driver_audit_ui',
    label: 'Driver audit read UI',
    guidance: {
      files: [
        'backend/services/ride_audit.py',
        'backend/routes/drivers.py',
        'driver-app/src/components/TripAuditReceipt.jsx',
        'driver-app/src/utils/tripAuditFormat.js',
        'docs/HALFAPP_DRIVER_AUDIT_READ_UI_01_REPORT.md',
      ],
      direction:
        'GET /drivers/rides/{ride_id}/audit + TripAuditReceipt at /driver/trips/:rideId/audit. Obligation/settlement language only; no PSP or payout-execution copy in UI source.',
      forbiddenClaims: [
        'Full financial audit UI ships payments',
        'UI computes dispatch fairness scores',
      ],
      proofCommands: [
        'cd backend && python -m pytest tests/test_driver_ride_audit.py -q',
        'cd driver-app && npm test && npm run build',
      ],
      expectedVerdict: 'GO — HALFAPP_DRIVER_AUDIT_READ_UI_01 (read-only trip audit / receipt details).',
    },
  },
  route_snapshot_ui: {
    id: 'route_snapshot_ui',
    label: 'Route snapshot read UI',
    guidance: {
      files: [
        'backend/services/route_snapshots_read.py',
        'driver-app/src/components/cockpit/RouteTruthDetails.jsx',
        'driver-app/src/utils/routeTruthFormat.js',
        'docs/HALFAPP_ROUTE_SNAPSHOT_READ_UI_01_REPORT.md',
      ],
      direction:
        'GET /drivers/rides/{ride_id}/route-snapshots + RouteTruthDetails in cockpit and trip audit. Honest fallback + osrm_runtime_claim not_proved.',
      forbiddenClaims: [
        'Driver sees guaranteed road-network route in all environments',
        'OSRM runtime is proven on Windows dev host',
      ],
      proofCommands: [
        'cd backend && python -m pytest tests/test_route_snapshot_read_ui.py -q',
        'cd driver-app && npm test && npm run build',
      ],
      expectedVerdict: 'GO — HALFAPP_ROUTE_SNAPSHOT_READ_UI_01 (read-only route truth UI).',
    },
  },
  postgres_claim_race: {
    id: 'postgres_claim_race',
    label: 'Postgres claim-race proof',
    guidance: {
      files: [
        'backend/tests/test_ride_claim_lock_concurrency.py',
        'backend/services/dispatch.py',
        'docs/RIDE_002_ATOMIC_CLAIM_LOCK_REPORT.md',
      ],
      direction:
        'Run 10-driver concurrent accept test against PostgreSQL DATABASE_URL. SQLite serializes differently; Postgres proof is required before production dispatch claims.',
      forbiddenClaims: [
        'SQLite concurrency proof equals Postgres production safety',
        'Claim lock can be removed in favor of app-level checks only',
      ],
      proofCommands: [
        'cd backend && DATABASE_URL=postgresql+psycopg2://... python -m pytest tests/test_ride_claim_lock_concurrency.py -v',
      ],
      expectedVerdict: 'GO on Postgres when exactly 1 winner and 9 conflicts; do not reopen RIDE-002 without rescope.',
    },
  },
  settlement_copy_lock: {
    id: 'settlement_copy_lock',
    label: 'Settlement copy lock',
    guidance: {
      files: [
        'backend/models/settlement_entry.py',
        'backend/services/ride_settlement.py',
        'backend/tests/test_ride_settlement_ledger.py',
        'driver-app/src/utils/ridePricingDisplay.js',
      ],
      direction:
        'UI copy must say obligation rows / pricing ledger — not payout settled, not Stripe, not bank transfer. Lock strings in tests; cite ride_pricing integer cents and settlement_entries on complete.',
      forbiddenClaims: [
        'Driver was paid',
        'Payment processed',
        'Taxes remitted',
        'PSP capture completed',
      ],
      proofCommands: [
        'cd backend && python -m pytest tests/test_ride_settlement_ledger.py tests/test_pricing_ledger_v01.py -q',
        'cd driver-app && npm test',
      ],
      expectedVerdict: 'GO when UI and docs use obligation/pricing language only; payments lane stays NO_GO.',
    },
  },
}

export const QUICK_ACTION_LIST = Object.values(QUICK_ACTIONS)

/**
 * Pure local lookup — no fetch, no side effects.
 * @param {string} actionId
 * @returns {QuickActionGuidance | null}
 */
export function selectQuickAction(actionId) {
  const entry = QUICK_ACTIONS[actionId]
  return entry ? { ...entry.guidance, actionId: entry.id, label: entry.label } : null
}

/** View model for initial shell render (testable without DOM). */
export function buildShellViewModel() {
  return {
    mode: ENGINEERING_INTELLIGENCE_MODE,
    reportId: REPORT_ID,
    statusChips: STATUS_CHIPS,
    quickActionLabels: QUICK_ACTION_LIST.map((a) => a.label),
    aiConnectionEnabled: false,
    externalProviderConfigured: false,
  }
}

export function isEngineeringIntelligenceEnabled() {
  if (typeof import.meta === 'undefined' || !import.meta.env) {
    return false
  }
  if (import.meta.env.DEV) {
    return true
  }
  return import.meta.env.VITE_ENABLE_ENGINEERING_INTELLIGENCE === '1'
}
