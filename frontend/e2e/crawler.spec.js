const { test, expect } = require('@playwright/test');

test.use({ javaScriptEnabled: false });

test('site forecast is answerable from normal HTML without MCP or llms.txt', async ({ page }) => {
  const requestedPaths = [];
  page.on('request', (request) => {
    requestedPaths.push(new URL(request.url()).pathname);
  });

  const response = await page.goto('/details/1?date=2026-08-01&metric=XC0');

  expect(response.status()).toBe(200);
  await expect(page.getByRole('heading', { name: 'Raná', level: 1 })).toBeVisible();

  const forecastTable = page.locator('table[aria-label="Raná seven-day forecast probabilities"]');
  await expect(forecastTable).toHaveCount(1);

  const forecastText = await forecastTable.textContent();
  expect(forecastText).toContain('XC0');
  expect(forecastText).toContain('72%');
  expect(forecastText).toContain('2026-08-01T09:30:00Z');
  expect(forecastText).toContain('2026-08-01T06:00:00Z');

  expect(requestedPaths.some((pathname) => (
    pathname.startsWith('/mcp') ||
    pathname.startsWith('/llms') ||
    pathname.startsWith('/api/llms')
  ))).toBe(false);
});
