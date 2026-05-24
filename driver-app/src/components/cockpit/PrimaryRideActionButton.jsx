import React from 'react'

const TONES = {
  primary: 'primary-ride-cta--primary',
  success: 'primary-ride-cta--success',
  danger: 'primary-ride-cta--danger',
  neutral: 'primary-ride-cta--neutral',
}

/**
 * Single dominant cockpit CTA — min 44px touch target.
 */
export default function PrimaryRideActionButton({
  children,
  onClick,
  disabled,
  tone = 'primary',
  testId,
  type = 'button',
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      data-testid={testId}
      className={`primary-ride-cta cockpit-pressable ${TONES[tone] ?? TONES.primary}`}
    >
      {children}
    </button>
  )
}
