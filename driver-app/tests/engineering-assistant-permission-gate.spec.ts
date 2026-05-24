import { test, expect } from '@playwright/test'
import { loginDriver } from './helpers/driverLogin.ts'

const PROVIDER_HOST_PATTERN =
  /api\.anthropic\.com|api\.openai\.com|generativelanguage\.googleapis\.com/

test.describe('HALFAPP_AI_ASSISTANT_PERMISSION_GATE_01', () => {
  test('initial cockpit render performs zero external model provider requests', async ({ page }) => {
    const providerRequests: string[] = []
    page.on('request', (request) => {
      const url = request.url()
      if (PROVIDER_HOST_PATTERN.test(url)) {
        providerRequests.push(url)
      }
    })

    await loginDriver(page)
    await expect(page.getByTestId('experimental-map-panel')).toBeVisible({ timeout: 15000 })

    expect(providerRequests).toEqual([])
  })

  test('quick actions fill prompt locally without provider requests', async ({ page }) => {
    const providerRequests: string[] = []
    const assistantRequests: string[] = []

    page.on('request', (request) => {
      const url = request.url()
      if (PROVIDER_HOST_PATTERN.test(url)) {
        providerRequests.push(url)
      }
      if (url.includes('engineering-assistant')) {
        assistantRequests.push(url)
      }
    })

    await loginDriver(page)
    await page.getByTestId('diagnostics-toggle').click()
    await expect(page.getByTestId('halfapp-engineer-panel')).toBeVisible()
    await expect(page.getByTestId('ai-connection-status')).toContainText(/AI off/i)

    await page.getByTestId('quick-action-summarize_truth').click()
    await expect(page.getByTestId('engineer-prompt-input')).not.toHaveValue('')

    await page.getByTestId('local-research-current_truth').click()
    await expect(page.getByTestId('engineer-local-context')).toBeVisible()

    expect(providerRequests).toEqual([])
    expect(assistantRequests).toEqual([])
  })
})
