const STEPS = [
  { key: 'requested', label: 'Requested' },
  { key: 'assigned', label: 'Assigned' },
  { key: 'in_progress', label: 'In progress' },
  { key: 'completed', label: 'Completed' },
]

function stepIndex(status) {
  if (status === 'cancelled') return -1
  if (status === 'completed') return 3
  if (status === 'in_progress') return 2
  if (status === 'driver_arrived' || status === 'accepted') return 1
  return 0
}

export default function RideStatusTimeline({ ride, statusLabel }) {
  const active = stepIndex(ride?.status)
  const terminal = ride?.status === 'cancelled' || ride?.status === 'completed'

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-4">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs uppercase tracking-wide text-cyan-300">Ride status</p>
        <p className="text-sm font-medium text-slate-100">{statusLabel}</p>
      </div>
      {ride?.status === 'cancelled' ? (
        <p className="mt-3 text-sm text-amber-200">This ride was cancelled.</p>
      ) : (
        <ol className="mt-4 grid grid-cols-4 gap-1">
          {STEPS.map((step, index) => {
            const done = active > index || (terminal && ride?.status === 'completed' && index <= 3)
            const current = active === index && !terminal
            return (
              <li key={step.key} className="text-center">
                <div
                  className={[
                    'mx-auto h-2 w-2 rounded-full',
                    done ? 'bg-emerald-400' : current ? 'bg-cyan-400' : 'bg-slate-700',
                  ].join(' ')}
                />
                <p className="mt-2 text-[10px] leading-tight text-slate-400">{step.label}</p>
              </li>
            )
          })}
        </ol>
      )}
      {ride?.driver_id && ride.status !== 'cancelled' && (
        <p className="mt-4 text-sm text-slate-300">
          Driver assigned · ID {ride.driver_id}
        </p>
      )}
      {ride?.status === 'completed' && ride?.pricing?.customer_total_cents != null && (
        <p className="mt-2 text-sm font-medium text-emerald-300">
          Total ${(ride.pricing.customer_total_cents / 100).toFixed(2)}
        </p>
      )}
    </div>
  )
}
