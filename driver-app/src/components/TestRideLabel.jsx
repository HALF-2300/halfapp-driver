import React from 'react'
import { testRideLabelForLifecycleReason } from '../utils/betaTruthCopy.js'

/** Shows beta/simulation/ops test ride label when lifecycle_reason warrants it. */
export default function TestRideLabel({ lifecycleReason, testId = 'test-ride-label' }) {
  const label = testRideLabelForLifecycleReason(lifecycleReason)
  if (!label) return null
  return (
    <span
      className="inline-block rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-semibold text-amber-200"
      data-testid={testId}
    >
      {label}
    </span>
  )
}
