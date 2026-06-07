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

export async function fetchPresentJob(rideId) {
  return request(`/present/jobs/${rideId}`)
}

export async function fetchReadinessBoard() {
  return request('/admin/readiness-board')
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

export async function listSupportCases({ status, category, ride_id, limit } = {}) {
  const params = new URLSearchParams()
  if (status) params.set('status', status)
  if (category) params.set('category', category)
  if (ride_id != null) params.set('ride_id', String(ride_id))
  if (limit != null) params.set('limit', String(limit))
  const q = params.toString()
  return request(`/support/cases${q ? `?${q}` : ''}`)
}

export async function getSupportCase(caseId) {
  return request(`/support/cases/${caseId}`)
}

export async function updateSupportCaseStatus(caseId, status) {
  return request(`/support/cases/${caseId}/status`, {
    method: 'PATCH',
    body: { status },
  })
}

export async function listDeliveryOrders({ status } = {}) {
  const query = status ? `?status=${encodeURIComponent(status)}` : ''
  return request(`/delivery/ops/orders${query}`)
}

export async function fetchDeliveryOrderForOps(orderId) {
  return request(`/delivery/ops/orders/${orderId}`)
}

export async function refundDeliveryOrder(orderId, body) {
  return request(`/delivery/ops/orders/${orderId}/refund`, {
    method: 'POST',
    body,
  })
}

export async function listMerchantDeliveryOrders(merchantAccessCode) {
  return request(`/delivery/merchant/orders?merchant_access_code=${encodeURIComponent(merchantAccessCode)}`)
}

export async function merchantAcceptDeliveryOrder(orderId, merchantAccessCode) {
  return request(`/delivery/merchant/orders/${orderId}/accept?merchant_access_code=${encodeURIComponent(merchantAccessCode)}`, {
    method: 'POST',
  })
}

export async function merchantRejectDeliveryOrder(orderId, merchantAccessCode, reason) {
  return request(`/delivery/merchant/orders/${orderId}/reject?merchant_access_code=${encodeURIComponent(merchantAccessCode)}`, {
    method: 'POST',
    body: { reason },
  })
}

export async function merchantMarkDeliveryPreparing(orderId, merchantAccessCode) {
  return request(`/delivery/merchant/orders/${orderId}/preparing?merchant_access_code=${encodeURIComponent(merchantAccessCode)}`, {
    method: 'POST',
  })
}

export async function merchantMarkDeliveryReady(orderId, merchantAccessCode) {
  return request(`/delivery/merchant/orders/${orderId}/ready?merchant_access_code=${encodeURIComponent(merchantAccessCode)}`, {
    method: 'POST',
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
  if (s === 'open') return 'bg-amber-900/50 text-amber-100'
  if (s === 'in_review') return 'bg-sky-900/40 text-sky-200'
  if (s === 'waiting_on_user') return 'bg-violet-900/40 text-violet-200'
  if (s === 'resolved' || s === 'closed') return 'bg-emerald-900/50 text-emerald-200'
  if (s === 'completed' || s === 'captured') return 'bg-emerald-900/50 text-emerald-200'
  if (s === 'cancelled' || s === 'failed') return 'bg-red-900/40 text-red-200'
  if (s === 'in_progress' || s === 'accepted' || s === 'authorized') return 'bg-sky-900/40 text-sky-200'
  if (s === 'requested' || s === 'pending') return 'bg-amber-900/40 text-amber-200'
  return 'bg-slate-800 text-slate-300'
}

export function supportCategoryBadgeClass(category) {
  const c = (category || '').toLowerCase()
  if (c === 'safety_concern') return 'bg-red-900/60 text-red-100 border border-red-400/40'
  if (c === 'lost_item') return 'bg-amber-900/40 text-amber-100'
  if (c === 'ride_issue') return 'bg-sky-900/40 text-sky-100'
  return 'bg-slate-800/80 text-slate-300'
}

export function supportCategoryLabel(category) {
  const c = (category || '').toLowerCase()
  if (c === 'safety_concern') return 'Safety concern'
  if (c === 'lost_item') return 'Lost item'
  if (c === 'ride_issue') return 'Ride issue'
  return category || '—'
}
