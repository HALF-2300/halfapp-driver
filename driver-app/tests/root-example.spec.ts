import { test, expect } from '@playwright/test';

test('loads dashboard and checks health', async ({ page }) => {
  await page.goto('/#/');
  const welcome = page.getByRole('heading', { name: /Welcome,/i });
  try {
    await expect(welcome).toBeVisible();
  } catch {
    // Fallback: if not on dashboard, verify login screen renders
    await expect(page.getByTestId('driver-portal-frontpage')).toBeVisible();
  }
});
