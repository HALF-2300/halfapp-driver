import { defineConfig, devices } from '@playwright/test'
import os from 'os'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const backendDir = path.join(__dirname, '..', 'backend')
/** Dedicated port so we never reuse a Vite dev server started with different env (e.g. offline mock). */
const PORT = Number(process.env.PLAYWRIGHT_TRUST_PORT || 3023)
const baseURL = process.env.PLAYWRIGHT_BASE_URL || `http://127.0.0.1:${PORT}`
/** Isolated from dev uvicorn on 8000; override with PLAYWRIGHT_TRUST_BACKEND_PORT. */
const BACKEND_PORT = Number(process.env.PLAYWRIGHT_TRUST_BACKEND_PORT || 8010)
const trustApiBase = `http://127.0.0.1:${BACKEND_PORT}`
/** Same-origin /api proxy avoids browser CORS failures in Playwright (matches ride-flow lane). */
const trustAppApiBase = '/api'
process.env.VITE_API_BASE = trustAppApiBase
process.env.VITE_API_PROXY_TARGET = trustApiBase
const trustDbPath = path.join(os.tmpdir(), `halfapp_trust_${process.pid}.db`)
const trustDatabaseUrl = `sqlite:///${trustDbPath.replace(/\\/g, '/')}`
process.env.PLAYWRIGHT_TRUST_BACKEND_PORT = String(BACKEND_PORT)

const uvicornCmd =
  process.env.UVICORN_CMD ||
  (process.platform === 'win32'
    ? `py -3.11 -m uvicorn main:app --host 127.0.0.1 --port ${BACKEND_PORT}`
    : `python3 -m uvicorn main:app --host 127.0.0.1 --port ${BACKEND_PORT}`)

/**
 * Mock-off + real API: VITE_ALLOW_OFFLINE_MOCK=false, VITE_API_BASE=trust lane backend port (default 8010)
 * Starts backend (SQLite) then Vite. Does not run stage1-honesty (those expect offline mock banner).
 */
export default defineConfig({
  testDir: './tests/trust-mock-off',
  testMatch: '**/*.spec.ts',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: 'list',
  use: {
    baseURL,
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: uvicornCmd,
      cwd: backendDir,
      url: `${trustApiBase}/health`,
      // Always start our backend: a reused process may be an older build without CORS for the trust Vite port (3023), which makes browser fetch fail with "Failed to fetch" while /health still passes.
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        ...process.env,
        DATABASE_URL: trustDatabaseUrl,
        HALFAPP_ENV: 'test',
        HALFAPP_ENABLE_RIDE_SIMULATION: '1',
        SECRET_KEY: 'pytest-playwright-trust-secret-32chars-min',
      },
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${PORT}`,
      url: baseURL,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        ...process.env,
        VITE_ALLOW_OFFLINE_MOCK: 'false',
        VITE_ENABLE_RIDE_SIMULATION: 'false',
        VITE_API_BASE: trustAppApiBase,
        VITE_API_PROXY_TARGET: trustApiBase,
      },
    },
  ],
})
