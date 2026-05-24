import { test, expect } from '@playwright/test';

test.use({ storageState: { cookies: [], origins: [] } });

function buildTestUser() {
  const stamp = Date.now();
  return {
    name: 'PlayUser',
    email: `playwright+${stamp}@example.com`,
    password: 'PWtest123',
    license_no: `DL${String(stamp).slice(-8)}`
  };
}

test('driver auth flow: register, welcome, logout, login, persistence', async ({ page }) => {
  const user = buildTestUser();

  await page.goto('/#/login');
  await expect(page.getByTestId('driver-portal-frontpage')).toBeVisible({ timeout: 15_000 });

  const signUpButton = page.getByRole('button', { name: 'Sign Up' });
  if (await signUpButton.isVisible()) {
    await signUpButton.click();
  }

  await page.getByPlaceholder('Full Name').fill(user.name);
  await page.getByPlaceholder(/license number/i).fill(user.license_no);
  await page.getByPlaceholder('Email Address').fill(user.email);
  await page.getByPlaceholder('Password').fill(user.password);

  await Promise.all([
    page.waitForURL('**/#/**', { timeout: 15_000 }),
    page.getByTestId('login-submit-btn').click(),
  ]);
  const cockpit = page.getByTestId('map-home');
  await expect(cockpit).toBeVisible({ timeout: 15_000 });

  await page.reload();
  await expect(cockpit).toBeVisible({ timeout: 15_000 });

  await Promise.all([
    page.waitForURL('**/#/', { timeout: 15_000 }),
    page.getByTestId('logout-btn').click(),
  ]);
  const segmentedSignIn = page.getByRole('button', { name: 'Sign In' }).first();
  await expect(segmentedSignIn).toBeVisible();

  const cls = (await segmentedSignIn.getAttribute('class')) || '';
  if (!cls.includes('bg-white')) {
    await segmentedSignIn.click();
  }

  await page.getByPlaceholder('Email Address').fill(user.email);
  await page.getByPlaceholder('Password').fill(user.password);

  const submitBtn = page.getByTestId('login-submit-btn');
  await expect(submitBtn).toBeEnabled({ timeout: 15_000 });
  await Promise.all([
    page.waitForURL('**/#/**', { timeout: 15_000 }),
    submitBtn.click(),
  ]);
  await expect(cockpit).toBeVisible({ timeout: 15_000 });
});
