import React, { useEffect, useState } from 'react'
import { formatCents, listMerchantDeliveryOrders, merchantAcceptDeliveryOrder, merchantMarkDeliveryPreparing, merchantMarkDeliveryReady, merchantRejectDeliveryOrder } from '../utils/api.js'
import { deliveryBadgeTone, deliveryStatusLabel } from '../utils/deliveryContracts.js'

export default function MerchantDeliveryPortal() {
  const [accessCode, setAccessCode] = useState(() => localStorage.getItem('merchant_delivery_access_code') || 'local-pearl-market')
  const [orders, setOrders] = useState([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const load = async () => {
    if (!accessCode) return
    try {
      localStorage.setItem('merchant_delivery_access_code', accessCode)
      const payload = await listMerchantDeliveryOrders(accessCode)
      setOrders(payload.orders || [])
      setError('')
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const act = async (orderId, action) => {
    setBusy(true)
    setError('')
    try {
      if (action === 'accept') await merchantAcceptDeliveryOrder(orderId, accessCode)
      if (action === 'reject') await merchantRejectDeliveryOrder(orderId, accessCode, 'merchant_rejected_from_portal')
      if (action === 'preparing') await merchantMarkDeliveryPreparing(orderId, accessCode)
      if (action === 'ready') await merchantMarkDeliveryReady(orderId, accessCode)
      await load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="ops-command-shell" style={{ minHeight: '100vh', padding: 24 }} data-testid="merchant-delivery-portal">
      <section className="ops-card" style={{ maxWidth: 980, margin: '0 auto', padding: 18, display: 'grid', gap: 16 }}>
        <div>
          <p className="ops-command-eyebrow">Merchant delivery portal</p>
          <h1 style={{ margin: '4px 0', fontSize: 28 }}>Order queue</h1>
          <p style={{ margin: 0, color: 'var(--ops-muted)' }}>
            Minimal merchant surface for local testing. Full merchant accounts and onboarding are still a launch blocker.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <input className="ops-btn" style={{ minWidth: 260 }} value={accessCode} onChange={(event) => setAccessCode(event.target.value)} aria-label="Merchant access code" />
          <button type="button" className="ops-btn ops-btn-primary" onClick={load}>Load queue</button>
        </div>
        {error ? <div className="ops-alert ops-alert--safety">{error}</div> : null}
        {orders.length === 0 ? <div className="ops-empty-state">No orders for this merchant access code.</div> : (
          <div style={{ display: 'grid', gap: 12 }}>
            {orders.map((order) => (
              <article key={order.id} className="ops-proof-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                  <div>
                    <strong>Order #{order.id}</strong>
                    <p style={{ margin: '4px 0', color: 'var(--ops-muted)' }}>{order.items_summary || 'Items pending merchant detail'}</p>
                    <span className={`ops-status-badge ${deliveryBadgeTone(order.status)}`}>{deliveryStatusLabel(order.status)}</span>
                  </div>
                  <strong>{formatCents(order.pricing?.merchant_payout_cents)}</strong>
                </div>
                <p style={{ color: 'var(--ops-muted)' }}>
                  Dropoff: {order.dropoff_address}<br />
                  Notes: {order.delivery_notes || 'No delivery notes'}
                </p>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {order.status === 'paid' ? (
                    <>
                      <button className="ops-btn ops-btn-primary" disabled={busy} onClick={() => act(order.id, 'accept')}>Accept</button>
                      <button className="ops-btn ops-btn-danger" disabled={busy} onClick={() => act(order.id, 'reject')}>Reject</button>
                    </>
                  ) : null}
                  {order.status === 'merchant_accepted' ? <button className="ops-btn ops-btn-primary" disabled={busy} onClick={() => act(order.id, 'preparing')}>Start preparing</button> : null}
                  {order.status === 'preparing' ? <button className="ops-btn ops-btn-primary" disabled={busy} onClick={() => act(order.id, 'ready')}>Ready for pickup</button> : null}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  )
}
