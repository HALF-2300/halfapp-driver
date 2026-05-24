/** Local-only research snippets — never sent to a model unless user explicitly connects via backend. */

export const LOCAL_RESEARCH_SNIPPETS = Object.freeze({
  current_truth:
    'Review docs/CURRENT_TRUTH.md — active surfaces: backend + driver-app only; no payment settlement; open-board dispatch.',
  agent_directives:
    'Review docs/HALFAPP_AGENT_ACTION_DIRECTIVES.md — P0 lanes closed; next: OSRM runtime proof or production hardening.',
  transparency:
    'Review docs/HALFAPP_TRANSPARENCY_ARCHITECTURE.md — five pillars; ride_pricing integer cents; route_snapshots foundation.',
})

export const QUICK_ACTION_PROMPTS = Object.freeze({
  summarize_truth:
    'Summarize the active HalfApp truth boundary from docs/CURRENT_TRUTH.md. List what may be claimed vs forbidden.',
  next_slice:
    'Recommend the next small backend-truth slice from docs/HALFAPP_AGENT_ACTION_DIRECTIVES.md with tests required.',
  dispatch_audit:
    'Explain how open-board dispatch audit works: visibility, claim attempts, marketplace_ledger_events, structured 409.',
})
