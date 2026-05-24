import React, { useCallback, useMemo, useState } from 'react'

const DEFAULT_SLICE =
  'HALFAPP_NEXT_BACKEND_TRUTH_SLICE — pick one small contract from docs/HALFAPP_AGENT_ACTION_DIRECTIVES.md'

/**
 * Dev-only planning helper — copies a structured agent prompt. Does not execute code or mutate data.
 */
export default function AgentBriefGenerator({ activeSurface = 'driver cockpit (MapHome)' }) {
  const [nextSlice, setNextSlice] = useState(DEFAULT_SLICE)
  const [copied, setCopied] = useState(false)

  const brief = useMemo(() => {
    const date = new Date().toISOString().slice(0, 10)
    return `# HalfApp Agent Brief (dev planning only)
Date: ${date}
Model target: Sonnet 4.6

## Active surface
${activeSurface}

## Next recommended slice
${nextSlice.trim() || DEFAULT_SLICE}

## Files to inspect
- driver-app/src/components/MapHome.jsx
- driver-app/src/components/cockpit/
- driver-app/src/utils/api.js
- backend/main.py
- docs/CURRENT_TRUTH.md
- docs/RIDE_LIFECYCLE_CONTRACT.md
- docs/HALFAPP_ARCHITECTURE_DOSSIER_EXTRACTION_01.md

## Constraints
- Backend truth only for marketplace facts (presence, rides, claims, fares, earnings).
- No localStorage as marketplace truth.
- No invented ETA/route/nearest-driver claims.
- No Kafka, PostGIS, WebSockets, or double-entry ledger unless explicitly scoped.
- Minimize diff; match existing conventions.

## Tests required
- driver-app: npm test (unit)
- driver-app: npm run test:e2e (cockpit-identity, map-cockpit-truth)
- backend: pytest on touched lifecycle/dispatch paths

## Final report format
Return markdown:
# Final Report: <SLICE_ID>
## Verdict — GO | PARTIAL_GO | NO_GO
## What changed
## Backend truth preserved
## Tests run
## Not built
## Next small slice

---
DEV ONLY — Agent Brief Generator. Does not execute code or claim work is done.
`
  }, [activeSurface, nextSlice])

  const copyBrief = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(brief)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }, [brief])

  if (!import.meta.env.DEV) return null

  return (
    <section
      className="mt-4 rounded-[16px] border border-violet-400/30 bg-violet-950/30 p-3"
      data-testid="agent-brief-generator"
    >
      <p className="text-[11px] font-semibold uppercase tracking-wide text-violet-200">
        DEV ONLY — Agent Brief Generator
      </p>
      <p className="mt-1 text-[10px] text-[#AAB6C8]">
        Copies a structured prompt for Sonnet 4.6. Does not run agents or mutate production data.
      </p>
      <label className="mt-2 block text-[10px] text-[#AAB6C8]" htmlFor="agent-brief-next-slice">
        Next slice
      </label>
      <input
        id="agent-brief-next-slice"
        type="text"
        value={nextSlice}
        onChange={(e) => setNextSlice(e.target.value)}
        className="mt-1 w-full rounded-lg border border-white/10 bg-black/40 px-2 py-1.5 text-[11px] text-[#F8FAFC]"
      />
      <pre className="mt-2 max-h-[140px] overflow-y-auto rounded-lg border border-white/5 bg-black/50 p-2 text-[9px] leading-snug text-[#AAB6C8] whitespace-pre-wrap">
        {brief.slice(0, 480)}…
      </pre>
      <button
        type="button"
        onClick={copyBrief}
        data-testid="agent-brief-copy-btn"
        className="cockpit-pressable mt-2 rounded-full border border-violet-400/40 bg-violet-500/25 px-3 py-1.5 text-[11px] font-medium text-violet-100"
      >
        {copied ? 'Copied' : 'Copy brief'}
      </button>
    </section>
  )
}
