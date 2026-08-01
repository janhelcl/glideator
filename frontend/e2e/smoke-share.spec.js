const { test, expect } = require('@playwright/test');

const todayUtc = () => new Date().toISOString().slice(0, 10);

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('disclaimerAccepted', 'true');
    window.__copiedForecastLink = null;

    Object.defineProperty(window.navigator, 'share', {
      configurable: true,
      value: undefined,
    });
    Object.defineProperty(window.navigator, 'clipboard', {
      configurable: true,
      value: {
        writeText: async (value) => {
          window.__copiedForecastLink = value;
        },
      },
    });
  });
});

test('copies a clean dated forecast URL that restores the shared state', async ({ page }) => {
  const date = todayUtc();

  await page.goto(`/details/1?date=${date}&metric=XC20&campaign=pilot`);

  await expect(page.getByRole('heading', { name: 'Raná', level: 1 })).toBeVisible();
  await expect(page).toHaveTitle(/Raná: 52% for XC20/);
  await expect(page.getByText(`Chances of a Flight on ${date}`, { exact: true })).toBeVisible();
  await expect(page.locator('meta[property="og:url"]').last()).toHaveAttribute(
    'content',
    'http://127.0.0.1:4173/details/1',
  );
  await expect(page.locator('meta[property="og:description"]').last()).toHaveAttribute(
    'content',
    /52% probability for XC20 activity at Raná/,
  );

  const shareButton = page.getByRole('button', { name: 'Share forecast for Raná' });
  await expect(shareButton).toBeVisible();
  await expect(shareButton).toHaveText('Share');
  await shareButton.click();
  await expect(page.getByText('Forecast link copied')).toBeVisible();

  const copiedUrl = await page.evaluate(() => window.__copiedForecastLink);
  expect(copiedUrl).toBe(`http://127.0.0.1:4173/details/1?date=${date}&metric=XC20`);

  await page.goto(copiedUrl);
  await expect(page).toHaveURL(new RegExp(`/details/1\\?date=${date}&metric=XC20(?:&tab=forecast)?$`));
  await expect(page).toHaveTitle(/Raná: 52% for XC20/);
  await expect(page.getByRole('button', { name: 'Share forecast for Raná' })).toBeVisible();
});
