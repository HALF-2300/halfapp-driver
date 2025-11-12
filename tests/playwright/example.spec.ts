import { test, expect } from '@playwright/test';

test('loads dashboard and checks health', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('HalfApp Dashboard')).toBeVisible();
});