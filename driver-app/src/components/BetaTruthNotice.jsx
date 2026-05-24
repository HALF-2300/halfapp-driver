import React from 'react'
import {
  BETA_CALCULATED_VALUE_LABEL,
  BETA_COCKPIT_BANNER_BODY,
  BETA_COCKPIT_BANNER_TITLE,
  BETA_NO_MONEY_HEADLINE,
  BETA_NO_MONEY_SUBHEAD,
  BETA_NO_MONEY_TRUTH_ENABLED,
  BETA_OBLIGATION_NOT_PAYOUT,
  BETA_OPEN_BOARD_DISPATCH,
  BETA_ROUTE_ESTIMATE_DISCLAIMER,
  BETA_VALUES_ARE_TEST_VALUES,
} from '../utils/betaTruthCopy.js'

/**
 * Compact no-money beta boundary notice (build flag: VITE_BETA_NO_MONEY_TRUTH=true).
 */
export default function BetaTruthNotice({ variant = 'compact' }) {
  if (!BETA_NO_MONEY_TRUTH_ENABLED) return null

  if (variant === 'inline') {
    return (
      <p className="ha-truth-note" data-testid="beta-truth-notice">
        {BETA_CALCULATED_VALUE_LABEL}
      </p>
    )
  }

  if (variant === 'cockpit') {
    return (
      <div
        className="rounded-[14px] border border-sky-500/25 bg-sky-950/50 px-3 py-2 text-left"
        data-testid="beta-truth-notice"
        role="status"
      >
        <p className="text-[10px] font-semibold uppercase tracking-wide text-sky-300/90">
          {BETA_COCKPIT_BANNER_TITLE}
        </p>
        <p className="mt-0.5 text-[11px] font-semibold text-sky-100">{BETA_NO_MONEY_HEADLINE}</p>
        <p className="mt-1 text-[10px] text-sky-100/85">{BETA_COCKPIT_BANNER_BODY}</p>
      </div>
    )
  }

  return (
    <div
      className="ha-card border border-sky-500/25 bg-sky-950/40 mb-4"
      data-testid="beta-truth-notice"
      role="status"
    >
      <p className="text-xs font-semibold text-sky-200">{BETA_NO_MONEY_HEADLINE}</p>
      <p className="text-[11px] mt-1 text-sky-100/90">{BETA_NO_MONEY_SUBHEAD}</p>
      <ul className="mt-2 space-y-1 text-[11px] text-sky-100/90 list-disc pl-4">
        <li>{BETA_VALUES_ARE_TEST_VALUES}</li>
        <li>{BETA_OBLIGATION_NOT_PAYOUT}</li>
        <li>{BETA_OPEN_BOARD_DISPATCH}</li>
        {variant === 'full' ? <li>{BETA_ROUTE_ESTIMATE_DISCLAIMER}</li> : null}
      </ul>
    </div>
  )
}
