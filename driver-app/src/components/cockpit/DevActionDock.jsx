import React from 'react'
import { BETA_SIMULATION_RIDE_LABEL } from '../../utils/betaTruthCopy.js'

/** Dev-only compact FAB — must not read as a production primary CTA */
export default function DevActionDock({ onCreateRide, disabled, visible }) {
  if (!visible) return null
  return (
    <button
      type="button"
      onClick={onCreateRide}
      disabled={disabled}
      data-testid="dev-demo-ride-btn"
      aria-label={BETA_SIMULATION_RIDE_LABEL}
      title={BETA_SIMULATION_RIDE_LABEL}
      className="dev-action-fab cockpit-pressable disabled:opacity-50"
    >
      DEV · Simulation ride
    </button>
  )
}
