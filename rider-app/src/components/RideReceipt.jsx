import React from 'react'

import { formatCents } from '../utils/api.js'

export default function RideReceipt({ payment, ride }) {
  if (!payment && !ride?.pricing?.customer_total_cents) return null

  const amountCents = payment?.amount_cents ?? ride?.pricing?.customer_total_cents
  const status = payment?.status ?? (ride?.status === 'completed' ? 'captured' : 'pending')

  return (
    <div className="rounded-2xl border border-emerald-500/40 bg-emerald-950/40 p-4">
      <p className="text-xs uppercase tracking-wide text-emerald-300">Receipt</p>
      <p className="mt-2 text-2xl font-semibold text-emerald-100">{formatCents(amountCents)}</p>
      <p className="mt-1 text-sm text-slate-300">Payment status: {status}</p>
      {ride?.driver_id ? (
        <p className="mt-2 text-sm text-slate-400">Driver ID {ride.driver_id}</p>
      ) : null}
      {payment?.captured_at ? (
        <p className="mt-1 text-xs text-slate-500">Captured {new Date(payment.captured_at).toLocaleString()}</p>
      ) : null}
    </div>
  )
}
