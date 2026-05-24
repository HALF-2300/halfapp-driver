import React, { useCallback, useEffect, useState } from 'react'

import driverAPI from '../../utils/api.js'

const CRL_DISCLAIMER =
  'Based on recent activity patterns in the app. Not a guarantee.'

export default function CityRealityPanel({ open, onClose }) {
  const [cells, setCells] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [selected, setSelected] = useState(null)
  const [explain, setExplain] = useState(null)

  const loadMap = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const json = await driverAPI.getCrlMap({ window: '30m' })
      setCells(json?.cells || [])
    } catch (err) {
      setCells([])
      setError(err?.message || 'Could not load city patterns')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!open) return
    loadMap()
    setSelected(null)
    setExplain(null)
  }, [open, loadMap])

  const loadExplain = useCallback(async (h3) => {
    setSelected(h3)
    setExplain(null)
    try {
      const json = await driverAPI.getCrlExplain(h3)
      setExplain(json)
    } catch {
      setExplain({ not_enough_data: true, label: 'Could not load explanation.' })
    }
  }, [])

  if (!open) return null

  return (
    <div
      className="absolute left-[18px] right-[18px] bottom-[200px] z-[25] max-h-[50vh] overflow-y-auto rounded-2xl border border-white/10 bg-[#0f1419]/95 p-3 shadow-2xl"
      data-testid="city-reality-panel"
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <h2 className="text-[13px] font-semibold text-[#F8FAFC]">City Reality</h2>
        <button
          type="button"
          onClick={onClose}
          className="cockpit-pressable rounded-full px-2 py-1 text-[11px] text-[#AAB6C8]"
        >
          Close
        </button>
      </div>

      <p className="text-[10px] leading-snug text-[#94a3b8] mb-2">{CRL_DISCLAIMER}</p>
      <p className="text-[10px] text-[#64748b] mb-3">
        Explains what may be driving activity — not just where it appears on the map.
      </p>

      {loading ? (
        <p className="text-[11px] text-[#94a3b8]">Loading patterns…</p>
      ) : null}
      {error ? <p className="text-[11px] text-amber-300">{error}</p> : null}

      <ul className="space-y-2">
        {cells.length === 0 && !loading ? (
          <li className="text-[11px] text-[#94a3b8]" data-testid="crl-not-enough">
            Not enough recent activity to estimate patterns here.
          </li>
        ) : null}
        {cells.map((cell) => (
          <li key={cell.h3}>
            <button
              type="button"
              className="w-full text-left rounded-xl border border-white/10 px-3 py-2 hover:bg-white/5"
              onClick={() => loadExplain(cell.h3)}
              data-testid="crl-cell-row"
            >
              <div className="text-[11px] font-medium text-[#E2E8F0]">{cell.label}</div>
              <div className="text-[10px] text-[#94a3b8] mt-1">
                Confidence: {cell.confidence_band || cell.confidence} · Cause:{' '}
                {cell.primary_cause?.replace(/_/g, ' ')}
              </div>
            </button>
          </li>
        ))}
      </ul>

      {selected && explain ? (
        <div
          className="mt-3 border-t border-white/10 pt-3 text-[10px] text-[#CBD5E1]"
          data-testid="crl-explain-detail"
        >
          <div className="font-semibold text-[#F8FAFC] mb-1">Why this area?</div>
          <p>{explain.label}</p>
          {explain.signals_used ? (
            <p className="mt-2 text-[#64748b]">
              Pattern factors recorded (aggregated only).
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
