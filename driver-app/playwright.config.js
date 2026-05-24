import { defineConfig, devices } from '@playwright/test'

// Default 3022. If occupied by a stale HalfApp Vite dev server, run:
//   npm run test:e2e:cockpit   (runs scripts/ensure-playwright-port-free.mjs first)
const PORT = Number(process.env.PLAYWRIGHT_PORT || 3022)
const baseURL = process.env.PLAYWRIGHT_BASE_URL || `http://127.0.0.1:${PORT}`

export default defineConfig({
  testDir: './tests',
  testIgnore: ['**/trust-mock-off/**'],
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'list',
  globalSetup: process.env.PLAYWRIGHT_WITH_GLOBAL_SETUP === '1' ? './tests/global-setup.ts' : undefined,
  use: {
    baseURL,
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: `npm run dev -- --host 127.0.0.1 --port ${PORT}`,
    url: baseURL,
    reuseExistingServer: false,
    timeout: 120_000,
    env: {
      ...process.env,
      VITE_ALLOW_OFFLINE_MOCK: 'true',
      VITE_ENABLE_RIDE_SIMULATION: 'true',
    },
  },
})
