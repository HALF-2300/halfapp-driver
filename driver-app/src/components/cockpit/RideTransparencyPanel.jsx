import React, { useCallback, useEffect, useState } from 'react'
import driverAPI from '../../utils/api.js'
import TruthBadge from './TruthBadge.jsx'
import { formatTransparencyLine } from '../../utils/rideTransparency.js'

function ProofRow({ label, value }) {
  return (
    <div className="flex justify-between gap-2 text-[11px]">
      <span className="text-[#AAB6C8]">{label}</span>
      <span className="max-w-[58%] text-right font-medium text-[#F8FAFC]">{value}</span>
    </div>
  )
}

/**
 * Expandable backend transparency for an incoming/active ride.
 */
export default function RideTransparencyPanel({ rideId, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [proof, setProof] = useState(null)

  const loadProof = useCallback(async () => {
    if (!rideId) return
    setLoading(true)
    setError(null)
    try {
      const data = await driverAPI.getRideTransparency(rideId)
      setProof(data)
    } catch (err) {
      setProof(null)
      setError(err?.message || 'Could not load backend transparency')
    } finally {
      setLoading(false)
    }
  }, [rideId])

  useEffect(() => {
    if (open && !proof && !loading && !error) {
      loadProof()
    }
  }, [open, proof, loading, error, loadProof])

  const lines = proof ? formatTransparencyLine(proof) : []

  return (
    <div className="rounded-[18px] border border-white/10 bg-white/[0.03]" data-testid="ride-transparency-panel">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        data-testid="ride-transparency-toggle"
        className="cockpit-pressable flex w-full items-center justify-between px-3 py-2.5 text-left text-[12px] font-semibold text-[#F8FAFC]"
      >
        Why am I seeing this?
        <span className="text-[#AAB6C8]">{open ? '−' : '+'}</span>
      </button>
      {open && (
        <div className="space-y-2 border-t border-white/10 px-3 py-2.5" data-testid="ride-transparency-body">
          {loading && <p className="text-[11px] text-[#AAB6C8]">Loading backend proof…</p>}
          {error && (
            <p className="text-[11px] text-amber-300" data-testid="ride-transparency-error">
              {error}
            </p>
          )}
          {proof && (
            <>
              <div className="flex flex-wrap gap-1" data-testid="ride-transparency-truth-labels">
                {(proof.truth_labels || []).slice(0, 6).map((label) => (
                  <TruthBadge key={label} kind="BACKEND_OWNED">
                    {label.replace(/_/g, ' ')}
                  </TruthBadge>
                ))}
              </div>
              <div className="space-y-1.5">
                {lines.map((row) => (
                  <ProofRow key={row.label} label={row.label} value={row.value} />
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
