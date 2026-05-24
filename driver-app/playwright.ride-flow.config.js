import { defineConfig, devices } from '@playwright/test'
import os from 'os'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const backendDir = path.join(__dirname, '..', 'backend')
const PORT = Number(process.env.PLAYWRIGHT_RIDE_FLOW_PORT || 3024)
const baseURL = process.env.PLAYWRIGHT_BASE_URL || `http://127.0.0.1:${PORT}`
const BACKEND_PORT = Number(process.env.PLAYWRIGHT_RIDE_FLOW_BACKEND_PORT || 8011)
const rideFlowApiBase = `http://127.0.0.1:${BACKEND_PORT}`
/** Same-origin /api proxy avoids browser CORS failures in Playwright. */
const rideFlowAppApiBase = '/api'
process.env.VITE_API_BASE = rideFlowAppApiBase
process.env.VITE_API_PROXY_TARGET = rideFlowApiBase
const rideFlowDbPath = path.join(os.tmpdir(), `halfapp_ride_flow_${process.pid}.db`)
const rideFlowDatabaseUrl = `sqlite:///${rideFlowDbPath.replace(/\\/g, '/')}`

process.env.PLAYWRIGHT_RIDE_FLOW_BACKEND_PORT = String(BACKEND_PORT)

const uvicornCmd =
  process.env.UVICORN_CMD || 'node scripts/start-playwright-backend.mjs'

/** Full ride flow proof: isolated backend + mock-off driver app. */
export default defineConfig({
  testDir: './tests',
  testMatch: [
    '**/ride-flow-ui-proof.spec.ts',
    '**/sse-session-recovery.spec.ts',
    '**/sse-ride-pool.spec.ts',
    '**/session-recovery.spec.ts',
  ],
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
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
      cwd: path.join(__dirname),
      url: `${rideFlowApiBase}/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        ...process.env,
        DATABASE_URL: rideFlowDatabaseUrl,
        ALLOW_TEST_USER_SEED: 'true',
        HALFAPP_ENV: 'test',
        HALFAPP_ENABLE_RIDE_SIMULATION: '1',
        HALFAPP_OPEN_BOARD_DISPATCH: '1',
        SECRET_KEY: 'pytest-playwright-ride-flow-secret-32chars',
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
        VITE_API_BASE: rideFlowAppApiBase,
        VITE_API_PROXY_TARGET: rideFlowApiBase,
        VITE_GOOGLE_MAPS_FALLBACK_ENABLED: 'false',
        VITE_API_TIMEOUT_MS: '25000',
      },
    },
  ],
})
