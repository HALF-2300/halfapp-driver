import { defineConfig, devices } from '@playwright/test'
import os from 'os'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const PORT = Number(process.env.PLAYWRIGHT_RIDER_FLOW_PORT || 3025)
const baseURL = process.env.PLAYWRIGHT_BASE_URL || `http://127.0.0.1:${PORT}`
const BACKEND_PORT = Number(process.env.PLAYWRIGHT_RIDER_FLOW_BACKEND_PORT || 8012)
const apiBase = `http://127.0.0.1:${BACKEND_PORT}`
const appApiBase = '/api'

process.env.PLAYWRIGHT_RIDER_FLOW_BACKEND_PORT = String(BACKEND_PORT)
process.env.VITE_API_BASE = appApiBase
process.env.VITE_API_PROXY_TARGET = apiBase

const rideFlowDbPath = path.join(os.tmpdir(), `halfapp_rider_flow_${process.pid}.db`)
const rideFlowDatabaseUrl = `sqlite:///${rideFlowDbPath.replace(/\\/g, '/')}`

export default defineConfig({
  testDir: './tests',
  testMatch: ['**/ride-flow-ui-proof.spec.ts'],
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 2 : 1,
  reporter: 'list',
  use: {
    baseURL,
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: 'node scripts/start-playwright-backend.mjs',
      cwd: __dirname,
      url: `${apiBase}/health`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        ...process.env,
        DATABASE_URL: rideFlowDatabaseUrl,
        ALLOW_TEST_USER_SEED: 'true',
        HALFAPP_ENV: 'test',
        HALFAPP_OPEN_BOARD_DISPATCH: '1',
        SECRET_KEY: 'pytest-playwright-rider-flow-secret-32chars',
      },
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${PORT}`,
      url: baseURL,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        ...process.env,
        VITE_API_BASE: appApiBase,
        VITE_API_PROXY_TARGET: apiBase,
      },
    },
  ],
})
