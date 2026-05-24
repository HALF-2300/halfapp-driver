/**
 * Authenticated SSE wrapper for the driver ride pool.
 * EventSource does not support custom headers in browsers, so JWT goes in URL.
 * Acceptable here because:
 *   - URL only travels over HTTPS to our own backend
 *   - Token is short-lived (15 min refresh rotation)
 *   - Server validates same as Authorization header
 */

function resolveApiBase() {
  if (typeof sessionStorage !== 'undefined') {
    const override = sessionStorage.getItem('halfapp_api_base_override')
    if (override) return override
  }
  return import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'
}

function buildStreamUrl(apiBase, token) {
  const path = `${apiBase.replace(/\/$/, '')}/drivers/available-rides/stream`
  const url = path.startsWith('http')
    ? new URL(path)
    : new URL(path, window.location.origin)
  url.searchParams.set('access_token', token)
  return url.toString()
}

/** Normalize v0.1 pool_delta payloads to flat event types for UI handlers. */
export function normalizePoolDelta(raw) {
  if (raw?.type === 'pool_delta') {
    return {
      type: raw.event,
      ride_id: raw.ride_id,
      ride: raw.ride ?? null,
      removed: Boolean(raw.removed),
    }
  }
  return raw
}

/**
 * @param {string} token
 * @param {{ onSnapshot?: (rides: unknown[]) => void, onDelta?: (event: unknown) => void, onError?: (err: unknown) => void, apiBase?: string }} handlers
 * @returns {() => void} unsubscribe
 */
export function subscribeRidePool(token, { onSnapshot, onDelta, onError, apiBase = resolveApiBase() } = {}) {
  if (!token || token.startsWith('mock_')) {
    onError?.(new Error('sse_unavailable'))
    return () => {}
  }

  let es = null
  let closed = false

  try {
    es = new EventSource(buildStreamUrl(apiBase, token))

    es.addEventListener('snapshot', (event) => {
      if (closed || !event?.data) return
      try {
        onSnapshot?.(JSON.parse(event.data))
      } catch (err) {
        onError?.(err)
      }
    })

    es.addEventListener('delta', (event) => {
      if (closed || !event?.data) return
      try {
        onDelta?.(normalizePoolDelta(JSON.parse(event.data)))
      } catch (err) {
        onError?.(err)
      }
    })

    es.onerror = () => {
      if (!closed) onError?.(new Error('sse_connection_error'))
    }
  } catch (err) {
    onError?.(err)
    return () => {}
  }

  return () => {
    closed = true
    if (es) {
      es.close()
      es = null
    }
  }
}
