/**
 * Format driver-scoped transparency for compact UI rows.
 *
 * @param {Record<string, unknown>} proof
 * @returns {{ label: string, value: string }[]}
 */
export function formatTransparencyLine(proof) {
  if (!proof) return []
  const visibility = proof.visibility || {}
  const claim = proof.claim || {}
  const dismissal = proof.dismissal || {}

  const rows = [
    {
      label: 'Visibility source',
      value: String(visibility.source || 'unknown').replace(/_/g, ' '),
    },
    {
      label: 'Policy',
      value: visibility.policy_name || visibility.policy_version || 'Not provided',
    },
    {
      label: 'Claimable',
      value: claim.claimable ? 'Yes (backend)' : 'No',
    },
    {
      label: 'Ride status',
      value: claim.current_status || 'unknown',
    },
  ]

  if (visibility.reason_codes?.length) {
    rows.push({
      label: 'Reason codes',
      value: visibility.reason_codes.join(', '),
    })
  }

  if (dismissal.hidden_for_this_driver) {
    rows.push({
      label: 'Hidden for you',
      value: dismissal.reason || 'Yes',
    })
  }

  if (claim.last_claim_result && claim.last_claim_result !== 'none') {
    rows.push({
      label: 'Your last claim',
      value: claim.last_claim_result,
    })
  }

  if (claim.claimed_by_driver_id && claim.claimed_by_driver_id !== proof.driver_id) {
    rows.push({
      label: 'Assigned driver',
      value: `Driver #${claim.claimed_by_driver_id}`,
    })
  }

  if (proof.audit?.correlation_id) {
    rows.push({
      label: 'Correlation',
      value: String(proof.audit.correlation_id).slice(0, 12) + '…',
    })
  }

  return rows
}

/**
 * Compact rows for online-idle conflict memory panel.
 *
 * @param {Record<string, unknown> | null} proof
 * @param {number | string | null} rideId
 */
export function formatConflictIdleProof(proof, rideId) {
  if (!proof) {
    return [
      { label: 'Ride', value: rideId != null ? `#${rideId}` : 'Unknown' },
      { label: 'Status', value: 'Conflict recorded by backend' },
      { label: 'Transparency', value: 'Details unavailable' },
    ]
  }

  const visibility = proof.visibility || {}
  const claim = proof.claim || {}
  const audit = proof.audit || {}

  const rows = [
    { label: 'Ride', value: `#${proof.ride_id || rideId}` },
    {
      label: 'last_claim_result',
      value: claim.last_claim_result || 'lost',
    },
    {
      label: 'truth_status',
      value: claim.truth_status || 'backend_conflict',
    },
    {
      label: 'Claimable',
      value: claim.claimable ? 'Yes (backend)' : 'No',
    },
    {
      label: 'Visibility source',
      value: String(visibility.source || 'unknown').replace(/_/g, ' '),
    },
    {
      label: 'Policy',
      value: visibility.policy_name || visibility.policy_version || 'Not provided',
    },
  ]

  if (audit.ledger_event_ids?.length) {
    const ids = audit.ledger_event_ids.slice(0, 4).join(', ')
    const suffix = audit.ledger_event_ids.length > 4 ? '…' : ''
    rows.push({
      label: 'Audit event ids',
      value: `${ids}${suffix}`,
    })
  }

  return rows
}

/**
 * @param {Record<string, unknown> | null} proof
 */
export function hasClaimConflictProofLabel(proof) {
  if (!proof?.truth_labels) return true
  return proof.truth_labels.includes('CLAIM_CONFLICT_PROOF')
}

/**
 * @param {unknown} detail
 */
export function isBackendClaimConflict(detail) {
  if (!detail || typeof detail !== 'object') return false
  return detail.truth_status === 'backend_conflict' || detail.claim_result === 'lost'
}
