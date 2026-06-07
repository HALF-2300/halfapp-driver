const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'
const TOKEN_KEY = 'rider_token'
const ROLE_KEY = 'rider_role'

function parseErrorDetail(detail) {
  if (!detail) return 'Request failed'
  if (typeof detail === 'string') return detail
  if (typeof detail === 'object' && detail.message) return detail.message
  return JSON.stringify(detail)
}

async function request(path, { method = 'GET', body, token } = {}) {
  const headers = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const authToken = token ?? localStorage.getItem(TOKEN_KEY)
  if (authToken) headers.Authorization = `Bearer ${authToken}`

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  const text = await res.text()
  let payload = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = { detail: text }
    }
  }

  if (!res.ok) {
    throw new Error(parseErrorDetail(payload?.detail) || `HTTP ${res.status}`)
  }
  return payload
}

export function getApiBase() {
  return API_BASE
}

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(ROLE_KEY)
}

export function persistSession(response) {
  localStorage.setItem(TOKEN_KEY, response.access_token)
  localStorage.setItem(ROLE_KEY, response.role || 'customer')
}

export async function registerRider({ email, name, password }) {
  const response = await request('/auth/rider/register', {
    method: 'POST',
    body: { email, name, password, role: 'customer' },
  })
  if (response.role !== 'customer') {
    throw new Error('Registration failed: expected customer role')
  }
  persistSession(response)
  return response
}

export async function loginRider(email, password) {
  const response = await request('/auth/rider/login', {
    method: 'POST',
    body: { email, password },
  })
  if (response.role !== 'customer') {
    throw new Error('Login failed: rider access only')
  }
  persistSession(response)
  return response
}

export async function fetchProfile() {
  return request('/auth/me')
}

export async function createRide(payload) {
  return request('/rides/', { method: 'POST', body: payload })
}

export async function fetchRide(rideId) {
  return request(`/rides/${rideId}`)
}

export async function fetchPresentJob(rideId) {
  return request(`/present/jobs/${rideId}`)
}

export async function cancelRide(rideId, reason) {
  return request(`/rides/${rideId}/cancel`, {
    method: 'POST',
    body: reason ? { reason } : {},
  })
}

export function subscribeRideStatus(
  rideId,
  { onStatus, onDriverLocation, onFareUpdate, onEtaUpdate, onError },
) {
  const token = getStoredToken()
  if (!token) {
    onError?.(new Error('Not authenticated'))
    return () => {}
  }

  let closed = false
  let pollTimer = null
  let source = null

  const applyStatus = (status, ride) => {
    onStatus?.(status, ride)
    if (status === 'completed' || status === 'cancelled') {
      cleanup()
    }
  }

  const poll = async () => {
    try {
      const payload = await fetchRide(rideId)
      applyStatus(payload.ride.status, payload.ride)
    } catch (err) {
      onError?.(err)
    }
  }

  const startPolling = () => {
    if (pollTimer) return
    pollTimer = window.setInterval(poll, 3000)
    poll()
  }

  const cleanup = () => {
    closed = true
    if (source) {
      source.close()
      source = null
    }
    if (pollTimer) {
      window.clearInterval(pollTimer)
      pollTimer = null
    }
  }

  try {
    source = new EventSource(
      `${API_BASE}/rides/${rideId}/stream?access_token=${encodeURIComponent(token)}`,
    )
    const handleStatusPayload = async (data) => {
      try {
        const payload = await fetchRide(rideId)
        applyStatus(data.status ?? payload.ride.status, payload.ride)
      } catch (err) {
        onError?.(err)
      }
    }

    source.addEventListener('status_change', (event) => {
      try {
        handleStatusPayload(JSON.parse(event.data))
      } catch (err) {
        onError?.(err)
      }
    })
    source.addEventListener('driver_location', (event) => {
      try {
        onDriverLocation?.(JSON.parse(event.data))
      } catch {
        /* ignore malformed */
      }
    })
    source.addEventListener('fare_update', (event) => {
      try {
        onFareUpdate?.(JSON.parse(event.data))
      } catch {
        /* ignore malformed */
      }
    })
    source.addEventListener('eta_update', (event) => {
      try {
        onEtaUpdate?.(JSON.parse(event.data))
      } catch {
        /* ignore malformed */
      }
    })

    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'status_change' || data.status) {
          handleStatusPayload(data)
        } else if (data.lat != null && data.lng != null) {
          onDriverLocation?.(data)
        } else if (data.fare_cents != null) {
          onFareUpdate?.(data)
        } else if (data.eta_seconds != null) {
          onEtaUpdate?.(data)
        }
      } catch (err) {
        onError?.(err)
      }
    }
    source.onerror = () => {
      if (closed) return
      if (source) {
        source.close()
        source = null
      }
      startPolling()
    }
  } catch {
    startPolling()
  }

  return cleanup
}

export function formatCents(cents) {
  if (!Number.isFinite(Number(cents))) return '—'
  return `$${(Number(cents) / 100).toFixed(2)}`
}

export async function estimateFare(payload) {
  return request('/rides/estimate', { method: 'POST', body: payload })
}

export async function fetchRidePayment(rideId) {
  return request(`/rides/${rideId}/payment`)
}

export async function fetchMyRides(limit = 30) {
  return request(`/rides/my-rides?limit=${limit}`)
}

export async function quoteDelivery(payload) {
  return request('/delivery/quote', { method: 'POST', body: payload })
}

export async function createDeliveryOrder(payload) {
  return request('/delivery/orders', { method: 'POST', body: payload })
}

export async function fetchDeliveryOrder(orderId) {
  return request(`/delivery/orders/${orderId}`)
}

export async function fetchMyDeliveryOrders() {
  return request('/delivery/orders/customer')
}

export async function cancelDeliveryOrder(orderId, reason) {
  return request(`/delivery/orders/${orderId}/cancel`, {
    method: 'POST',
    body: reason ? { reason } : {},
  })
}

export async function createSupportCase(body) {
  return request('/support/cases', { method: 'POST', body })
}

export async function fetchSafetyToolkit() {
  return request('/safety/toolkit')
}

export async function fetchNotifications() {
  return request('/notifications/')
}

export async function markNotificationRead(deliveryId) {
  return request(`/notifications/${deliveryId}/read`, { method: 'PATCH' })
}

import { riderStatusLabel, riderStatusStep } from './riderStatus.js'

export { riderStatusLabel, riderStatusStep }
