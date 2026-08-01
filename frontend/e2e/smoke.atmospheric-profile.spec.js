const { test, expect } = require('@playwright/test');

test.use({
  viewport: { width: 390, height: 844 },
});

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('disclaimerAccepted', 'true');
  });
});

test('atmospheric profile has full height on its first expansion', async ({ page }) => {
  await page.route('**/api/sites/1/forecast**', async (route) => {
    // Keep the loading state visible while the MUI Collapse measures its first expansion.
    // The regression only appeared when the chart replaced that shorter content.
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

  const chart = page.locator('svg[aria-label="Atmospheric profile"]');
  await expect(chart).toBeVisible();

  await expect.poll(async () => {
    const box = await chart.boundingBox();
    return box?.height || 0;
  }).toBeGreaterThan(250);

  const box = await chart.boundingBox();
  expect(box).not.toBeNull();
  expect(box.width / box.height).toBeGreaterThan(0.95);
  expect(box.width / box.height).toBeLessThan(1.05);
});
