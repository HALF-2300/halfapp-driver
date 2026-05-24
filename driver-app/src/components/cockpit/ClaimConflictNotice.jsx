import React from 'react'
import {
  BETA_CLAIM_CONFLICT_BODY,
  BETA_CLAIM_CONFLICT_HEADLINE,
} from '../../utils/betaTruthCopy.js'
import TruthBadge from './TruthBadge.jsx'

export default function ClaimConflictNotice() {
  return (
    <div
      className="claim-conflict-proof-panel"
      data-testid="claim-conflict-notice"
      data-truth-status="backend_conflict"
      data-claim-result="lost"
    >
      <div className="claim-conflict-proof-panel__header">
        <p className="claim-conflict-proof-panel__eyebrow">Dispatch proof</p>
        <TruthBadge kind="BACKEND_OWNED">Backend-owned conflict</TruthBadge>
      </div>
      <p className="claim-conflict-proof-panel__headline">{BETA_CLAIM_CONFLICT_HEADLINE}</p>
      <p className="claim-conflict-proof-panel__body">{BETA_CLAIM_CONFLICT_BODY}</p>
      <div className="claim-conflict-proof-panel__dot" aria-hidden="true" />
      <div className="flex justify-start">
        <span className="text-[10px] text-rose-100/90">409 resolved from backend audit trail</span>
      </div>
    </div>
  )
}
