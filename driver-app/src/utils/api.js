// API Configuration and Utilities
// Prefer 127.0.0.1 over localhost: on some Windows setups localhost resolves to ::1 while the API binds IPv4 only.
import { subscribeRidePool } from './sseClient.js'
import {
  buildMockPricingViewForRide,
  getDriverTotalPayoutDollars,
} from './ridePricingDisplay.js'
import { getIdempotencyKey, clearIdempotencyKey } from './idempotencyKeys.js'
import { resilientFetch } from './resilientFetch.js'

const RETRYABLE_HTTP_STATUSES = new Set([502, 503, 504])

function resolveApiBase() {
  if (typeof sessionStorage !== 'undefined') {
    const override = sessionStorage.getItem('halfapp_api_base_override')
    if (override) return override
  }
  return import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'
}

const API_BASE = resolveApiBase()
const IS_PRODUCTION_BUILD = import.meta.env.PROD
/** Dev-only: fall back to localStorage mock data when the API errors. Production always fails closed. */
const ALLOW_OFFLINE_MOCK = !IS_PRODUCTION_BUILD && import.meta.env.VITE_ALLOW_OFFLINE_MOCK === 'true'
/** Dev-only: shows explicit backend-simulation controls for driver-only MVP testing, never production truth. */
const ALLOW_RIDE_SIMULATION = !IS_PRODUCTION_BUILD && import.meta.env.VITE_ENABLE_RIDE_SIMULATION === 'true'
const MARKETPLACE_TRUTH_SOURCE = 'backend-owned'

function buildMockSimulationCoordinates() {
  const baseLat = 45.523064
  const baseLng = -122.676483
  const jitter = () => (Math.random() * 0.06) - 0.03
  return {
    pickup_latitude: Number((baseLat + jitter()).toFixed(6)),
    pickup_longitude: Number((baseLng + jitter()).toFixed(6)),
    dropoff_latitude: Number((baseLat + jitter()).toFixed(6)),
    dropoff_longitude: Number((baseLng + jitter()).toFixed(6)),
  }
}

class DriverAPI {
  constructor() {
    this.token = localStorage.getItem('driver_token')
  }

  getBaseUrl() {
    return resolveApiBase()
  }

  // Driver database persistence (localStorage) — used only by ALLOW_OFFLINE_MOCK code paths
  getDriverDatabase() {
    try {
      const drivers = localStorage.getItem('halfapp_driver_database')
      return drivers ? JSON.parse(drivers) : {}
    } catch (e) {
      console.error('Error reading driver database:', e)
      return {}
    }
  }

  setDriverDatabase(drivers) {
    try {
      localStorage.setItem('halfapp_driver_database', JSON.stringify(drivers))
    } catch (e) {
      console.error('Error saving driver database:', e)
    }
  }

  getMockDriverAppSettings() {
    const defaults = {
      units: 'mi',
      locale: 'en-US',
      theme: 'system',
      notif_push_enabled: false,
      notif_sound_enabled: true,
      notif_quiet_hours: null,
    }
    try {
      const raw = localStorage.getItem('halfapp_mock_driver_app_settings')
      return raw ? { ...defaults, ...JSON.parse(raw) } : defaults
    } catch {
      return defaults
    }
  }

  setMockDriverAppSettings(settings) {
    try {
      localStorage.setItem('halfapp_mock_driver_app_settings', JSON.stringify(settings))
    } catch (e) {
      console.error('Error saving mock app settings:', e)
    }
  }

  getMockDriverMeProfile() {
    const defaults = {
      display_name: null,
      phone_e164: null,
      photo_url: null,
    }
    try {
      const raw = localStorage.getItem('halfapp_mock_driver_me_profile')
      return raw ? { ...defaults, ...JSON.parse(raw) } : defaults
    } catch {
      return defaults
    }
  }

  setMockDriverMeProfile(profile) {
    try {
      localStorage.setItem('halfapp_mock_driver_me_profile', JSON.stringify(profile))
    } catch (e) {
      console.error('Error saving mock me profile:', e)
    }
  }

  getMockRideDatabase() {
    try {
      const rides = localStorage.getItem('halfapp_mock_backend_rides')
      return rides ? JSON.parse(rides) : []
    } catch (e) {
      console.error('Error reading mock ride database:', e)
      return []
    }
  }

  setMockRideDatabase(rides) {
    try {
      localStorage.setItem('halfapp_mock_backend_rides', JSON.stringify(rides))
    } catch (e) {
      console.error('Error saving mock ride database:', e)
    }
  }

  driverExists(email) {
    const drivers = this.getDriverDatabase()
    return !!drivers[email]
  }

  getHeaders() {
    this.token = localStorage.getItem('driver_token')
    const headers = {
      'Content-Type': 'application/json'
    }

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    return headers
  }

  static formatErrorDetail(detail) {
    if (typeof detail === 'string') return detail
    if (detail && typeof detail === 'object') {
      if (typeof detail.detail === 'string') return detail.detail
      if (detail.message) return detail.message
      if (detail.error) return typeof detail.error === 'string' ? detail.error : JSON.stringify(detail)
    }
    return JSON.stringify(detail || {})
  }

  _persistAuthTokens(data) {
    if (data?.access_token) {
      this.token = data.access_token
      localStorage.setItem('driver_token', data.access_token)
    }
    if (data?.refresh_token) {
      localStorage.setItem('driver_refresh_token', data.refresh_token)
    }
  }

  async _tryRefreshOnce() {
    const refreshToken = localStorage.getItem('driver_refresh_token')
    if (!refreshToken || this.token?.startsWith('mock_')) {
      return false
    }

    const url = `${this.getBaseUrl()}/auth/refresh`
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: AbortSignal.timeout(Number(import.meta.env.VITE_API_TIMEOUT_MS) || 8_000),
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
      if (!response.ok) {
        return false
      }
      const data = await response.json()
      this._persistAuthTokens(data)
      return true
    } catch {
      return false
    }
  }

  // Generic API call method
  async call(endpoint, options = {}, isRetry = false) {
    const url = `${this.getBaseUrl()}${endpoint}`

    const config = {
      headers: this.getHeaders(),
      signal: AbortSignal.timeout(Number(import.meta.env.VITE_API_TIMEOUT_MS) || 8_000),
      ...options
    }

    try {
      const response = await fetch(url, config)

      if (
        response.status === 401 &&
        !isRetry &&
        !endpoint.startsWith('/auth/')
      ) {
        const refreshed = await this._tryRefreshOnce()
        if (refreshed) {
          return this.call(endpoint, options, true)
        }
      }

      if (!response.ok) {
        let errorBody = {}
        try {
          errorBody = await response.json()
        } catch {
          errorBody = {}
        }
        const detail = errorBody.detail
        const message =
          DriverAPI.formatErrorDetail(detail) || `HTTP ${response.status}`
        const error = new Error(message)
        error.status = response.status
        error.detail = detail
        throw error
      }

      return await response.json()
    } catch (error) {
      console.error(`API call failed: ${endpoint}`, error)
      throw error
    }
  }

  /**
   * Ride lifecycle POST with Idempotency-Key + resilientFetch (Slice 03).
   * Does not replace generic GET `call()` — no global GET retry blast radius.
   */
  async callRideWrite(endpoint, options = {}, rideMeta = {}, isRetry = false) {
    const { rideId, action } = rideMeta
    if (
      ALLOW_OFFLINE_MOCK &&
      typeof localStorage !== 'undefined' &&
      localStorage.getItem('driver_token')?.startsWith('mock_')
    ) {
      const mockBody =
        typeof options.body === 'string' && options.body
          ? JSON.parse(options.body)
          : options.body || {}
      const data = this.getMockResponse(endpoint, options.method || 'POST', mockBody)
      clearIdempotencyKey(rideId, action)
      return data
    }

    const url = `${this.getBaseUrl()}${endpoint}`
    const idempotencyKey = getIdempotencyKey(rideId, action)
    const headers = {
      ...this.getHeaders(),
      ...(options.headers || {}),
      'Idempotency-Key': idempotencyKey,
    }
    const config = {
      signal: AbortSignal.timeout(Number(import.meta.env.VITE_API_TIMEOUT_MS) || 8_000),
      ...options,
      headers,
    }

    try {
      let response = await resilientFetch(url, config, { methodRetryAllowlist: ['POST'] })

      if (
        response.status === 401 &&
        !isRetry &&
        !endpoint.startsWith('/auth/')
      ) {
        const refreshed = await this._tryRefreshOnce()
        if (refreshed) {
          return this.callRideWrite(endpoint, options, rideMeta, true)
        }
      }

      if (!response.ok) {
        let errorBody = {}
        try {
          errorBody = await response.json()
        } catch {
          errorBody = {}
        }
        const detail = errorBody.detail
        const message =
          DriverAPI.formatErrorDetail(detail) || `HTTP ${response.status}`
        const error = new Error(message)
        error.status = response.status
        error.detail = detail
        error.retryableWrite = RETRYABLE_HTTP_STATUSES.has(response.status)
        throw error
      }

      const data = await response.json()
      clearIdempotencyKey(rideId, action)
      return data
    } catch (error) {
      if (error?.retryableWrite == null) {
        error.retryableWrite = !error?.status
      }
      console.error(`Ride write failed: ${endpoint}`, error)
      throw error
    }
  }

  getMockResponse(endpoint, method = 'POST', body = {}) {
    let mockDrivers = this.getDriverDatabase()

    if (Object.keys(mockDrivers).length === 0) {
      mockDrivers = {
        'driver1@example.com': {
          id: 1,
          email: 'driver1@example.com',
          name: 'John Driver',
          role: 'driver',
          license_no: 'DL12345',
          vehicle_make: 'Toyota',
          vehicle_model: 'Prius',
          license_plate: 'BETA-001',
          insurance_policy: 'BETA-POLICY-001',
          insurance_expires_at: '2027-05-25T00:00:00Z',
          vehicle_ready: true,
          approval_status: 'approved',
          availability: 'offline',
          password: 'driver123',
          createdAt: new Date().toISOString()
        },
        'driver2@example.com': {
          id: 2,
          email: 'driver2@example.com',
          name: 'Jane Driver',
          role: 'driver',
          license_no: 'DL67890',
          vehicle_make: 'Honda',
          vehicle_model: 'Civic',
          license_plate: 'BETA-002',
          insurance_policy: 'BETA-POLICY-002',
          insurance_expires_at: '2027-05-25T00:00:00Z',
          vehicle_ready: true,
          approval_status: 'approved',
          availability: 'offline',
          password: 'driver456',
          createdAt: new Date().toISOString()
        }
      }
      this.setDriverDatabase(mockDrivers)
    }

    const mockAdmins = {
      'admin@example.com': {
        id: 101,
        email: 'admin@example.com',
        name: 'System Admin',
        role: 'admin',
        password: 'admin123'
      }
    }

    const mockCustomers = {
      'customer@example.com': {
        id: 201,
        email: 'customer@example.com',
        name: 'Test Customer',
        role: 'customer',
        password: 'customer123'
      }
    }

    if (endpoint === '/auth/login' && method === 'POST') {
      const { email, password } = body
      const driver = mockDrivers[email]

      if (driver && driver.password === password) {
        return {
          access_token: `mock_driver_token_${driver.id}`,
          token_type: 'bearer',
          role: 'driver',
          user: {
            id: driver.id,
            email: driver.email,
            name: driver.name,
            role: driver.role,
            license_no: driver.license_no,
            availability: driver.availability || 'offline',
          }
        }
      }

      if (mockAdmins[email] && mockAdmins[email].password === password) {
        throw new Error('Admin access not allowed in driver app. Please use the admin portal.')
      }

      if (mockCustomers[email] && mockCustomers[email].password === password) {
        throw new Error('Customer access not allowed in driver app. Please use the customer app.')
      }

      throw new Error('Invalid driver credentials or account not found')
    }

    if (endpoint === '/auth/register' && method === 'POST') {
      const { email, name, password, license_no } = body

      if (mockDrivers[email]) {
        throw new Error('A driver account with this email already exists. Please sign in instead.')
      }

      if (mockAdmins[email]) {
        throw new Error('This email is registered as an admin. Please use a different email for your driver account.')
      }

      if (mockCustomers[email]) {
        throw new Error('This email is registered as a customer. Please use a different email for your driver account.')
      }

      const newDriver = {
        id: Date.now(),
        email,
        name,
        role: 'driver',
        license_no: license_no || `DL${Date.now()}`,
        availability: 'offline',
        password,
        createdAt: new Date().toISOString()
      }

      mockDrivers[email] = newDriver
      this.setDriverDatabase(mockDrivers)

      return {
        access_token: `mock_driver_token_${newDriver.id}`,
        token_type: 'bearer',
        role: 'driver',
        user: {
          id: newDriver.id,
          email: newDriver.email,
          name: newDriver.name,
          role: newDriver.role,
          license_no: newDriver.license_no,
          availability: newDriver.availability,
        }
      }
    }

    if (endpoint === '/auth/me') {
      const token =
        typeof localStorage !== 'undefined' ? localStorage.getItem('driver_token') : null
      const match = token && /^mock_driver_token_(\d+)$/.exec(token)
      if (match) {
        const id = match[1]
        const byId = Object.values(mockDrivers).find((d) => String(d.id) === id)
        if (byId) {
          return {
            id: byId.id,
            email: byId.email,
            name: byId.name,
            role: 'driver',
            license_no: byId.license_no,
            availability: byId.availability || 'offline',
          }
        }
      }
      const currentDriver = Object.values(mockDrivers)[0]
      return (
        currentDriver || {
          id: 1,
          email: 'driver1@example.com',
          name: 'John Driver',
          role: 'driver',
          license_no: 'DL12345',
          availability: 'offline',
        }
      )
    }

    if (endpoint === '/drivers/profile' && method === 'GET') {
      const token =
        typeof localStorage !== 'undefined' ? localStorage.getItem('driver_token') : null
      const match = token && /^mock_driver_token_(\d+)$/.exec(token)
      const driver = match
        ? Object.values(mockDrivers).find((item) => String(item.id) === match[1])
        : Object.values(mockDrivers)[0]
      if (!driver) throw new Error('Mock driver not found')
      const { password: _password, ...rest } = driver
      return {
        id: rest.id,
        email: rest.email,
        name: rest.name,
        role: rest.role || 'driver',
        approval_status: rest.approval_status || 'pending',
        license_no: rest.license_no || null,
        vehicle: {
          make: rest.vehicle_make || 'Not registered',
          model: rest.vehicle_model || 'Not registered',
          plate: rest.license_plate || 'Not registered',
        },
        vehicle_ready: rest.vehicle_ready === true,
        insurance_policy: rest.insurance_policy || null,
        insurance_expires_at: rest.insurance_expires_at || null,
        read_only: true,
      }
    }

    if (endpoint === '/drivers/profile' && method === 'PUT') {
      const token =
        typeof localStorage !== 'undefined' ? localStorage.getItem('driver_token') : null
      const match = token && /^mock_driver_token_(\d+)$/.exec(token)
      const driver = match
        ? Object.values(mockDrivers).find((item) => String(item.id) === match[1])
        : Object.values(mockDrivers)[0]
      if (!driver) throw new Error('Mock driver not found')
      Object.assign(driver, body)
      this.setDriverDatabase(mockDrivers)
      const { password: _password, ...profile } = driver
      return {
        message: 'Profile updated',
        profile: {
          ...profile,
          availability: profile.availability || 'offline',
        },
      }
    }

    if (endpoint === '/drivers/presence' && method === 'GET') {
      const currentDriver = Object.values(mockDrivers)[0] || { id: 1, availability: 'offline' }
      return {
        driver_id: currentDriver.id,
        requested_state: currentDriver.availability || 'offline',
        effective_state: currentDriver.availability || 'offline',
        state: currentDriver.availability || 'offline',
        state_changed_at: new Date().toISOString(),
        heartbeat_at: currentDriver.heartbeat_at || null,
        stale_reason: null,
        updated_at: new Date().toISOString(),
      }
    }

    if (endpoint === '/drivers/presence' && method === 'PUT') {
      const currentDriver = Object.values(mockDrivers)[0] || { id: 1, availability: 'offline' }
      currentDriver.availability = body.state === 'available' ? 'available' : 'offline'
      currentDriver.heartbeat_at = body.state === 'available' ? new Date().toISOString() : currentDriver.heartbeat_at
      mockDrivers[currentDriver.email || 'driver1@example.com'] = currentDriver
      this.setDriverDatabase(mockDrivers)
      return {
        driver_id: currentDriver.id,
        requested_state: currentDriver.availability,
        effective_state: currentDriver.availability,
        state: currentDriver.availability,
        state_changed_at: new Date().toISOString(),
        heartbeat_at: currentDriver.heartbeat_at || null,
        stale_reason: null,
        updated_at: new Date().toISOString(),
      }
    }

    if (endpoint === '/drivers/heartbeat' && method === 'POST') {
      const currentDriver = Object.values(mockDrivers)[0] || { id: 1, availability: 'available' }
      currentDriver.availability = currentDriver.availability || 'available'
      currentDriver.heartbeat_at = new Date().toISOString()
      mockDrivers[currentDriver.email || 'driver1@example.com'] = currentDriver
      this.setDriverDatabase(mockDrivers)
      return {
        driver_id: currentDriver.id,
        requested_state: currentDriver.availability,
        effective_state: currentDriver.availability,
        state: currentDriver.availability,
        state_changed_at: new Date().toISOString(),
        heartbeat_at: currentDriver.heartbeat_at,
        stale_reason: null,
        updated_at: new Date().toISOString(),
      }
    }

    if (endpoint === '/drivers/simulate-ride' && method === 'POST') {
      const rides = this.getMockRideDatabase()
      const id = Date.now()
      const coords = buildMockSimulationCoordinates()
      const ride = {
        id,
        pickup_location: body.pickup_location || 'Simulation Pickup',
        destination: body.destination || 'Simulation Destination',
        pickup_latitude: body.pickup_latitude ?? coords.pickup_latitude,
        pickup_longitude: body.pickup_longitude ?? coords.pickup_longitude,
        dropoff_latitude: body.dropoff_latitude ?? coords.dropoff_latitude,
        dropoff_longitude: body.dropoff_longitude ?? coords.dropoff_longitude,
        customer_name: body.customer_name || 'Simulation Rider',
        fare_amount: 0,
        distance_km: body.distance_km ?? 4,
        duration_minutes: body.duration_minutes ?? 12,
        status: 'requested',
        created_at: new Date().toISOString(),
        accepted_at: null,
        arrived_pickup_at: null,
        started_at: null,
        completed_at: null,
        cancelled_at: null,
        lifecycle_reason: 'simulation',
        pricing: buildMockPricingViewForRide(
          {
            distance_km: body.distance_km ?? 4,
            duration_minutes: body.duration_minutes ?? 12,
          },
          { lock: false }
        ),
      }
      rides.push(ride)
      this.setMockRideDatabase(rides)
      return { message: `Simulation ride ${id} created`, ride }
    }

    const transparencyMatch = endpoint.match(/^\/drivers\/rides\/(\d+)\/transparency$/)
    const paymentMatch = endpoint.match(/^\/drivers\/rides\/(\d+)\/payment$/)
    if (paymentMatch && method === 'GET') {
      const rideId = Number(paymentMatch[1])
      const rides = this.getMockRideDatabase()
      const ride = rides.find((item) => Number(item.id) === rideId)
      if (!ride) throw new Error('Ride not found')
      const pricing = ride.pricing || buildMockPricingViewForRide(ride, { lock: ride.status === 'completed' })
      const gross = pricing.customer_total_cents || 925
      const driverPayout = pricing.driver_ride_payout_cents || Math.round(gross * 0.72)
      return {
        message: 'Ride payment',
        payment: {
          id: rideId,
          ride_id: rideId,
          rider_id: ride.customer_id || null,
          driver_id: ride.driver_id || 1,
          amount_cents: gross,
          driver_payout_cents: driverPayout,
          currency: 'USD',
          status: ride.status === 'completed' ? 'captured' : ride.status === 'cancelled' ? 'failed' : 'authorized',
          created_at: ride.created_at,
          authorized_at: ride.accepted_at,
          captured_at: ride.completed_at,
          failed_at: ride.cancelled_at,
        },
      }
    }
    if (transparencyMatch && method === 'GET') {
      const rideId = Number(transparencyMatch[1])
      const rides = this.getMockRideDatabase()
      const ride = rides.find((item) => Number(item.id) === rideId)
      if (!ride) throw new Error('Ride not found')
      return {
        ride_id: String(rideId),
        driver_id: '1',
        visibility: {
          visible: true,
          visible_at: new Date().toISOString(),
          visibility_record_id: `mock-${rideId}`,
          source: ride.lifecycle_reason === 'simulation' ? 'simulation' : 'open_board',
          policy_id: 'ranked_open_board_v1',
          policy_name: 'Ranked Open Board v1',
          policy_version: 'ranked_open_board_v1',
          reason_codes: ['requested_unassigned_open_board'],
        },
        claim: {
          claimable: ride.status === 'requested' && !ride.driver_id,
          current_status: ride.status,
          claimed_by_driver_id: ride.driver_id ? String(ride.driver_id) : null,
          last_claim_attempt_id: null,
          last_claim_result: 'none',
        },
        dismissal: {
          hidden_for_this_driver: !!ride.dismissed_at,
          hidden_at: ride.dismissed_at || null,
          expires_at: null,
          reason: ride.dismissal_reason || null,
        },
        audit: {
          ledger_event_ids: [],
          correlation_id: `mock-correlation-${rideId}`,
          idempotency_key: null,
        },
        truth_labels: ['BACKEND_OWNED', 'DISPATCH_BACKEND_OWNED', 'NO_ETA_GUARANTEE', 'NO_ROUTE_SNAPSHOT'],
      }
    }

    if (endpoint === '/drivers/available-rides') {
      return this.getMockRideDatabase().filter(
        (ride) => ride.status === 'requested' && !ride.driver_id && !ride.dismissed_at
      )
    }

    if (endpoint === '/drivers/my-rides') {
      return this.getMockRideDatabase().filter((ride) => ride.driver_id)
    }

    const hideMatch = endpoint.match(/^\/drivers\/rides\/(\d+)\/hide$/)
    if (hideMatch && method === 'POST') {
      const rideId = Number(hideMatch[1])
      const rides = this.getMockRideDatabase()
      const ride = rides.find((item) => Number(item.id) === rideId)
      if (!ride) throw new Error('Ride not found')
      if (ride.status !== 'requested' || ride.driver_id) throw new Error('Ride cannot be hidden in its current state')
      ride.dismissed_at = new Date().toISOString()
      ride.dismissal_reason = body.reason || null
      this.setMockRideDatabase(rides)
      return { message: `Ride ${rideId} hidden`, ride }
    }

    const transitionMatch = endpoint.match(
      /^\/drivers\/(accept-ride|decline-ride|dismiss-ride|arrive-pickup|start-ride|complete-ride)\/(\d+)$/
    )
    if (transitionMatch && method === 'POST') {
      const [, action, idRaw] = transitionMatch
      const rideId = Number(idRaw)
      const rides = this.getMockRideDatabase()
      const ride = rides.find((item) => Number(item.id) === rideId)
      if (!ride) throw new Error('Ride not found')

      if (action === 'accept-ride') {
        if (ride.driver_id) {
          const error = new Error('Ride already claimed')
          error.status = 409
          error.detail = {
            detail: 'Ride already claimed',
            ride_id: rideId,
            claim_result: 'lost',
            truth_status: 'backend_conflict',
          }
          throw error
        }
        if (ride.status !== 'requested') throw new Error('Ride not available')
        ride.driver_id = 1
        ride.status = 'accepted'
        ride.accepted_at = new Date().toISOString()
      } else if (action === 'decline-ride') {
        ride.driver_id = null
        ride.status = 'requested'
        ride.accepted_at = null
        ride.arrived_pickup_at = null
        ride.started_at = null
        ride.lifecycle_reason = body.reason || null
      } else if (action === 'dismiss-ride') {
        if (ride.status !== 'requested' || ride.driver_id) throw new Error('Ride cannot be dismissed in its current state')
        ride.dismissed_at = new Date().toISOString()
      } else if (action === 'arrive-pickup') {
        if (ride.status !== 'accepted') throw new Error('Cannot mark arrival in the current ride state')
        ride.status = 'driver_arrived'
        ride.arrived_pickup_at = new Date().toISOString()
      } else if (action === 'start-ride') {
        if (ride.status !== 'driver_arrived') throw new Error('Ride cannot be started in its current state')
        ride.status = 'in_progress'
        ride.started_at = new Date().toISOString()
      } else if (action === 'complete-ride') {
        if (ride.status !== 'in_progress') throw new Error('Ride is not in progress')
        ride.status = 'completed'
        ride.completed_at = new Date().toISOString()
        ride.pricing = buildMockPricingViewForRide(ride)
        const driverDollars = getDriverTotalPayoutDollars(ride)
        ride.fare_amount = driverDollars ?? 0
      }

      this.setMockRideDatabase(rides)
      if (action === 'complete-ride') {
        return {
          message: `Ride ${rideId} completed successfully`,
          fare_earned: ride.fare_amount,
          ride,
        }
      }
      return { message: `Ride ${rideId} updated`, ride }
    }

    if (endpoint === '/drivers/me/payment-reconciliation') {
      return {
        driver_id: 1,
        pricing_earned_cents: 0,
        collected_cents: 0,
        pending_cents: 0,
        refunded_cents: 0,
        disputed_cents: 0,
        available_cents: 0,
        execution_collected_cents: 0,
        execution_refunded_cents: 0,
        execution_disputed_cents: 0,
        execution_pending_collection_cents: 0,
        execution_refundable_cents: 0,
        display_note:
          'Shows processed and pending payment execution amounts from the provider. Not a bank deposit or payout guarantee.',
        payout_paid_cents: 0,
        payout_pending_cents: 0,
        payout_failed_cents: 0,
        payout_last_status: null,
        payout_last_at: null,
        provider_payout_visible: false,
        truth_labels: ['pricing_earned_is_obligation_not_payout'],
      }
    }

    if (endpoint === '/drivers/me/payment-executions') {
      return { items: [] }
    }

    if (endpoint === '/drivers/me/payouts') {
      return { items: [] }
    }

    if (endpoint === '/drivers/stripe/connect/status') {
      return {
        payments_enabled: false,
        payouts_enabled_flag: false,
        has_connect_account: false,
        stripe_account_id: null,
        charges_enabled: false,
        provider_payouts_enabled: false,
      }
    }

    if (endpoint === '/drivers/me/settings' && method === 'GET') {
      return this.getMockDriverAppSettings()
    }

    if (endpoint === '/drivers/me/settings' && method === 'PUT') {
      const current = this.getMockDriverAppSettings()
      const next = { ...current, ...body }
      this.setMockDriverAppSettings(next)
      return next
    }

    if (endpoint === '/drivers/me/profile' && method === 'GET') {
      return this.getMockDriverMeProfile()
    }

    if (endpoint === '/drivers/me/profile' && method === 'PUT') {
      const current = this.getMockDriverMeProfile()
      const next = { ...current, ...body }
      this.setMockDriverMeProfile(next)
      return next
    }

    if (endpoint === '/drivers/earnings') {
      const completed = this.getMockRideDatabase().filter((ride) => ride.status === 'completed')
      const total = completed.reduce(
        (sum, ride) => sum + (getDriverTotalPayoutDollars(ride) ?? Number(ride.fare_amount || 0)),
        0
      )
      return {
        driver_id: 1,
        driver_name: 'Mock Driver',
        earnings_summary: {
          total_earnings: Number(total.toFixed(2)),
          weekly_earnings: Number(total.toFixed(2)),
          today_earnings: Number(total.toFixed(2)),
          total_rides_completed: completed.length,
          weekly_rides: completed.length,
          today_rides: completed.length,
        },
        recent_rides: completed.slice(-10).reverse(),
      }
    }

    if (endpoint === '/drivers/statistics') {
      return { performance_stats: {} }
    }

    if (endpoint === '/drivers/insights') {
      return {
        driver_id: 1,
        generated_at: new Date().toISOString(),
        insights: [
          {
            type: 'insufficient_mock_data',
            status: 'insufficient_data',
            message: 'Measured driver insights require backend metrics.',
            evidence: {}
          }
        ]
      }
    }

    return { message: 'Mock response', success: true }
  }

  async login(email, password) {
    try {
      const response = await this.call('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      })

      if (response.role !== 'driver') {
        throw new Error(`Access denied: This is a driver app. ${response.role}s cannot login here.`)
      }

      this._persistAuthTokens(response)
      localStorage.setItem('driver_role', response.role)

      if (!response.user) {
        const me = await this.call('/auth/me')
        return { ...response, user: me }
      }

      return response
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) {
        throw error
      }
      console.warn('Backend unavailable — mock login (VITE_ALLOW_OFFLINE_MOCK=true)', error.message)
      const mockResponse = this.getMockResponse('/auth/login', 'POST', { email, password })
      if (mockResponse.role !== 'driver') {
        throw new Error('Access denied: This is a driver app. Only drivers can login here.')
      }
      this._persistAuthTokens(mockResponse)
      localStorage.setItem('driver_role', mockResponse.role)
      return mockResponse
    }
  }

  async register(userData) {
    if (!userData.email || !userData.name || !userData.password) {
      throw new Error('Email, name, and password are required for driver registration')
    }
    if (!userData.license_no || String(userData.license_no).trim().length < 5) {
      throw new Error("Driver's license number is required (at least 5 characters)")
    }

    try {
      const payload = {
        email: userData.email,
        name: userData.name,
        password: userData.password,
        role: 'driver',
        license_no: String(userData.license_no).trim()
      }

      const response = await this.call('/auth/register', {
        method: 'POST',
        body: JSON.stringify(payload)
      })

      if (response.role !== 'driver') {
        throw new Error('Registration failed: Only driver accounts can be created in this app')
      }

      this._persistAuthTokens(response)
      localStorage.setItem('driver_role', response.role)

      if (!response.user) {
        const me = await this.call('/auth/me')
        return { ...response, user: me }
      }

      return response
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) {
        throw error
      }
      console.warn('Backend unavailable — mock register (VITE_ALLOW_OFFLINE_MOCK=true)', error.message)
      const mockResponse = this.getMockResponse('/auth/register', 'POST', userData)
      this._persistAuthTokens(mockResponse)
      localStorage.setItem('driver_role', mockResponse.role)
      return mockResponse
    }
  }

  async getProfile() {
    try {
      return await this.call('/auth/me')
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) {
        throw error
      }
      return this.getMockResponse('/auth/me')
    }
  }

  async getDriverSettingsProfile() {
    try {
      return await this.call('/drivers/profile')
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) {
        throw error
      }
      return this.getMockResponse('/drivers/profile', 'GET')
    }
  }

  async getAvailableRides() {
    try {
      return await this.call('/drivers/available-rides')
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) {
        throw error
      }
      return this.getMockResponse('/drivers/available-rides')
    }
  }

  /**
   * SSE subscription for ride pool deltas (v0.1). Delegates to sseClient.
   * Returns `{ close }` — call close() on unmount.
   */
  subscribeAvailableRidesStream({ onSnapshot, onDelta, onError, onOpen } = {}) {
    const token = localStorage.getItem('driver_token')
    if (!token || token.startsWith('mock_')) {
      onError?.(new Error('sse_unavailable'))
      return { close: () => {} }
    }

    let opened = false
    const close = subscribeRidePool(token, {
      apiBase: this.getBaseUrl(),
      onSnapshot: (rides) => {
        if (!opened) {
          opened = true
          onOpen?.()
        }
        onSnapshot?.(rides)
      },
      onDelta: (event) => {
        if (!opened) {
          opened = true
          onOpen?.()
        }
        onDelta?.(event)
      },
      onError,
    })

    return { close }
  }

  async getActiveRide() {
    try {
      return await this.call('/drivers/me/active-ride')
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) {
        throw error
      }
      const rides = this.getMockRideDatabase()
      const active = rides.find(
        (r) =>
          r.driver_id === 1 &&
          ['accepted', 'driver_arrived', 'in_progress'].includes(r.status)
      )
      if (!active) {
        return { ride: null, lifecycle_stage: null, navigation: null }
      }
      return {
        ride: active,
        lifecycle_stage: active.status,
        navigation: null,
      }
    }
  }

  async getPresence() {
    try {
      return await this.call('/drivers/presence')
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) throw error
      return this.getMockResponse('/drivers/presence', 'GET')
    }
  }

  async updatePresence(state) {
    if (!['available', 'offline', 'paused'].includes(state)) {
      throw new Error("presence state must be 'available', 'offline', or 'paused'")
    }
    try {
      return await this.call('/drivers/presence', {
        method: 'PUT',
        body: JSON.stringify({ state }),
      })
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) throw error
      return this.getMockResponse('/drivers/presence', 'PUT', { state })
    }
  }

  async sendHeartbeat() {
    try {
      return await this.call('/drivers/heartbeat', {
        method: 'POST',
      })
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) throw error
      return this.getMockResponse('/drivers/heartbeat', 'POST', {})
    }
  }

  async getMyRides(params = {}) {
    const qs = new URLSearchParams()
    if (params.status) qs.set('status', params.status)
    if (params.from_date) qs.set('from_date', params.from_date)
    if (params.to_date) qs.set('to_date', params.to_date)
    if (params.q) qs.set('q', params.q)
    const suffix = qs.toString() ? `?${qs.toString()}` : ''
    try {
      return await this.call(`/drivers/my-rides${suffix}`)
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) {
        throw error
      }
      return this.getMockResponse('/drivers/my-rides')
    }
  }

  async getDriverTrips(params = {}) {
    const qs = new URLSearchParams()
    if (params.status) qs.set('status', params.status)
    if (params.from_date) qs.set('from_date', params.from_date)
    if (params.to_date) qs.set('to_date', params.to_date)
    if (params.q) qs.set('q', params.q)
    if (params.limit != null) qs.set('limit', String(params.limit))
    if (params.offset != null) qs.set('offset', String(params.offset))
    const suffix = qs.toString() ? `?${qs.toString()}` : ''
    try {
      return await this.call(`/drivers/me/trips${suffix}`)
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) {
        throw error
      }
      const rides = await this.getMockResponse('/drivers/my-rides')
      const list = Array.isArray(rides) ? rides : []
      return { items: list, total: list.length, limit: params.limit ?? 50, offset: params.offset ?? 0 }
    }
  }

  async exportMyRidesCsv(params = {}) {
    const qs = new URLSearchParams()
    if (params.status) qs.set('status', params.status)
    if (params.from_date) qs.set('from_date', params.from_date)
    if (params.to_date) qs.set('to_date', params.to_date)
    if (params.q) qs.set('q', params.q)
    const suffix = qs.toString() ? `?${qs.toString()}` : ''
    const token = localStorage.getItem('driver_token')
    const response = await fetch(`${this.getBaseUrl()}/drivers/me/trips/export.csv${suffix}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!response.ok) {
      throw new Error(`Export failed (${response.status})`)
    }
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'halfapp_trips.csv'
    anchor.click()
    URL.revokeObjectURL(url)
  }

  async forgotPassword(email) {
    return await this.call('/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email }),
    })
  }

  async resetPassword(token, newPassword) {
    return await this.call('/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({ token, new_password: newPassword }),
    })
  }

  async changePassword(currentPassword, newPassword) {
    return await this.call('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    })
  }

  async getRideMessages(rideId) {
    return await this.call(`/drivers/rides/${rideId}/messages`)
  }

  async sendRideMessage(rideId, body) {
    return await this.call(`/drivers/rides/${rideId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ body }),
    })
  }

  async getRideNavigation(rideId) {
    return await this.call(`/drivers/rides/${rideId}/navigation`)
  }

  async reportRideIssue(rideId, message, category = 'trip_issue') {
    return await this.call(`/drivers/rides/${rideId}/support-ticket`, {
      method: 'POST',
      body: JSON.stringify({ message, category }),
    })
  }

  async acceptRide(rideId) {
    const endpoint = `/drivers/accept-ride/${rideId}`
    try {
      return await this.callRideWrite(endpoint, { method: 'POST' }, { rideId, action: 'accept' })
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK || error.status === 409) throw error
      return this.getMockResponse(endpoint, 'POST', {})
    }
  }

  async getRideTransparency(rideId) {
    const endpoint = `/drivers/rides/${rideId}/transparency`
    try {
      return await this.call(endpoint)
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) throw error
      return this.getMockResponse(endpoint, 'GET')
    }
  }

  async getRideAudit(rideId) {
    const endpoint = `/drivers/rides/${rideId}/audit`
    return await this.call(endpoint)
  }

  async getRideRouteSnapshots(rideId) {
    const endpoint = `/drivers/rides/${rideId}/route-snapshots`
    return await this.call(endpoint)
  }

  async declineDispatchOffer(rideId) {
    const endpoint = `/drivers/decline-dispatch/${rideId}`
    try {
      return await this.callRideWrite(endpoint, { method: 'POST' }, { rideId, action: 'decline_dispatch' })
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) throw error
      return this.getMockResponse(endpoint, 'POST', {})
    }
  }

  async declineRide(rideId, body = {}) {
    const endpoint = `/drivers/decline-ride/${rideId}`
    try {
      return await this.callRideWrite(
        endpoint,
        { method: 'POST', body: JSON.stringify(body) },
        { rideId, action: 'decline' }
      )
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) throw error
      return this.getMockResponse(endpoint, 'POST', body)
    }
  }

  async dismissRide(rideId) {
    return this.hideRide(rideId)
  }

  async hideRide(rideId, body = {}) {
    const endpoint = `/drivers/rides/${rideId}/hide`
    try {
      return await this.callRideWrite(
        endpoint,
        { method: 'POST', body: JSON.stringify(body) },
        { rideId, action: 'hide' }
      )
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) throw error
      return this.getMockResponse(endpoint, 'POST', body)
    }
  }

  async arrivePickup(rideId) {
    const endpoint = `/drivers/arrive-pickup/${rideId}`
    try {
      return await this.callRideWrite(endpoint, { method: 'POST' }, { rideId, action: 'arrive' })
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) throw error
      return this.getMockResponse(endpoint, 'POST', {})
    }
  }

  async startRide(rideId) {
    const endpoint = `/drivers/start-ride/${rideId}`
    try {
      return await this.callRideWrite(endpoint, { method: 'POST' }, { rideId, action: 'start' })
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) throw error
      return this.getMockResponse(endpoint, 'POST', {})
    }
  }

  async completeRide(rideId, pricingBody = null) {
    const endpoint = `/drivers/complete-ride/${rideId}`
    try {
      return await this.callRideWrite(
        endpoint,
        {
          method: 'POST',
          body: pricingBody ? JSON.stringify(pricingBody) : undefined,
        },
        { rideId, action: 'complete' }
      )
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) throw error
      return this.getMockResponse(endpoint, 'POST', {})
    }
  }

  async getEarnings() {
    try {
      return await this.call('/drivers/earnings')
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) throw error
      return this.getMockResponse('/drivers/earnings')
    }
  }

  async getRidePayments() {
    return await this.call('/drivers/me/ride-payments')
  }

  async getRidePayment(rideId) {
    return await this.call(`/drivers/rides/${rideId}/payment`)
  }

  async getPaymentReconciliation() {
    return await this.call('/drivers/me/payment-reconciliation')
  }

  async getPaymentExecutions() {
    return await this.call('/drivers/me/payment-executions')
  }

  async getPayouts() {
    return await this.call('/drivers/me/payouts')
  }

  async getStripeConnectStatus() {
    return await this.call('/drivers/stripe/connect/status')
  }

  async getDriverAppSettings() {
    try {
      return await this.call('/drivers/me/settings')
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) throw error
      return this.getMockResponse('/drivers/me/settings', 'GET')
    }
  }

  async putDriverAppSettings(body) {
    try {
      return await this.call('/drivers/me/settings', {
        method: 'PUT',
        body: JSON.stringify(body),
      })
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) throw error
      return this.getMockResponse('/drivers/me/settings', 'PUT', body)
    }
  }

  async getDriverMeProfile() {
    try {
      return await this.call('/drivers/me/profile')
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) throw error
      return this.getMockResponse('/drivers/me/profile', 'GET')
    }
  }

  async putDriverMeProfile(body) {
    try {
      return await this.call('/drivers/me/profile', {
        method: 'PUT',
        body: JSON.stringify(body),
      })
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) throw error
      return this.getMockResponse('/drivers/me/profile', 'PUT', body)
    }
  }

  async createSimulationRide(rideData = {}) {
    try {
      return await this.call('/drivers/simulate-ride', {
        method: 'POST',
        body: JSON.stringify(rideData),
      })
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) throw error
      return this.getMockResponse('/drivers/simulate-ride', 'POST', rideData)
    }
  }

  async getStatistics() {
    try {
      return await this.call('/drivers/statistics')
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) {
        throw error
      }
      return this.getMockResponse('/drivers/statistics')
    }
  }

  async getInsights() {
    try {
      return await this.call('/drivers/insights')
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) {
        throw error
      }
      return this.getMockResponse('/drivers/insights')
    }
  }

  async updateLocation(latitude, longitude) {
    return await this.call('/drivers/update-location', {
      method: 'POST',
      body: JSON.stringify({ latitude, longitude })
    })
  }

  async updateProfile(profileData) {
    try {
      return await this.call('/drivers/profile', {
        method: 'PUT',
        body: JSON.stringify(profileData)
      })
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) throw error
      return this.getMockResponse('/drivers/profile', 'PUT', profileData)
    }
  }

  async getDriverMeStatus() {
    try {
      return await this.call('/drivers/me/status')
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) throw error
      const presence = await this.getMockResponse('/drivers/presence', 'GET')
      return {
        driver_id: presence?.driver_id,
        online: presence?.state === 'available',
        last_lat: null,
        last_lng: null,
        last_seen_at: presence?.heartbeat_at ?? null,
        current_ride_id: null,
        updated_at: presence?.updated_at ?? null,
      }
    }
  }

  async patchDriverMeStatus({ online, lat, lng }) {
    const body = { online }
    if (lat != null) body.lat = lat
    if (lng != null) body.lng = lng
    try {
      return await this.call('/drivers/me/status', {
        method: 'PATCH',
        body: JSON.stringify(body),
      })
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) throw error
      if (online) {
        return this.getMockResponse('/drivers/presence', 'PUT', { state: 'available' })
      }
      return this.getMockResponse('/drivers/presence', 'PUT', { state: 'offline' })
    }
  }

  async patchDriverMeLocation(lat, lng) {
    try {
      return await this.call('/drivers/me/location', {
        method: 'PATCH',
        body: JSON.stringify({ lat, lng }),
      })
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) throw error
      return this.updateLocation(lat, lng)
    }
  }

  async postDriverTelemetry({ lat, lng, speed_mps }) {
    const body = { lat, lng }
    if (speed_mps != null && Number.isFinite(speed_mps)) {
      body.speed_mps = speed_mps
    }
    return await this.call('/drivers/me/telemetry', {
      method: 'POST',
      body: JSON.stringify(body),
    })
  }

  async getSilMap({ bbox, layers = 'busy,slow', window = '30m', min_conf = 0.4 } = {}) {
    const qs = new URLSearchParams()
    if (bbox) qs.set('bbox', bbox)
    if (layers) qs.set('layers', layers)
    if (window) qs.set('window', window)
    if (min_conf != null) qs.set('min_conf', String(min_conf))
    const suffix = qs.toString() ? `?${qs.toString()}` : ''
    try {
      return await this.call(`/v1/sil/map${suffix}`)
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) throw error
      return { cells: [], not_enough_data_areas: [], disclaimer: '' }
    }
  }

  async getSilSuggest({ driver_lat, driver_lng, driver_h3, horizon = '15m' } = {}) {
    const qs = new URLSearchParams()
    if (driver_h3) qs.set('driver_h3', driver_h3)
    if (driver_lat != null) qs.set('driver_lat', String(driver_lat))
    if (driver_lng != null) qs.set('driver_lng', String(driver_lng))
    if (horizon) qs.set('horizon', horizon)
    const suffix = qs.toString() ? `?${qs.toString()}` : ''
    return await this.call(`/v1/sil/suggest${suffix}`)
  }

  async createSilRouteQuote({ from_lat, from_lng, to_lat, to_lng }) {
    return await this.call('/v1/sil/route/quote', {
      method: 'POST',
      body: JSON.stringify({ from_lat, from_lng, to_lat, to_lng, mode: 'driving' }),
    })
  }

  async getSilProofReceipt(receiptId) {
    return await this.call(`/v1/sil/proof/receipt/${receiptId}`)
  }

  async getCrlMap({ window = '30m', min_conf = 0.4 } = {}) {
    const qs = new URLSearchParams()
    if (window) qs.set('window', window)
    if (min_conf != null) qs.set('min_conf', String(min_conf))
    const suffix = qs.toString() ? `?${qs.toString()}` : ''
    try {
      const json = await this.call(`/v1/crl/map${suffix}`)
      const cells = (json?.cells || []).map((c) => ({
        ...c,
        confidence_band:
          c.confidence >= 0.66 ? 'high' : c.confidence >= 0.4 ? 'medium' : 'low',
      }))
      return { ...json, cells }
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) throw error
      return { cells: [], not_enough_data_label: 'Not enough recent activity to estimate patterns here.' }
    }
  }

  async getCrlExplain(h3) {
    return await this.call(`/v1/crl/explain?h3=${encodeURIComponent(h3)}`)
  }

  async getFleetTrafficHeatmap({ minutes = 10, precision = 0.002 } = {}) {
    const qs = new URLSearchParams()
    if (minutes != null) qs.set('minutes', String(minutes))
    if (precision != null) qs.set('precision', String(precision))
    const suffix = qs.toString() ? `?${qs.toString()}` : ''
    try {
      return await this.call(`/drivers/me/traffic-heatmap${suffix}`)
    } catch (error) {
      if (!ALLOW_OFFLINE_MOCK) throw error
      return { points: [], window_minutes: minutes }
    }
  }

  async updateAvailability(availability, coords = null) {
    if (availability === 'available') {
      const lat = coords?.lat ?? coords?.latitude
      const lng = coords?.lng ?? coords?.longitude
      if (lat != null && lng != null) {
        return await this.patchDriverMeStatus({ online: true, lat, lng })
      }
    }
    if (availability === 'offline') {
      return await this.patchDriverMeStatus({ online: false })
    }
    return await this.updatePresence(availability)
  }

  async getNotifications() {
    return await this.call('/notifications/')
  }

  async markNotificationRead(notificationId) {
    return await this.call(`/notifications/${notificationId}/read`, {
      method: 'POST'
    })
  }

  async testDatabaseConnection() {
    return await this.call('/test/db-connection')
  }

  async sendTestData(testData) {
    return await this.call('/test/driver-data', {
      method: 'POST',
      body: JSON.stringify(testData)
    })
  }

  async getTestLogs() {
    return await this.call('/test/driver-logs')
  }

  async logout() {
    const token = localStorage.getItem('driver_token')
    if (token && !token.startsWith('mock_')) {
      try {
        await fetch(`${this.getBaseUrl()}/auth/logout-all`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          signal: AbortSignal.timeout(Number(import.meta.env.VITE_API_TIMEOUT_MS) || 8_000),
        })
      } catch {
        // Best-effort server revocation; always clear local session.
      }
    }
    this.token = null
    localStorage.removeItem('driver_token')
    localStorage.removeItem('driver_refresh_token')
    localStorage.removeItem('driver_role')
  }

  isAuthenticated() {
    return !!localStorage.getItem('driver_token') && localStorage.getItem('driver_role') === 'driver'
  }
}

export const driverAPI = new DriverAPI()

export default driverAPI

export { ALLOW_OFFLINE_MOCK, ALLOW_RIDE_SIMULATION, MARKETPLACE_TRUTH_SOURCE }
