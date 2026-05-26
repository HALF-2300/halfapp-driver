const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'
const TOKEN_KEY = 'ops_token'
const ROLE_KEY = 'ops_role'

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

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(ROLE_KEY)
}

export function persistSession(response) {
  localStorage.setItem(TOKEN_KEY, response.access_token)
  localStorage.setItem(ROLE_KEY, response.role || 'admin')
}

export async function loginAdmin(email, password) {
  const response = await request('/auth/admin/login', {
    method: 'POST',
    body: { email, password },
  })
  if (response.role !== 'admin') {
    throw new Error('Login failed: admin access only')
  }
  persistSession(response)
  return response
}

export async function fetchProfile() {
  return request('/auth/me')
}

export async function listRides({ status } = {}) {
  const query = status ? `?status=${encodeURIComponent(status)}` : ''
  return request(`/admin/rides${query}`)
}

export async function getRide(rideId) {
  return request(`/admin/rides/${rideId}`)
}

export async function cancelRide(rideId, reason) {
  return request(`/admin/rides/${rideId}/cancel`, {
    method: 'POST',
    body: reason ? { reason } : {},
  })
}

export async function assignRide(rideId, driverId) {
  return request(`/admin/rides/${rideId}/assign`, {
    method: 'POST',
    body: { driver_id: driverId },
  })
}

export async function listDrivers() {
  return request('/admin/drivers')
}

export async function updateDriverReadiness(driverId, body) {
  return request(`/admin/drivers/${driverId}/readiness`, {
    method: 'PATCH',
    body,
  })
}

export function formatCents(cents) {
  if (cents == null) return '—'
  return `$${(Number(cents) / 100).toFixed(2)}`
}

export function formatDate(value) {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return String(value)
  }
}

export function statusBadgeClass(status) {
  const s = (status || '').toLowerCase()
  if (s === 'completed' || s === 'captured') return 'bg-emerald-900/50 text-emerald-200'
  if (s === 'cancelled' || s === 'failed') return 'bg-red-900/40 text-red-200'
  if (s === 'in_progress' || s === 'accepted' || s === 'authorized') return 'bg-sky-900/40 text-sky-200'
  if (s === 'requested' || s === 'pending') return 'bg-amber-900/40 text-amber-200'
  return 'bg-slate-800 text-slate-300'
}
