const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

/**
 * Bounded retries for ride-write POSTs only (Slice 03).
 * GET and other methods are not retried here — avoids global GET blast radius.
 */
export async function resilientFetch(url, options = {}, cfg = {}) {
  const {
    timeoutMs = Number(import.meta?.env?.VITE_API_TIMEOUT_MS) || 8_000,
    retries = 2,
    retryOn = [502, 503, 504],
    methodRetryAllowlist = ['POST'],
  } = cfg

  const method = (options.method || 'GET').toUpperCase()
  const canRetry = methodRetryAllowlist.includes(method)

  const attemptOnce = async () => {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), timeoutMs)
    try {
      return await fetch(url, { ...options, signal: controller.signal })
    } finally {
      clearTimeout(timer)
    }
  }

  let attempt = 0
  while (true) {
    try {
      const response = await attemptOnce()
      if (!canRetry) return response

      if (retryOn.includes(response.status) && attempt < retries) {
        await sleep(250 * 2 ** attempt)
        attempt += 1
        continue
      }
      return response
    } catch (error) {
      if (!canRetry || attempt >= retries) throw error
      await sleep(250 * 2 ** attempt)
      attempt += 1
    }
  }
}
