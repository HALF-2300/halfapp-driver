import React, { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import AppShellLayout from './AppShellLayout.jsx'
import RidePayoutSummary from './cockpit/RidePayoutSummary.jsx'
import TruthBadge from './cockpit/TruthBadge.jsx'
import driverAPI from '../utils/api.js'
import { formatCents } from '../utils/ridePricingDisplay.js'
import RouteTruthDetails from './cockpit/RouteTruthDetails.jsx'
import {
  BETA_AUDIT_DISCLAIMER,
  BETA_AUDIT_OBLIGATION_LABEL,
  BETA_SETTLEMENT_SECTION_NOTE,
} from '../utils/betaTruthCopy.js'
import {
  auditUsesObligationLanguage,
  buildAuditPricingForSummary,
  formatAuditEventType,
  formatSettlementEntryLabel,
} from '../utils/tripAuditFormat.js'
import TestRideLabel from './TestRideLabel.jsx'
import BetaTruthNotice from './BetaTruthNotice.jsx'
import { BETA_CALCULATED_VALUE_LABEL, BETA_NO_MONEY_TRUTH_ENABLED } from '../utils/betaTruthCopy.js'

function Section({ title, children, testId }) {
  return (
    <section className="ha-section" data-testid={testId}>
      <h2 className="ha-section-title">{title}</h2>
      <div className="ha-card space-y-3">{children}</div>
    </section>
  )
}

function Row({ label, value, testId }) {
  return (
    <div className="flex justify-between gap-3 text-xs" data-testid={testId}>
      <span style={{ color: 'var(--ha-muted)' }}>{label}</span>
      <span className="text-right font-medium" style={{ color: 'var(--ha-text)' }}>
        {value ?? '—'}
      </span>
    </div>
  )
}

function formatWhen(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
  })
}

export default function TripAuditReceipt() {
  const { rideId } = useParams()
  const [audit, setAudit] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [technicalOpen, setTechnicalOpen] = useState(false)
  const [issueText, setIssueText] = useState('')
  const [issueSent, setIssueSent] = useState(false)
  const [issueError, setIssueError] = useState(null)

  const load = useCallback(() => {
    if (!rideId) return
    setLoading(true)
    setError(null)
    driverAPI
      .getRideAudit(rideId)
      .then((data) => setAudit(data || null))
      .catch((err) => {
        setAudit(null)
        setError(err?.message || 'Could not load trip audit')
      })
      .finally(() => setLoading(false))
  }, [rideId])

  useEffect(() => {
    load()
  }, [load])

  const pricingForSummary = buildAuditPricingForSummary(audit)
  const lifecycleEvents = audit?.lifecycle_events || []
  const ledgerEvents = audit?.ledger_events || []
  const settlementEntries = audit?.settlement_entries || []
  const payoutHeadline =
    audit?.pricing?.driver_payout_cents != null
      ? formatCents(audit.pricing.driver_payout_cents)
      : null

  const disclaimerText = audit?.copy?.settlement_meaning || BETA_AUDIT_DISCLAIMER
  const primaryMoneyTruthSentence =
    'This is a server-calculated record. Pricing is locked by the server. No payout has been sent.'
  const shouldShowPrimaryMoneyTruth = (() => {
    const d = String(disclaimerText || '').toLowerCase()
    const p = primaryMoneyTruthSentence.toLowerCase()
    return !(d.includes('server-calculated record') || d.includes('no payout has been sent') || d.includes(p))
  })()

  return (
    <AppShellLayout
      title="Trip audit"
      subtitle="Read-only backend receipt details"
      testId="trip-audit-page"
      headerAction={
        <Link to="/driver/trips" className="text-xs font-semibold" style={{ color: 'var(--ha-green)' }}>
          ← Trips
        </Link>
      }
    >
      <BetaTruthNotice />
      <p className="ha-truth-note mb-4" data-testid="trip-audit-disclaimer">
        {disclaimerText}
      </p>

      {loading ? <div className="ha-card ha-empty">Loading audit…</div> : null}
      {error ? <div className="ha-alert ha-alert--warn">{error}</div> : null}

      {audit && shouldShowPrimaryMoneyTruth ? (
        <div
          data-testid="trip-audit-money-truth-summary"
          className="mb-3 rounded-lg bg-slate-50 p-3 text-sm text-slate-800"
        >
          {primaryMoneyTruthSentence}
        </div>
      ) : null}

      <section className="ha-section" data-testid="trip-audit-report-issue">
        <h2 className="ha-section-title">Report an issue</h2>
        <div className="ha-card space-y-3">
          <p className="text-xs ha-truth-note">
            Sends an internal support ticket for ops review — not live rider support chat.
          </p>
          <textarea
            className="w-full text-sm rounded-lg p-2 min-h-[80px]"
            value={issueText}
            onChange={(e) => setIssueText(e.target.value)}
            placeholder="Describe what went wrong on this trip…"
            data-testid="trip-audit-issue-input"
          />
          <button
            type="button"
            className="ha-btn ha-btn--ghost"
            disabled={!issueText.trim()}
            data-testid="trip-audit-issue-submit"
            onClick={async () => {
              setIssueError(null)
              try {
                await driverAPI.reportRideIssue(rideId, issueText.trim())
                setIssueSent(true)
                setIssueText('')
              } catch (err) {
                setIssueError(err?.message || 'Could not submit report')
              }
            }}
          >
            Submit report
          </button>
          {issueSent ? (
            <p className="text-xs" style={{ color: 'var(--ha-green)' }}>
              Report submitted. Ops can review the ticket in the backend.
            </p>
          ) : null}
          {issueError ? <p className="text-xs text-amber-300">{issueError}</p> : null}
        </div>
      </section>

      {audit ? (
        <div className="space-y-4" data-testid="trip-audit-body">
          {payoutHeadline ? (
            <section className="ha-card trip-audit-hero" data-testid="trip-audit-payout-headline">
              <p className="text-[11px] uppercase tracking-wide" style={{ color: 'var(--ha-muted)' }}>
                Driver earnings (backend ledger)
              </p>
              <p className="text-2xl font-bold mt-1" style={{ color: 'var(--ha-text)' }}>
                {payoutHeadline}
              </p>
              {BETA_NO_MONEY_TRUTH_ENABLED ? (
                <p className="text-[11px] mt-1 ha-truth-note" data-testid="trip-audit-calculated-test-label">
                  {BETA_CALCULATED_VALUE_LABEL}
                </p>
              ) : null}
              {auditUsesObligationLanguage(audit) ? (
                <p
                  className="text-xs mt-2 font-medium"
                  style={{ color: 'var(--ha-green)' }}
                  data-testid="trip-audit-obligation-label"
                >
                  {BETA_AUDIT_OBLIGATION_LABEL}
                </p>
              ) : null}
            </section>
          ) : null}

          <div className="flex flex-wrap gap-2">
            {(audit.truth_labels || []).map((label) => (
              <TruthBadge key={label}>{String(label).replace(/_/g, ' ')}</TruthBadge>
            ))}
          </div>

          <Section title="Ride" testId="trip-audit-ride">
            <div className="mb-2">
              <TestRideLabel lifecycleReason={audit.lifecycle_reason} testId="trip-audit-test-label" />
            </div>
            <Row label="Ride ID" value={audit.ride_id} testId="trip-audit-ride-id" />
            <Row label="Status" value={audit.status} />
            <Row
              label="Financial locked"
              value={audit.financial_locked ? 'Yes' : 'No'}
              testId="trip-audit-financial-locked"
            />
            {auditUsesObligationLanguage(audit) && !payoutHeadline ? (
              <p className="text-[11px]" style={{ color: 'var(--ha-muted)' }} data-testid="trip-audit-obligation-copy">
                {BETA_AUDIT_OBLIGATION_LABEL}
              </p>
            ) : null}
          </Section>

          {pricingForSummary ? (
            <Section title="Pricing breakdown" testId="trip-audit-pricing">
              <RidePayoutSummary
                pricing={pricingForSummary}
                locked={Boolean(audit.financial_locked)}
                variant="final"
              />
            </Section>
          ) : null}

          {settlementEntries.length > 0 ? (
            <Section title="Settlement obligations" testId="trip-audit-settlement">
              <p className="text-[11px] mb-2" style={{ color: 'var(--ha-muted)' }}>
                {BETA_SETTLEMENT_SECTION_NOTE}
              </p>
              <ul className="space-y-2">
                {settlementEntries.map((entry) => (
                  <li
                    key={entry.id ?? `${entry.entry_type}-${entry.party}`}
                    className="rounded-lg border border-white/10 px-3 py-2 text-xs"
                    data-testid="trip-audit-settlement-row"
                  >
                    <div className="flex justify-between gap-2 font-medium">
                      <span>{formatSettlementEntryLabel(entry)}</span>
                      <span>{formatCents(entry.amount_cents)}</span>
                    </div>
                    <div className="mt-1 text-[10px]" style={{ color: 'var(--ha-muted)' }}>
                      Status: {entry.settlement_status || '—'} · Source: {entry.source || '—'}
                    </div>
                  </li>
                ))}
              </ul>
            </Section>
          ) : null}

          {ledgerEvents.length > 0 ? (
            <Section title="Marketplace ledger events" testId="trip-audit-ledger">
              <ul className="space-y-2">
                {ledgerEvents.map((event, index) => (
                  <li
                    key={`${event.event_type}-${event.occurred_at}-${index}`}
                    className="text-xs"
                    data-testid="trip-audit-ledger-row"
                  >
                    <div className="font-medium">{formatAuditEventType(event.event_type)}</div>
                    <div style={{ color: 'var(--ha-muted)' }}>{formatWhen(event.occurred_at)}</div>
                  </li>
                ))}
              </ul>
            </Section>
          ) : null}

          {lifecycleEvents.length > 0 ? (
            <Section title="Lifecycle timeline" testId="trip-audit-lifecycle">
              <ul className="space-y-2 max-h-64 overflow-y-auto">
                {lifecycleEvents.map((event, index) => (
                  <li
                    key={`${event.event_type}-${event.occurred_at}-${index}`}
                    className="text-xs border-b border-white/5 pb-2"
                    data-testid="trip-audit-lifecycle-row"
                  >
                    <div className="font-medium">{formatAuditEventType(event.event_type)}</div>
                    <div style={{ color: 'var(--ha-muted)' }}>
                      {formatWhen(event.occurred_at)} · {event.source}
                    </div>
                  </li>
                ))}
              </ul>
            </Section>
          ) : null}

          {rideId ? (
            <Section title="Route truth" testId="trip-audit-route">
              <RouteTruthDetails rideId={rideId} embedded defaultOpen={false} />
            </Section>
          ) : null}

          {(ledgerEvents.length > 0 || audit.copy?.payment_execution) ? (
            <section className="trip-truth-details" data-testid="trip-audit-technical">
              <button
                type="button"
                onClick={() => setTechnicalOpen((v) => !v)}
                aria-expanded={technicalOpen}
                data-testid="trip-audit-technical-toggle"
                className="trip-truth-details__toggle cockpit-pressable"
              >
                <span>Technical proof</span>
                <span>{technicalOpen ? '−' : '+'}</span>
              </button>
              {technicalOpen ? (
                <div className="trip-truth-details__body" data-testid="trip-audit-technical-body">
                  <p
                    className="text-[11px] mb-2"
                    style={{ color: 'var(--ha-muted)' }}
                    data-testid="trip-audit-payment-execution"
                  >
                    Payment execution: {audit.copy?.payment_execution || 'not_implemented'}
                  </p>
                  {ledgerEvents.map((event, index) => (
                    <div key={`tech-${event.event_hash || index}`} className="text-[11px] mb-2">
                      <div className="font-medium">{event.event_type}</div>
                      {event.correlation_id ? (
                        <div style={{ color: 'var(--ha-muted)' }}>correlation: {event.correlation_id}</div>
                      ) : null}
                      {event.idempotency_key ? (
                        <div style={{ color: 'var(--ha-muted)' }}>idempotency: {event.idempotency_key}</div>
                      ) : null}
                      {event.event_hash ? (
                        <div style={{ color: 'var(--ha-muted)' }} data-testid="trip-audit-event-hash">
                          hash: {event.event_hash.slice(0, 16)}…
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : null}
            </section>
          ) : null}
        </div>
      ) : null}
    </AppShellLayout>
  )
}
