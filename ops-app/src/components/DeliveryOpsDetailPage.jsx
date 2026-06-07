import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { fetchDeliveryOrderForOps, formatCents, refundDeliveryOrder } from '../utils/api.js'
import { deliveryBadgeTone, deliveryStatusLabel } from '../utils/deliveryContracts.js'

export default function DeliveryOpsDetailPage() {
  const { orderId } = useParams()
  const [detail, setDetail] = useState(null)
  const [refundAmount, setRefundAmount] = useState(300)
  const [error, setError] = useState('')

  const load = async () => {
    try {
      setDetail(await fetchDeliveryOrderForOps(orderId))
      setError('')
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    load()
  }, [orderId])

  const refund = async () => {
    try {
      setDetail(await refundDeliveryOrder(orderId, { amount_cents: Number(refundAmount), reason: 'ops_review_refund' }))
    } catch (err) {
      setError(err.message)
    }
  }

  const order = detail?.order

  return (
    <section data-testid="ops-delivery-detail" style={{ display: 'grid', gap: 16 }}>
      <Link to="/deliveries" style={{ color: 'var(--ops-accent)' }}>← Delivery monitor</Link>
      {error ? <div className="ops-alert ops-alert--safety">{error}</div> : null}
      {!order ? <div className="ops-skeleton" style={{ height: 160 }} /> : (
        <>
          <div className="ops-card" style={{ padding: 18 }}>
            <p className="ops-command-eyebrow">Delivery order #{order.id}</p>
            <h1 style={{ margin: '4px 0', fontSize: 28 }}>{order.merchant_name}</h1>
            <span className={`ops-status-badge ${deliveryBadgeTone(order.status)}`}>{deliveryStatusLabel(order.status)}</span>
            <p style={{ color: 'var(--ops-muted)' }}>
              Merchant access code: <strong>{order.merchant_access_code}</strong>
            </p>
          </div>
          <div className="ops-card" style={{ padding: 18, display: 'grid', gap: 10 }}>
            <h2 style={{ margin: 0, fontSize: 18 }}>Financial summary</h2>
            {[
              ['Customer charge', order.pricing?.customer_charge_cents],
              ['Merchant payout obligation', order.pricing?.merchant_payout_cents],
              ['Courier payout obligation', order.pricing?.courier_payout_cents],
              ['Platform fee', order.pricing?.platform_fee_cents],
              ['Refunded', order.pricing?.refunded_cents],
            ].map(([label, cents]) => (
              <div key={label} style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: 'var(--ops-muted)' }}>{label}</span>
                <strong>{formatCents(cents)}</strong>
              </div>
            ))}
          </div>
          <div className="ops-card" style={{ padding: 18, display: 'grid', gap: 10 }}>
            <h2 style={{ margin: 0, fontSize: 18 }}>Refund eligibility</h2>
            <p style={{ margin: 0, color: 'var(--ops-muted)' }}>
              {order.refund?.eligible ? `Refundable: ${formatCents(order.refund.refundable_cents)}` : `Not refundable: ${order.refund?.reason}`}
            </p>
            <div style={{ display: 'flex', gap: 8 }}>
              <input className="ops-btn" type="number" min="1" value={refundAmount} onChange={(event) => setRefundAmount(event.target.value)} />
              <button type="button" className="ops-btn ops-btn-primary" onClick={refund}>Record refund</button>
            </div>
          </div>
          <div className="ops-card" style={{ padding: 18 }}>
            <h2 style={{ margin: '0 0 10px', fontSize: 18 }}>Settlement entries</h2>
            <table className="ops-table">
              <thead>
                <tr>
                  <th>Party</th>
                  <th>Type</th>
                  <th>Amount</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {(detail.settlement_entries || []).map((entry) => (
                  <tr key={entry.id || `${entry.entry_type}-${entry.amount_cents}`}>
                    <td>{entry.party}</td>
                    <td>{entry.entry_type}</td>
                    <td>{formatCents(entry.amount_cents)}</td>
                    <td>{entry.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  )
}
