export const READINESS_BLOCKERS = Object.freeze({
  PROFILE_INCOMPLETE: 'profile_incomplete',
  VEHICLE_MISSING: 'vehicle_missing',
  LICENSE_DOCS_MISSING: 'license_docs_missing',
  INSURANCE_MISSING: 'insurance_missing',
  INSURANCE_EXPIRED: 'insurance_expired',
  BACKEND_UNAVAILABLE: 'backend_unavailable',
  APPROVAL_REQUIRED: 'approval_required',
})

const NOT_REGISTERED = new Set(['', 'not registered', 'none', 'null', 'undefined'])

function present(value) {
  return !NOT_REGISTERED.has(String(value ?? '').trim().toLowerCase())
}

function isExpired(value, now = new Date()) {
  if (!value) return false
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return false
  return date.getTime() < now.getTime()
}

function blocker(code, label, actionLabel = 'Complete driver setup') {
  return { code, label, actionLabel }
}

export function buildDriverReadiness({
  accountProfile = null,
  appProfile = null,
  backendUnavailable = false,
  now = new Date(),
} = {}) {
  const blockers = []
  const approvalStatus = String(accountProfile?.approval_status || '').toLowerCase()
  const vehicle = accountProfile?.vehicle || {}

  if (backendUnavailable) {
    blockers.push(
      blocker(
        READINESS_BLOCKERS.BACKEND_UNAVAILABLE,
        'Backend unavailable',
        'Retry readiness check'
      )
    )
  }

  if (
    !present(accountProfile?.name) ||
    !present(accountProfile?.email) ||
    (appProfile && !present(appProfile.display_name) && !present(appProfile.phone_e164))
  ) {
    blockers.push(
      blocker(READINESS_BLOCKERS.PROFILE_INCOMPLETE, 'Profile incomplete')
    )
  }

  if (!present(vehicle.make) || !present(vehicle.model) || !present(vehicle.plate)) {
    blockers.push(
      blocker(READINESS_BLOCKERS.VEHICLE_MISSING, 'Vehicle info missing')
    )
  }

  if (!present(accountProfile?.license_no)) {
    blockers.push(
      blocker(READINESS_BLOCKERS.LICENSE_DOCS_MISSING, 'License/docs missing')
    )
  }

  if (!present(accountProfile?.insurance_policy)) {
    blockers.push(
      blocker(READINESS_BLOCKERS.INSURANCE_MISSING, 'Insurance missing')
    )
  } else if (isExpired(accountProfile?.insurance_expires_at, now)) {
    blockers.push(
      blocker(READINESS_BLOCKERS.INSURANCE_EXPIRED, 'Insurance expired')
    )
  }

  if (approvalStatus !== 'approved') {
    blockers.push(
      blocker(
        READINESS_BLOCKERS.APPROVAL_REQUIRED,
        'Beta approval/manual ops required',
        'Contact operations'
      )
    )
  }

  const primaryBlocker = blockers[0] || null
  return {
    canGoOnline: blockers.length === 0,
    blockers,
    primaryBlocker,
    statusLabel: blockers.length === 0 ? 'Ready to go online' : 'Blocked: setup needed',
    headline:
      blockers.length === 0
        ? 'Ready to go online'
        : 'You are not ready to go online yet',
    nextAction: primaryBlocker?.actionLabel || 'Go online',
  }
}
