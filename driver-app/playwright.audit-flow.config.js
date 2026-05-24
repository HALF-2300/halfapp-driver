import { defineConfig, devices } from '@playwright/test'
import os from 'os'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const PORT = Number(process.env.PLAYWRIGHT_AUDIT_FLOW_PORT || 3036)
const baseURL = process.env.PLAYWRIGHT_BASE_URL || `http://127.0.0.1:${PORT}`
const BACKEND_PORT = Number(process.env.PLAYWRIGHT_AUDIT_FLOW_BACKEND_PORT || 8013)
const auditFlowApiBase = `http://127.0.0.1:${BACKEND_PORT}`
const auditFlowAppApiBase = '/api'
process.env.VITE_API_BASE = auditFlowAppApiBase
process.env.VITE_API_PROXY_TARGET = auditFlowApiBase
process.env.PLAYWRIGHT_RIDE_FLOW_BACKEND_PORT = String(BACKEND_PORT)
const auditFlowDbPath = path.join(os.tmpdir(), `halfapp_audit_flow_${process.pid}.db`)
const auditFlowDatabaseUrl = `sqlite:///${auditFlowDbPath.replace(/\\/g, '/')}`

const uvicornCmd = process.env.UVICORN_CMD || 'node scripts/start-playwright-backend.mjs'

/** Trip audit / receipt E2E: isolated backend + mock-off driver app. */
export default defineConfig({
  testDir: './tests',
  testMatch: '**/audit-flow-ui-proof.spec.ts',
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
      url: `${auditFlowApiBase}/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        ...process.env,
        DATABASE_URL: auditFlowDatabaseUrl,
        ALLOW_TEST_USER_SEED: 'true',
        HALFAPP_ENV: 'test',
        HALFAPP_ENABLE_RIDE_SIMULATION: '1',
        HALFAPP_OPEN_BOARD_DISPATCH: '1',
        SECRET_KEY: 'pytest-playwright-audit-flow-secret-32chars',
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
        VITE_API_BASE: auditFlowAppApiBase,
        VITE_API_PROXY_TARGET: auditFlowApiBase,
        VITE_GOOGLE_MAPS_FALLBACK_ENABLED: 'false',
        VITE_API_TIMEOUT_MS: '25000',
      },
    },
  ],
})
