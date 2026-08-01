const { test, expect } = require('@playwright/test');

test.use({
  viewport: { width: 390, height: 844 },
});

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('disclaimerAccepted', 'true');
  });
});

test('atmospheric profile is not clipped on its first expansion', async ({ page }) => {
  await page.route('**/api/sites/1/forecast**', async (route) => {
    // Reproduce the production sequence: the details panel opens with a short
    // loading state, then asynchronously receives the much taller chart.
    await new Promise((resolve) => setTimeout(resolve, 200));
    const response = await route.fetch();
    await route.fulfill({ response });
  });

  await page.goto('/?lat=50.4&lng=13.8&zoom=8');

  const marker = page.locator('.glowing-marker').first();
  await expect(marker).toBeVisible();
  await marker.click({ force: true });
  await page.getByRole('button', { name: 'View Details' }).click();

  await expect(page).toHaveURL(/\/details\/1/);
  await expect(page.getByRole('heading', { name: 'Raná', level: 1 })).toBeVisible();

  await page.getByRole('button', { name: /see what's driving this/i }).click();

  const panel = page.getByTestId('weather-details-panel');
  const chart = page.locator('svg[aria-label="Atmospheric profile"]');
  await expect(panel).toBeVisible();
  await expect(chart).toBeVisible();

  await expect.poll(async () => {
    const box = await chart.boundingBox();
    return box?.height || 0;
  }).toBeGreaterThan(250);

  const similarDaysHeading = page.getByText('Similar Days in the Past', { exact: true }).last();
  await expect(similarDaysHeading).toBeVisible();

  await expect.poll(async () => {
    const chartBox = await chart.boundingBox();
    const headingBox = await similarDaysHeading.boundingBox();
    if (!chartBox || !headingBox) return -1;
    return headingBox.y - (chartBox.y + chartBox.height);
  }).toBeGreaterThan(20);

  const chartBox = await chart.boundingBox();
  expect(chartBox).not.toBeNull();
  expect(chartBox.width / chartBox.height).toBeGreaterThan(0.95);
  expect(chartBox.width / chartBox.height).toBeLessThan(1.05);
});
