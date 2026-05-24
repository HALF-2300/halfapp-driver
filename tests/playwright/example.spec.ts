import { test, expect } from '@playwright/test';

// Smoke: `/` should mount LandingPage (React). Uses driver login link (stable route).
// If this fails, check browser console for bundle errors; `index.html` also has a 3s
// fallback panel that can mask a broken SPA (see honest report).
test('loads root and shows HalfApp landing', async ({ page }) => {
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  const driverLink = page.locator('a[href="/driver/login"]');
  await expect(driverLink).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole('heading', { name: /HalfApp/i })).toBeVisible();
});
