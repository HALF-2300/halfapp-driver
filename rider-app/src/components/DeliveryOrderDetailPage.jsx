import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import RiderAppShell from './RiderAppShell.jsx'
import { cancelDeliveryOrder, fetchDeliveryOrder, formatCents } from '../utils/api.js'
import { DELIVERY_TIMELINE, deliveryStatusLabel, deliveryStepIndex } from '../utils/deliveryContracts.js'
import { useAuth } from '../hooks/useAuth.jsx'

export default function DeliveryOrderDetailPage() {
  const { orderId } = useParams()
  const { logout } = useAuth()
  const [order, setOrder] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const payload = await fetchDeliveryOrder(orderId)
      setOrder(payload.order)
      setError('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    const timer = window.setInterval(load, 4000)
    return () => window.clearInterval(timer)
  }, [orderId])

  const cancel = async () => {
    try {
      const payload = await cancelDeliveryOrder(orderId, 'customer_cancelled_from_delivery_screen')
      setOrder(payload.order)
    } catch (err) {
      setError(err.message)
    }
  }

  const activeIndex = deliveryStepIndex(order?.status)
  const canCancel = ['created', 'priced', 'paid', 'merchant_accepted', 'preparing', 'ready_for_pickup', 'courier_assigned'].includes(order?.status)

  return (
    <RiderAppShell onSignOut={logout}>
      <section className="rider-card" style={{ padding: 18, display: 'grid', gap: 16 }} data-testid="customer-delivery-detail">
        <Link to="/delivery" style={{ color: 'var(--rider-accent)', textDecoration: 'none' }}>← Delivery orders</Link>
        {loading ? <div className="rider-skeleton" style={{ height: 120 }} /> : null}
        {error ? <div className="rider-alert rider-alert--safety">{error}</div> : null}
        {order ? (
          <>
            <div>
              <p className="rider-command-eyebrow">Order #{order.id}</p>
              <h1 style={{ margin: '4px 0', fontSize: 28 }}>{order.merchant_name}</h1>
              <span className="rider-status-badge rider-status-badge--active">{deliveryStatusLabel(order.status)}</span>
            </div>

            <div className="rider-proof-card">
              <h2 style={{ margin: '0 0 10px', fontSize: 18 }}>Status timeline</h2>
              <div style={{ display: 'grid', gap: 8 }}>
                {DELIVERY_TIMELINE.map((status, index) => (
                  <div key={status} style={{ display: 'flex', gap: 10, alignItems: 'center', color: index <= activeIndex ? 'var(--rider-text)' : 'var(--rider-subtle)' }}>
                    <span style={{ width: 12, height: 12, borderRadius: 999, background: index <= activeIndex ? 'var(--rider-teal)' : 'var(--rider-border)' }} />
                    <span>{deliveryStatusLabel(status)}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rider-proof-card" data-testid="delivery-receipt-view">
              <h2 style={{ margin: '0 0 10px', fontSize: 18 }}>Receipt</h2>
              {[
                ['Items', order.pricing?.items_subtotal_cents],
                ['Delivery fee', order.pricing?.delivery_fee_cents],
                ['Service fee', order.pricing?.service_fee_cents],
                ['Tax', order.pricing?.tax_cents],
                ['Tip', order.pricing?.tip_cents],
                ['Total', order.pricing?.customer_charge_cents],
                ['Refunded', order.pricing?.refunded_cents],
              ].map(([label, cents]) => (
                <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
                  <span style={{ color: 'var(--rider-muted)' }}>{label}</span>
                  <strong>{formatCents(cents)}</strong>
                </div>
              ))}
              <p style={{ color: 'var(--rider-muted)', fontSize: 12 }}>
                Payment truth: {order.payment?.truth_label || 'local test hold only'}.
              </p>
            </div>

            <div className="rider-proof-card">
              <h2 style={{ margin: '0 0 10px', fontSize: 18 }}>Delivery details</h2>
              <p><strong>Pickup:</strong> {order.pickup_address}</p>
              <p><strong>Dropoff:</strong> {order.dropoff_address}</p>
              <p><strong>Items:</strong> {order.items_summary || 'Items recorded by merchant'}</p>
              <p><strong>Notes:</strong> {order.delivery_notes || 'No notes'}</p>
              <p><strong>Merchant access code:</strong> {order.merchant_access_code}</p>
            </div>

            {canCancel ? (
              <button type="button" className="rider-btn rider-btn-quiet" onClick={cancel}>
                Cancel order
              </button>
            ) : null}
          </>
        ) : null}
      </section>
    </RiderAppShell>
  )
}
