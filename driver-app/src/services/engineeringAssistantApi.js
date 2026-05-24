/**
 * Engineering assistant API — backend proxy only.
 * Never calls Anthropic/OpenAI/Gemini directly from the browser.
 */

const env = typeof import.meta !== 'undefined' && import.meta.env ? import.meta.env : {}

function resolveApiBase() {
  if (typeof sessionStorage !== 'undefined') {
    const override = sessionStorage.getItem('halfapp_api_base_override')
    if (override) return override.replace(/\/$/, '')
  }
  const configured = env.VITE_API_BASE?.trim()
  if (configured) return configured.replace(/\/$/, '')
  return ''
}

/**
 * @param {string} path e.g. "/status" or "/chat"
 */
export function resolveEngineeringAssistantUrl(path) {
  const normalized = path.startsWith('/') ? path : `/${path}`
  const apiBase = resolveApiBase()
  if (apiBase) {
    return `${apiBase}/engineering-assistant${normalized}`
  }
  return `/api/engineering-assistant${normalized}`
}

function authHeaders(token) {
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  }
}

/**
 * @param {string} token
 * @returns {Promise<{ configured: boolean, provider: string | null }>}
 */
export async function fetchAssistantStatus(token) {
  const res = await fetch(resolveEngineeringAssistantUrl('/status'), {
    method: 'GET',
    headers: authHeaders(token),
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(detail || `Assistant status failed (${res.status})`)
  }
  return res.json()
}

/**
 * @param {string} token
 * @param {{ messages: Array<{ role: string, content: string }>, prompt: string }} body
 * @returns {Promise<{ reply: string, provider: string, model: string }>}
 */
export async function sendAssistantChat(token, body) {
  const res = await fetch(resolveEngineeringAssistantUrl('/chat'), {
    method: 'POST',
    headers: authHeaders(token),
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    let detail = `Assistant chat failed (${res.status})`
    try {
      const payload = await res.json()
      if (payload?.detail) {
        detail = typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail)
      }
    } catch {
      /* ignore */
    }
    throw new Error(detail)
  }
  return res.json()
}
