import React from 'react'
import TruthBadge from './TruthBadge.jsx'
import {
  formatConflictIdleProof,
  hasClaimConflictProofLabel,
} from '../../utils/rideTransparency.js'

function ProofRow({ label, value }) {
  return (
    <div className="flex justify-between gap-2 text-[11px]">
      <span className="text-[#AAB6C8]">{label}</span>
      <span className="max-w-[58%] text-right font-medium text-[#F8FAFC]">{value}</span>
    </div>
  )
}

/**
 * Backend conflict proof shown on online-idle after a 409 claim loss.
 * Session UI only — not marketplace truth storage.
 */
export default function ConflictTransparencyMemory({
  rideId,
  proof,
  loading,
  unavailable,
}) {
  const rows = unavailable
    ? formatConflictIdleProof(null, rideId)
    : formatConflictIdleProof(proof, rideId)

  return (
    <div
      className="rounded-[18px] border border-white/10 bg-white/[0.03] px-3 py-2.5 space-y-2"
      data-testid="conflict-transparency-memory"
      data-conflict-ride-id={rideId ?? undefined}
    >
      <p className="text-[11px] font-semibold uppercase tracking-wide text-[#AAB6C8]">
        Backend conflict proof
      </p>
      {loading && (
        <p className="text-[11px] text-[#AAB6C8]" data-testid="conflict-transparency-loading">
          Loading backend transparency…
        </p>
      )}
      {!loading && unavailable && (
        <p className="text-[11px] text-amber-200/90" data-testid="conflict-transparency-unavailable">
          Conflict recorded by backend · Transparency details unavailable
        </p>
      )}
      {!loading && (
        <>
          <div className="flex flex-wrap gap-1" data-testid="conflict-idle-truth-labels">
            <TruthBadge kind="BACKEND_OWNED">Backend conflict proof</TruthBadge>
            {(proof == null || hasClaimConflictProofLabel(proof)) && (
              <TruthBadge kind="BACKEND_OWNED">CLAIM_CONFLICT_PROOF</TruthBadge>
            )}
          </div>
          <div className="space-y-1">
            {rows.map((row) => (
              <ProofRow key={row.label} label={row.label} value={row.value} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
