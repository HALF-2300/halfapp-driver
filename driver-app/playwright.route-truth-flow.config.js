import { defineConfig, devices } from '@playwright/test'
import os from 'os'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const PORT = Number(process.env.PLAYWRIGHT_ROUTE_TRUTH_FLOW_PORT || 3037)
const baseURL = process.env.PLAYWRIGHT_BASE_URL || `http://127.0.0.1:${PORT}`
const BACKEND_PORT = Number(process.env.PLAYWRIGHT_ROUTE_TRUTH_FLOW_BACKEND_PORT || 8014)
const routeTruthFlowApiBase = `http://127.0.0.1:${BACKEND_PORT}`
const routeTruthFlowAppApiBase = '/api'
process.env.VITE_API_BASE = routeTruthFlowAppApiBase
process.env.VITE_API_PROXY_TARGET = routeTruthFlowApiBase
process.env.PLAYWRIGHT_RIDE_FLOW_BACKEND_PORT = String(BACKEND_PORT)
const routeTruthFlowDbPath = path.join(os.tmpdir(), `halfapp_route_truth_flow_${process.pid}.db`)
const routeTruthFlowDatabaseUrl = `sqlite:///${routeTruthFlowDbPath.replace(/\\/g, '/')}`

const uvicornCmd = process.env.UVICORN_CMD || 'node scripts/start-playwright-backend.mjs'

/** Route truth / snapshot read UI E2E: isolated backend + mock-off driver app. */
export default defineConfig({
  testDir: './tests',
  testMatch: '**/route-truth-flow-ui-proof.spec.ts',
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
      url: `${routeTruthFlowApiBase}/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        ...process.env,
        DATABASE_URL: routeTruthFlowDatabaseUrl,
        ALLOW_TEST_USER_SEED: 'true',
        HALFAPP_ENV: 'test',
        HALFAPP_ENABLE_RIDE_SIMULATION: '1',
        HALFAPP_OPEN_BOARD_DISPATCH: '1',
        SECRET_KEY: 'pytest-playwright-route-truth-flow-secret-32ch',
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
        VITE_API_BASE: routeTruthFlowAppApiBase,
        VITE_API_PROXY_TARGET: routeTruthFlowApiBase,
        VITE_GOOGLE_MAPS_FALLBACK_ENABLED: 'false',
        VITE_API_TIMEOUT_MS: '25000',
      },
    },
  ],
})
