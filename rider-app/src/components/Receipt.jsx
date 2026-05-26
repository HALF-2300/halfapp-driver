/**
 * Post-trip receipt — amounts from ledger payment or ride pricing only.
 */
export default function Receipt({ payment, ride, driver, onDone }) {
  if (!payment && ride?.status === 'completed') {
    return (
      <div className="receipt receipt--loading">
        <div className="receipt-spinner" />
        <p>Settling payment…</p>
      </div>
    )
  }

  if (!payment) return null

  const { fare_cents, currency = 'USD', payment_method, settled_at, trip_id, source } = payment

  const fareFmt = new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(
    (fare_cents ?? 0) / 100,
  )
  const dateStr = settled_at
    ? new Date(settled_at).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      })
    : '—'

  return (
    <div className="receipt">
      <div className="receipt-header">
        <span className="receipt-check">✓</span>
        <h2 className="receipt-title">Trip complete</h2>
      </div>

      <div className="receipt-fare">{fareFmt}</div>

      <div className="receipt-rows">
        <ReceiptRow
          label="Trip"
          value={`${ride?.pickup_location?.split(',')[0] ?? '—'} → ${(ride?.dropoff_location || ride?.destination || '—').split(',')[0]}`}
        />
        <ReceiptRow label="Driver" value={driver?.name ?? (ride?.driver_id ? `Driver #${ride.driver_id}` : '—')} />
        <ReceiptRow label="Payment" value={payment_method?.label ?? '—'} />
        <ReceiptRow label="Date" value={dateStr} />
        <ReceiptRow label="Trip ID" value={String(trip_id ?? ride?.id ?? '—')} mono />
      </div>

      {source === 'RIDE_PRICING' && (
        <p className="receipt-disclaimer">Pricing from ride ledger row — payment record pending.</p>
      )}

      <button type="button" className="btn btn--primary" onClick={onDone}>
        Book another ride
      </button>
    </div>
  )
}

function ReceiptRow({ label, value, mono }) {
  return (
    <div className="receipt-row">
      <span className="receipt-row-label">{label}</span>
      <span className={`receipt-row-value${mono ? ' mono' : ''}`}>{value}</span>
    </div>
  )
}
