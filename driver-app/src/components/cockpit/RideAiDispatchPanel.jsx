import React from 'react'
import { DISPATCH_AI_STATES, ROUTE_ADVISORY_LABEL } from '../../services/rideAiDispatch/constants.js'

/**
 * Advisory AI panel for ride dispatch loop — read-only; does not control dispatch.
 */
export default function RideAiDispatchPanel({
  panelText,
  panelMeta,
  manualMode,
  dispatchAiState,
  streaming,
  onReset,
}) {
  return (
    <section
      className="mt-3 rounded-[14px] border border-violet-400/25 bg-violet-950/30 p-3"
      data-testid="ride-ai-dispatch-panel"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-wide text-violet-200/90">
            Ride AI (advisory)
          </p>
          <p className="text-[10px] text-violet-200/60" data-testid="ride-ai-dispatch-state">
            State: {dispatchAiState}
            {manualMode ? ' · manual mode' : ''}
            {streaming ? ' · streaming' : ''}
          </p>
        </div>
        <button
          type="button"
          className="text-[10px] text-violet-200/80 underline"
          data-testid="ride-ai-reset"
          onClick={onReset}
        >
          Reset
        </button>
      </div>
      {panelMeta ? (
        <p className="mt-2 text-[10px] text-violet-100/70" data-testid="ride-ai-meta">
          {panelMeta}
        </p>
      ) : null}
      {panelMeta?.includes(ROUTE_ADVISORY_LABEL) || panelText?.includes(ROUTE_ADVISORY_LABEL) ? (
        <p
          className="mt-1 text-[10px] font-medium text-amber-200/90"
          data-testid="ride-ai-route-advisory-label"
        >
          {ROUTE_ADVISORY_LABEL}
        </p>
      ) : null}
      <pre
        className="mt-2 max-h-40 overflow-y-auto whitespace-pre-wrap text-[11px] leading-relaxed text-violet-50/90"
        data-testid="ride-ai-panel-text"
      >
        {panelText || (manualMode ? 'Manual mode — operator drives dispatch without AI.' : 'Waiting for lifecycle event…')}
      </pre>
      {dispatchAiState === DISPATCH_AI_STATES.DECLINED ||
      dispatchAiState === DISPATCH_AI_STATES.REDISPATCHING ? (
        <p className="mt-2 text-[10px] text-amber-100/80">
          Decline / redispatch is advisory only — backend pool handles real assignment.
        </p>
      ) : null}
    </section>
  )
}
