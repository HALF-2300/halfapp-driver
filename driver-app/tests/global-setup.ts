import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

/**
 * Pre-auth storage for nav-flow tests: obtain a real JWT from the API when possible.
 * Requires backend on PLAYWRIGHT_API_URL (default http://127.0.0.1:8000) with SQLite or Postgres.
 */
async function obtainAccessToken(apiBase: string): Promise<string> {
  const email = 'test@driver.com'
  const password = 'password123'
  const name = 'Test Driver'
  const license_no = 'DLPLAY1'

  let res = await fetch(`${apiBase}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (res.ok) {
    const j = (await res.json()) as { access_token: string }
    return j.access_token
  }

  await fetch(`${apiBase}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, name, role: 'driver', license_no }),
  }).catch(() => null)

  res = await fetch(`${apiBase}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(
      `Playwright globalSetup: cannot login at ${apiBase}. Start backend (e.g. DATABASE_URL=sqlite:///./halfapp_local.db). ${res.status} ${text}`
    )
  }
  const j = (await res.json()) as { access_token: string }
  return j.access_token
}

export default async function globalSetup() {
  const __filename = fileURLToPath(import.meta.url)
  const __dirname = path.dirname(__filename)
  const authDir = path.resolve(__dirname, '.auth')
  const statePath = path.join(authDir, 'driver.json')

  fs.mkdirSync(authDir, { recursive: true })

  const apiBase = process.env.PLAYWRIGHT_API_URL || 'http://127.0.0.1:8000'
  // Must match the URL the browser uses for driver-app (do not use generic BASE_URL / other frontend ports).
  const origin = process.env.PLAYWRIGHT_DRIVER_URL || 'http://127.0.0.1:3022'

  const token = await obtainAccessToken(apiBase)

  const storageState = {
    cookies: [],
    origins: [
      {
        origin,
        localStorage: [
          { name: 'driver_token', value: token },
          { name: 'driver_role', value: 'driver' }
        ]
      }
    ]
  }

  fs.writeFileSync(statePath, JSON.stringify(storageState, null, 2), 'utf-8')
  console.log(`Wrote auth storage state to: ${statePath} (token from ${apiBase})`)
}
