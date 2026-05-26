export function riderStatusLabel(ride) {
  const v01 = ride?.v01_lifecycle_status
  const storage = ride?.status

  if (v01 === 'driver_assigned' || storage === 'accepted') return 'Driver assigned'
  if (v01 === 'driver_arriving' || storage === 'driver_arrived') return 'Driver arriving'
  if (v01 === 'in_progress' || storage === 'in_progress') return 'On the way'
  if (v01 === 'completed' || storage === 'completed') return 'Trip complete'
  if (v01 === 'cancelled' || storage === 'cancelled') return 'Cancelled'
  if (v01 === 'priced' || storage === 'requested') return 'Looking for a driver'
  return storage || 'Unknown'
}

export function riderStatusStep(ride) {
  const status = ride?.status
  if (status === 'cancelled') return 0
  if (status === 'completed') return 4
  if (status === 'in_progress') return 3
  if (status === 'driver_arrived') return 2
  if (status === 'accepted') return 2
  if (status === 'requested') return 1
  return 1
}
