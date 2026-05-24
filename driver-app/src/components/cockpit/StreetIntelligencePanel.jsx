import React, { useCallback, useState } from 'react'

import driverAPI from '../../utils/api.js'
import {
  BUSY_LAYER_LABEL,
  ROUTE_LABEL_FALLBACK,
  ROUTE_LABEL_OSRM,
  SIL_MAP_DISCLAIMER,
  SLOW_LAYER_LABEL,
} from '../../utils/streetIntelligenceLabels.js'

export default function StreetIntelligencePanel({
  open,
  onClose,
  showBusy,
  showSlow,
  onToggleBusy,
  onToggleSlow,
  devicePosition,
  activeRide,
}) {
  const [quote, setQuote] = useState(null)
  const [quoteError, setQuoteError] = useState(null)
  const [receipt, setReceipt] = useState(null)
  const [loadingQuote, setLoadingQuote] = useState(false)

  const previewRoute = useCallback(async () => {
    if (!devicePosition || !activeRide?.pickup || !activeRide?.dropoff) {
      setQuoteError('Need GPS and an active ride to preview a route.')
      return
    }
    setLoadingQuote(true)
    setQuoteError(null)
    setReceipt(null)
    try {
      const body = await driverAPI.createSilRouteQuote({
        from_lat: devicePosition.lat,
        from_lng: devicePosition.lng,
        to_lat: activeRide.pickup.lat,
        to_lng: activeRide.pickup.lng,
      })
      setQuote(body)
    } catch (err) {
      setQuote(null)
      setQuoteError(err?.message || 'Could not load route quote')
    } finally {
      setLoadingQuote(false)
    }
  }, [devicePosition, activeRide])

  const viewReceipt = useCallback(async () => {
    if (!quote?.proof_receipt_id) return
    try {
      const summary = await driverAPI.getSilProofReceipt(quote.proof_receipt_id)
      setReceipt(summary)
    } catch {
      setReceipt(null)
    }
  }, [quote])

  if (!open) return null

  const routeLabel =
    quote?.route_method === 'osrm_route' ? ROUTE_LABEL_OSRM : ROUTE_LABEL_FALLBACK

  return (
    <div
      className="absolute left-[18px] right-[18px] bottom-[200px] z-[24] max-h-[45vh] overflow-y-auto rounded-2xl border border-white/10 bg-[#0f1419]/95 p-3 shadow-2xl"
      data-testid="street-intelligence-panel"
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <h2 className="text-[13px] font-semibold text-[#F8FAFC]">Street Intelligence</h2>
        <button
          type="button"
          onClick={onClose}
          className="cockpit-pressable rounded-full px-2 py-1 text-[11px] text-[#AAB6C8]"
        >
          Close
        </button>
      </div>

      <p className="text-[10px] leading-snug text-[#94a3b8] mb-3">{SIL_MAP_DISCLAIMER}</p>

      <div className="space-y-2 text-[11px] text-[#CBD5E1]">
        <label className="flex items-start gap-2">
          <input
            type="checkbox"
            checked={showBusy}
            onChange={(e) => onToggleBusy(e.target.checked)}
            data-testid="sil-toggle-busy"
          />
          <span>
            <span className="font-medium">Estimated Busy Areas</span>
            <span className="block text-[10px] text-[#94a3b8] mt-0.5">{BUSY_LAYER_LABEL}</span>
          </span>
        </label>
        <label className="flex items-start gap-2">
          <input
            type="checkbox"
            checked={showSlow}
            onChange={(e) => onToggleSlow(e.target.checked)}
            data-testid="sil-toggle-slow"
          />
          <span>
            <span className="font-medium">Fleet-Estimated Slow Areas</span>
            <span className="block text-[10px] text-[#94a3b8] mt-0.5">{SLOW_LAYER_LABEL}</span>
          </span>
        </label>
      </div>

      {activeRide ? (
        <div className="mt-3 border-t border-white/10 pt-3">
          <button
            type="button"
            className="cockpit-pressable w-full rounded-xl py-2 text-[11px] font-semibold"
            onClick={previewRoute}
            disabled={loadingQuote}
            data-testid="sil-route-preview-btn"
          >
            {loadingQuote ? 'Loading route…' : 'Route preview (to pickup)'}
          </button>
          {quoteError ? (
            <p className="mt-2 text-[10px] text-amber-300">{quoteError}</p>
          ) : null}
          {quote ? (
            <div className="mt-2 space-y-1 text-[10px] text-[#CBD5E1]" data-testid="sil-route-quote-card">
              <div className="font-semibold text-[#F8FAFC]" data-testid="sil-route-method-badge">
                {routeLabel}
              </div>
              <div data-testid="sil-proof-badge">{quote.proof_badge}</div>
              <div>{quote.eta_honesty}</div>
              <div>
                ~{(quote.distance_m_est / 1000).toFixed(1)} km · ~
                {Math.round((quote.duration_s_est || 0) / 60)} min (estimate)
              </div>
              <button
                type="button"
                className="text-[#38bdf8] underline"
                onClick={viewReceipt}
                data-testid="sil-view-receipt-btn"
              >
                View receipt
              </button>
              {receipt ? (
                <pre className="mt-1 max-h-24 overflow-auto rounded bg-black/40 p-2 text-[9px]">
                  {receipt.receipt_hash?.slice(0, 16)}… · {receipt.proof_level}
                </pre>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
