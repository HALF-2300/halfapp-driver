import { test, expect } from '@playwright/test';

test('loads landing page and checks content', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'HalfApp' })).toBeVisible();
});