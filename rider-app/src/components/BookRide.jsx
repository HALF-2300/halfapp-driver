import { useState, useCallback } from 'react'
import { geocodeAddress } from '../utils/geocode.js'
import { estimateFare, formatCents } from '../utils/api.js'

/**
 * Address entry + geocode + fare estimate; fires onRequest with backend field names.
 */
export default function BookRide({ onRequest, disabled, customerName }) {
  const [pickupText, setPickupText] = useState('')
  const [dropoffText, setDropoffText] = useState('')
  const [pickup, setPickup] = useState(null)
  const [dropoff, setDropoff] = useState(null)
  const [resolving, setResolving] = useState(false)
  const [geoError, setGeoError] = useState(null)
  const [fareEstimate, setFareEstimate] = useState(null)

  const resolve = useCallback(async () => {
    setResolving(true)
    setGeoError(null)
    setFareEstimate(null)
    try {
      const [p, d] = await Promise.all([geocodeAddress(pickupText), geocodeAddress(dropoffText)])
      setPickup(p)
      setDropoff(d)
      const est = await estimateFare({
        pickup_latitude: p.lat,
        pickup_longitude: p.lng,
        dropoff_latitude: d.lat,
        dropoff_longitude: d.lng,
      })
      setFareEstimate(est)
    } catch (e) {
      setGeoError(e.message)
      setPickup(null)
      setDropoff(null)
    } finally {
      setResolving(false)
    }
  }, [pickupText, dropoffText])

  const handleRequest = () => {
    if (!pickup || !dropoff) return
    onRequest({
      pickup_lat: pickup.lat,
      pickup_lng: pickup.lng,
      pickup_address: pickup.label,
      dropoff_lat: dropoff.lat,
      dropoff_lng: dropoff.lng,
      dropoff_address: dropoff.label,
      customer_name: customerName,
    })
  }

  const ready = pickup && dropoff && !disabled

  return (
    <div className="book-panel">
      <h2 className="panel-title">Get a ride</h2>

      <div className="field-group">
        <label className="field-label">Pickup</label>
        <div className="address-row">
          <span className="dot dot--pickup" />
          <input
            className="address-input"
            placeholder="Enter pickup address"
            value={pickupText}
            onChange={(e) => {
              setPickupText(e.target.value)
              setPickup(null)
              setFareEstimate(null)
            }}
            disabled={disabled}
          />
        </div>

        <label className="field-label" style={{ marginTop: 8 }}>
          Dropoff
        </label>
        <div className="address-row">
          <span className="dot dot--dropoff" />
          <input
            className="address-input"
            placeholder="Enter destination"
            value={dropoffText}
            onChange={(e) => {
              setDropoffText(e.target.value)
              setDropoff(null)
              setFareEstimate(null)
            }}
            disabled={disabled}
          />
        </div>
      </div>

      {geoError && <p className="error-text">{geoError}</p>}

      {(!pickup || !dropoff) && pickupText && dropoffText && (
        <button
          type="button"
          className="btn btn--secondary"
          onClick={resolve}
          disabled={resolving || disabled}
        >
          {resolving ? 'Looking up addresses…' : 'Confirm addresses'}
        </button>
      )}

      {pickup && dropoff && (
        <div className="fare-estimate" data-testid="fare-estimate">
          <div className="fare-row">
            <span className="fare-label">From</span>
            <span className="fare-value">{pickup.label.split(',')[0]}</span>
          </div>
          <div className="fare-row">
            <span className="fare-label">To</span>
            <span className="fare-value">{dropoff.label.split(',')[0]}</span>
          </div>
          <div className="fare-divider" />
          <div className="fare-row">
            <span className="fare-label">Estimated fare</span>
            <span className="fare-value fare-value--price">
              {fareEstimate?.amount_cents != null
                ? formatCents(fareEstimate.amount_cents)
                : '—'}
            </span>
          </div>
          <div className="fare-row">
            <span className="fare-label">Payment</span>
            <span className="fare-value">Test record · no charge</span>
          </div>
        </div>
      )}

      <button
        type="button"
        className="btn btn--primary"
        data-testid="request-ride-btn"
        onClick={handleRequest}
        disabled={!ready}
      >
        Request ride
      </button>
    </div>
  )
}
