const { test, expect } = require('@playwright/test');

const todayUtc = () => new Date().toISOString().slice(0, 10);
const addDays = (date, days) => {
  const value = new Date(`${date}T00:00:00Z`);
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
};

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
    Object.defineProperty(window.navigator, 'geolocation', {
      configurable: true,
      value: {
        getCurrentPosition: (success) => success({
          coords: { latitude: 50.0875, longitude: 14.4213 },
          timestamp: Date.now(),
        }),
      },
    });
  });
});

test('copies a clean dated forecast URL from the global app bar', async ({ page }) => {
  const date = todayUtc();

  await page.goto(`/details/1?date=${date}&metric=XC20&campaign=pilot`);

  await expect(page.getByRole('heading', { name: 'Raná', level: 1 })).toBeVisible();
  await expect(page).toHaveTitle(/Raná: 52% chance of a 20\+ point flight/);
  await expect(page.getByText(`Chances of a Flight on ${date}`, { exact: true })).toBeVisible();
  await expect(page.locator('meta[property="og:url"]').last()).toHaveAttribute(
    'content',
    'http://127.0.0.1:4173/details/1',
  );
  await expect(page.locator('meta[property="og:description"]').last()).toHaveAttribute(
    'content',
    /52% chance of a 20\+ point flight at Raná/,
  );

  const shareButton = page.getByRole('button', { name: 'Share forecast for Raná' });
  await expect(shareButton).toBeVisible();
  await shareButton.click();
  await expect(page.getByText('Forecast link copied')).toBeVisible();

  const copiedUrl = await page.evaluate(() => window.__copiedForecastLink);
  expect(copiedUrl).toBe(`http://127.0.0.1:4173/details/1?date=${date}&metric=XC20`);

  await page.goto(copiedUrl);
  await expect(page).toHaveURL(new RegExp(`/details/1\\?date=${date}&metric=XC20(?:&tab=forecast)?$`));
  await expect(page).toHaveTitle(/Raná: 52% chance of a 20\+ point flight/);
  await expect(page.getByRole('button', { name: 'Share forecast for Raná' })).toBeVisible();
});

test('shares a privacy-rounded forecast map state', async ({ page }) => {
  const date = todayUtc();
  await page.goto(`/?date=${date}&metric=XC20&lat=50.12345&lng=14.98765&zoom=7.8&mapType=topographic&campaign=pilot`);

  const shareButton = page.getByRole('button', { name: 'Share forecast map' });
  await expect(shareButton).toBeVisible();
  await shareButton.click();
  await expect(page.getByText('Forecast map link copied')).toBeVisible();

  const copiedUrl = await page.evaluate(() => window.__copiedForecastLink);
  expect(copiedUrl).toBe(
    `http://127.0.0.1:4173/?date=${date}&metric=XC20&lat=50.12&lng=14.99&zoom=8&mapType=topographic`,
  );
});

test('offers a coarse shared origin for distance-filtered trip plans', async ({ page }) => {
  const startDate = todayUtc();
  const endDate = addDays(startDate, 1);
  await page.goto(
    `/trip-planner?startDate=${startDate}&endDate=${endDate}&distEnabled=true&distKm=200&metric=XC20&sortBy=distance`,
  );

  await page.getByRole('button', { name: 'Share trip plan' }).click();
  await expect(page.getByRole('heading', { name: 'Share starting area?' })).toBeVisible();
  await page.getByRole('button', { name: 'Include area' }).click();
  await expect(page.getByText('Trip plan link copied')).toBeVisible();

  const copiedUrl = await page.evaluate(() => window.__copiedForecastLink);
  expect(copiedUrl).toContain(`startDate=${startDate}`);
  expect(copiedUrl).toContain(`endDate=${endDate}`);
  expect(copiedUrl).toContain('metric=XC20');
  expect(copiedUrl).toContain('originLat=50.1');
  expect(copiedUrl).toContain('originLng=14.4');
});
