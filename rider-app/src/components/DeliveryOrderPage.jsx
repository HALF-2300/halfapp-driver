import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import RiderAppShell from './RiderAppShell.jsx'
import { createDeliveryOrder, fetchMyDeliveryOrders, formatCents, quoteDelivery } from '../utils/api.js'
import { deliveryStatusLabel } from '../utils/deliveryContracts.js'
import { useAuth } from '../hooks/useAuth.jsx'

const DEFAULT_FORM = {
  merchant_name: 'Pearl Market',
  pickup_address: '10 Market St',
  dropoff_address: '88 Local Ave',
  items_summary: 'Noodle bowl, sparkling water',
  delivery_notes: 'Contactless dropoff preferred',
  items_subtotal_cents: 2400,
  distance_km: 3.2,
  tip_cents: 500,
  contactless: true,
}

function Field({ label, children }) {
  return (
    <label style={{ display: 'grid', gap: 6, fontSize: 13, color: 'var(--rider-muted)' }}>
      <span>{label}</span>
      {children}
    </label>
  )
}

export default function DeliveryOrderPage() {
  const navigate = useNavigate()
  const { logout } = useAuth()
  const [form, setForm] = useState(DEFAULT_FORM)
  const [quote, setQuote] = useState(null)
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const update = (name, value) => {
    setForm((current) => ({ ...current, [name]: value }))
  }

  const loadOrders = async () => {
    try {
      const payload = await fetchMyDeliveryOrders()
      setOrders(payload.orders || [])
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    loadOrders()
  }, [])

  const previewQuote = async () => {
    setError('')
    try {
      const payload = await quoteDelivery({
        items_subtotal_cents: Number(form.items_subtotal_cents),
        distance_km: Number(form.distance_km),
        tip_cents: Number(form.tip_cents),
      })
      setQuote(payload.quote)
    } catch (err) {
      setError(err.message)
    }
  }

  const submit = async (event) => {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const payload = await createDeliveryOrder({
        ...form,
        items_subtotal_cents: Number(form.items_subtotal_cents),
        distance_km: Number(form.distance_km),
        tip_cents: Number(form.tip_cents),
      })
      navigate(`/delivery/${payload.order.id}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <RiderAppShell onSignOut={logout}>
      <section className="rider-card" style={{ padding: 18, display: 'grid', gap: 18 }} data-testid="customer-delivery-flow">
        <div>
          <p className="rider-command-eyebrow">Local delivery</p>
          <h1 style={{ margin: '4px 0 6px', fontSize: 28 }}>Create a delivery order</h1>
          <p style={{ margin: 0, color: 'var(--rider-muted)', lineHeight: 1.5 }}>
            A real backend order is created with delivery lifecycle, transparent pricing, and a local test payment hold.
          </p>
        </div>

        {error ? <div className="rider-alert rider-alert--safety">{error}</div> : null}

        <form onSubmit={submit} style={{ display: 'grid', gap: 12 }}>
          <Field label="Store or merchant">
            <input className="input-field" value={form.merchant_name} onChange={(e) => update('merchant_name', e.target.value)} />
          </Field>
          <Field label="Pickup address">
            <input className="input-field" value={form.pickup_address} onChange={(e) => update('pickup_address', e.target.value)} />
          </Field>
          <Field label="Dropoff address">
            <input className="input-field" value={form.dropoff_address} onChange={(e) => update('dropoff_address', e.target.value)} />
          </Field>
          <Field label="Items">
            <textarea className="input-field" rows={3} value={form.items_summary} onChange={(e) => update('items_summary', e.target.value)} />
          </Field>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 10 }}>
            <Field label="Subtotal cents">
              <input className="input-field" type="number" min="0" value={form.items_subtotal_cents} onChange={(e) => update('items_subtotal_cents', e.target.value)} />
            </Field>
            <Field label="Distance km">
              <input className="input-field" type="number" min="0" step="0.1" value={form.distance_km} onChange={(e) => update('distance_km', e.target.value)} />
            </Field>
            <Field label="Tip cents">
              <input className="input-field" type="number" min="0" value={form.tip_cents} onChange={(e) => update('tip_cents', e.target.value)} />
            </Field>
          </div>
          <Field label="Delivery notes">
            <input className="input-field" value={form.delivery_notes} onChange={(e) => update('delivery_notes', e.target.value)} />
          </Field>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--rider-muted)', fontSize: 13 }}>
            <input type="checkbox" checked={form.contactless} onChange={(e) => update('contactless', e.target.checked)} />
            Contactless delivery
          </label>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            <button type="button" className="rider-btn rider-btn-quiet" onClick={previewQuote}>
              Preview price
            </button>
            <button type="submit" className="rider-btn rider-btn-primary" disabled={loading}>
              {loading ? 'Creating order...' : 'Place delivery order'}
            </button>
          </div>
        </form>

        {quote ? (
          <div className="rider-proof-card" data-testid="delivery-price-breakdown">
            <h2 style={{ margin: '0 0 10px', fontSize: 18 }}>Transparent price breakdown</h2>
            {[
              ['Items', quote.items_subtotal_cents],
              ['Delivery fee', quote.delivery_fee_cents],
              ['Service fee', quote.service_fee_cents],
              ['Small order fee', quote.small_order_fee_cents],
              ['Tax', quote.tax_cents],
              ['Tip', quote.tip_cents],
              ['Customer total', quote.customer_charge_cents],
            ].map(([label, cents]) => (
              <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
                <span style={{ color: 'var(--rider-muted)' }}>{label}</span>
                <strong>{formatCents(cents)}</strong>
              </div>
            ))}
          </div>
        ) : null}

        <div>
          <h2 style={{ margin: '0 0 10px', fontSize: 18 }}>Recent delivery orders</h2>
          {orders.length === 0 ? (
            <div className="rider-empty-state">No delivery orders yet.</div>
          ) : (
            <div style={{ display: 'grid', gap: 10 }}>
              {orders.map((order) => (
                <Link key={order.id} to={`/delivery/${order.id}`} className="rider-proof-card" style={{ color: 'inherit', textDecoration: 'none' }}>
                  <strong>#{order.id} · {order.merchant_name}</strong>
                  <p style={{ margin: '4px 0 0', color: 'var(--rider-muted)' }}>
                    {deliveryStatusLabel(order.status)} · {formatCents(order.pricing?.customer_charge_cents)}
                  </p>
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>
    </RiderAppShell>
  )
}
