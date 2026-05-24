import React from 'react'
import { ALLOW_OFFLINE_MOCK, ALLOW_RIDE_SIMULATION } from '../utils/api.js'

/**
 * Visible when offline mock substitution is enabled at build time.
 */
export default function MockModeBanner() {
  if (!ALLOW_OFFLINE_MOCK && !ALLOW_RIDE_SIMULATION) return null
  return (
    <div
      data-testid="mock-mode-banner"
      role="status"
      className="bg-slate-950 border-b border-amber-500/30 px-4 py-2 text-center text-xs font-medium text-amber-200"
    >
      Investor Showcase guard: {ALLOW_OFFLINE_MOCK ? 'offline mock fallback is enabled' : 'offline mock fallback is off'}
      {ALLOW_RIDE_SIMULATION ? '; explicit backend simulation controls are visible' : ''}. Not production launch.
    </div>
  )
}
