import React, { useEffect, useState } from 'react'
import AppShellLayout from './AppShellLayout.jsx'
import driverAPI from '../utils/api.js'
import { deliveryStatusLabel, locationHealthLabel, nextCourierDeliveryAction } from '../utils/deliveryContracts.js'
import { useDriverGeolocation } from '../hooks/useDriverGeolocation.js'

function money(cents) {
  if (cents == null) return '$0.00'
  return `$${(Number(cents) / 100).toFixed(2)}`
}

function OrderCard({ order, onAction, busy }) {
  const nextAction = nextCourierDeliveryAction(order.status)
  return (
    <article className="ha-card" style={{ padding: 16, display: 'grid', gap: 10 }} data-testid="courier-delivery-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
        <div>
          <p className="ha-badge">Delivery #{order.id}</p>
          <h2 style={{ margin: '8px 0 4px', fontSize: 20 }}>{order.merchant_name}</h2>
          <p style={{ margin: 0, color: 'var(--ha-muted)' }}>{deliveryStatusLabel(order.status)}</p>
        </div>
        <strong>{money(order.pricing?.courier_payout_cents)}</strong>
      </div>
      <div className="ha-alert">
        <strong>Pickup:</strong> {order.pickup_address}<br />
        <strong>Dropoff:</strong> {order.dropoff_address}<br />
        <strong>Items:</strong> {order.items_summary || 'Merchant item record'}
      </div>
      {order.status === 'ready_for_pickup' ? (
        <button type="button" className="ha-button ha-button--primary" disabled={busy} onClick={() => onAction(order.id, 'accept')}>
          Accept delivery offer
        </button>
      ) : null}
      {nextAction ? (
        <button type="button" className="ha-button ha-button--success" disabled={busy} onClick={() => onAction(order.id, nextAction)}>
          {nextAction === 'pickup' ? 'Confirm pickup' : nextAction === 'en_route' ? 'Start delivery route' : 'Mark delivered with proof'}
        </button>
      ) : null}
    </article>
  )
}

export default function DeliveryJobs() {
  const geo = useDriverGeolocation()
  const [offers, setOffers] = useState([])
  const [mine, setMine] = useState([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const load = async () => {
    try {
      const [offerPayload, myPayload] = await Promise.all([
        driverAPI.getDeliveryOffers(),
        driverAPI.getMyDeliveryOrders(),
      ])
      setOffers(offerPayload.orders || [])
      setMine(myPayload.orders || [])
      setError('')
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    load()
    const timer = window.setInterval(load, 5000)
    return () => window.clearInterval(timer)
  }, [])

  const act = async (orderId, action) => {
    setBusy(true)
    setError('')
    try {
      if (action === 'accept') await driverAPI.acceptDeliveryOrder(orderId)
      if (action === 'pickup') await driverAPI.pickupDeliveryOrder(orderId)
      if (action === 'en_route') await driverAPI.startDeliveryOrder(orderId)
      if (action === 'delivered') {
        await driverAPI.deliverDeliveryOrder(orderId, {
          proof_reference: `courier-confirmed-${orderId}`,
          dropoff_note: 'Courier marked dropoff complete',
        })
      }
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <AppShellLayout
      title="Delivery jobs"
      subtitle="Courier delivery offers are separate from ride offers"
      testId="courier-delivery-flow"
    >
      <div style={{ display: 'grid', gap: 16, paddingBottom: 96 }}>
        <section className="ha-alert">
          <strong>Location health:</strong> {locationHealthLabel(geo)}
          {geo.accuracyMeters != null ? ` · ${Math.round(geo.accuracyMeters)}m accuracy` : ''}
          <br />
          <span style={{ color: 'var(--ha-muted)' }}>
            GPS denied, stale, or unavailable states are shown here and do not stop delivery actions.
          </span>
        </section>
        {error ? <section className="ha-alert ha-alert--safety">{error}</section> : null}
        <section style={{ display: 'grid', gap: 10 }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>Available delivery offers</h2>
          {offers.length === 0 ? (
            <div className="ha-empty-state"><strong>No delivery offers</strong> Merchant-ready orders will appear here.</div>
          ) : offers.map((order) => (
            <OrderCard key={order.id} order={order} onAction={act} busy={busy} />
          ))}
        </section>
        <section style={{ display: 'grid', gap: 10 }}>
          <h2 style={{ margin: 0, fontSize: 18 }}>My active deliveries</h2>
          {mine.length === 0 ? (
            <div className="ha-empty-state"><strong>No assigned deliveries</strong> Accepted delivery orders stay separate from ride trips.</div>
          ) : mine.map((order) => (
            <OrderCard key={order.id} order={order} onAction={act} busy={busy} />
          ))}
        </section>
      </div>
    </AppShellLayout>
  )
}
