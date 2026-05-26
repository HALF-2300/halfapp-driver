import { defineConfig, devices } from '@playwright/test'
import os from 'os'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const PORT = Number(process.env.PLAYWRIGHT_RIDE_AI_PORT || 3026)
const baseURL = process.env.PLAYWRIGHT_BASE_URL || `http://127.0.0.1:${PORT}`
const BACKEND_PORT = Number(process.env.PLAYWRIGHT_RIDE_AI_BACKEND_PORT || 8012)
const apiBase = `http://127.0.0.1:${BACKEND_PORT}`
const appApiBase = '/api'

process.env.PLAYWRIGHT_RIDE_FLOW_BACKEND_PORT = String(BACKEND_PORT)
process.env.VITE_API_PROXY_TARGET = apiBase

const dbPath = path.join(os.tmpdir(), `halfapp_ride_ai_dispatch_${process.pid}.db`)
const databaseUrl = `sqlite:///${dbPath.replace(/\\/g, '/')}`

const uvicornCmd = process.env.UVICORN_CMD || 'node scripts/start-playwright-backend.mjs'

export default defineConfig({
  testDir: './tests',
  testMatch: ['**/ride-ai-dispatch-ui-proof.spec.ts'],
  fullyParallel: false,
  workers: 1,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report-ride-ai-dispatch' }]],
  use: {
    baseURL,
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: uvicornCmd,
      cwd: __dirname,
      url: `${apiBase}/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        ...process.env,
        PLAYWRIGHT_RIDE_FLOW_BACKEND_PORT: String(BACKEND_PORT),
        DATABASE_URL: databaseUrl,
        ALLOW_TEST_USER_SEED: 'true',
        HALFAPP_ENV: 'test',
        HALFAPP_ENABLE_RIDE_SIMULATION: '1',
        HALFAPP_OPEN_BOARD_DISPATCH: '1',
        HALFAPP_AUTO_ASSIGN: '0',
        ROUTING_PROVIDER: 'osrm_self_hosted',
        OSRM_BASE_URL: process.env.OSRM_BASE_URL || 'http://127.0.0.1:5000',
        ROUTING_FALLBACK_ENABLED: 'true',
        SECRET_KEY: 'pytest-playwright-ride-ai-dispatch',
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
        VITE_ENABLE_RIDE_SIMULATION: 'true',
        VITE_API_BASE: appApiBase,
        VITE_API_PROXY_TARGET: apiBase,
      },
    },
  ],
})
