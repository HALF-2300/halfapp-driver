/** User-facing copy for driver ride request / accept errors (UX-001). */

export function friendlyAcceptError(err) {
  const detail = err?.detail
  if (err?.status === 409) {
    if (detail?.reason === 'ride_already_claimed' || String(detail?.detail || '').includes('claimed')) {
      return 'Ride taken by another driver'
    }
    if (detail?.error === 'invalid_state_transition') {
      return 'This ride is no longer available'
    }
  }
  if (typeof detail === 'string' && detail.includes('claimed')) {
    return 'Ride taken by another driver'
  }
  return err?.message && !String(err.message).startsWith('{') ? err.message : 'Could not accept ride'
}
