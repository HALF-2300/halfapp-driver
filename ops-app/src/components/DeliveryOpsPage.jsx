import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { formatCents, listDeliveryOrders } from '../utils/api.js'
import { deliveryBadgeTone, deliveryStatusLabel } from '../utils/deliveryContracts.js'

export default function DeliveryOpsPage() {
  const [orders, setOrders] = useState([])
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const payload = await listDeliveryOrders({ status: status || undefined })
      setOrders(payload.orders || [])
      setError('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [status])

  return (
    <section data-testid="ops-delivery-monitor" style={{ display: 'grid', gap: 16 }}>
      <div>
        <p className="ops-command-eyebrow">Delivery control plane</p>
        <h1 style={{ margin: '4px 0', fontSize: 28 }}>Delivery orders</h1>
        <p style={{ margin: 0, color: 'var(--ops-muted)' }}>
          Supervises delivery orders separately from people-transport rides.
        </p>
      </div>
      <div className="ops-alert">
        Delivery payment is a local test hold in this skeleton. Settlement rows are obligation records for ops review.
      </div>
      <label style={{ color: 'var(--ops-muted)', display: 'grid', gap: 6, maxWidth: 280 }}>
        Filter status
        <select className="ops-btn" value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="">All delivery statuses</option>
          {['paid', 'merchant_accepted', 'preparing', 'ready_for_pickup', 'courier_assigned', 'picked_up', 'en_route', 'delivered', 'cancelled', 'refunded', 'failed'].map((item) => (
            <option key={item} value={item}>{deliveryStatusLabel(item)}</option>
          ))}
        </select>
      </label>
      {error ? <div className="ops-alert ops-alert--safety">{error}</div> : null}
      {loading ? <div className="ops-skeleton" style={{ height: 120 }} /> : null}
      {!loading && orders.length === 0 ? <div className="ops-empty-state">No delivery orders match this view.</div> : null}
      {orders.length > 0 ? (
        <div className="ops-card" style={{ overflow: 'hidden' }}>
          <table className="ops-table">
            <thead>
              <tr>
                <th>Order</th>
                <th>Status</th>
                <th>Merchant</th>
                <th>Courier</th>
                <th>Customer total</th>
                <th>Settlement</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((order) => (
                <tr key={order.id}>
                  <td><Link to={`/deliveries/${order.id}`} style={{ color: '#d8ebff' }}>#{order.id}</Link></td>
                  <td><span className={`ops-status-badge ${deliveryBadgeTone(order.status)}`}>{deliveryStatusLabel(order.status)}</span></td>
                  <td>{order.merchant_name}</td>
                  <td>{order.courier_id || 'Unassigned'}</td>
                  <td>{formatCents(order.pricing?.customer_charge_cents)}</td>
                  <td>{formatCents(order.pricing?.merchant_payout_cents)} merchant · {formatCents(order.pricing?.courier_payout_cents)} courier</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  )
}
