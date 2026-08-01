const { test, expect } = require('@playwright/test');

test.use({ javaScriptEnabled: false });

const today = new Date().toISOString().slice(0, 10);

const forbiddenAgentPaths = (pathname) => (
  pathname.startsWith('/mcp') ||
  pathname.startsWith('/llms') ||
  pathname.startsWith('/api/llms')
);

const readXc0 = async (page, siteName) => {
  const table = page.locator(`table[aria-label="${siteName} seven-day forecast probabilities"]`);
  await expect(table).toHaveCount(1);
  const firstDataRow = table.locator('tbody tr').first();
  const xc0Text = await firstDataRow.locator('td').first().textContent();
  return Number(xc0Text.replace('%', ''));
};

test('site forecast is answerable from normal HTML without MCP or llms.txt', async ({ page }) => {
  const requestedPaths = [];
  page.on('request', (request) => {
    requestedPaths.push(new URL(request.url()).pathname);
  });

  const response = await page.goto(`/details/1?date=${today}&metric=XC0`);

  expect(response.status()).toBe(200);
  await expect(page.getByRole('heading', { name: 'Raná', level: 1 })).toBeVisible();

  const forecastTable = page.locator('table[aria-label="Raná seven-day forecast probabilities"]');
  const forecastText = await forecastTable.textContent();
  expect(forecastText).toContain('XC0');
  expect(forecastText).toContain('72%');
  expect(forecastText).toContain('2026-08-01T09:30:00Z');
  expect(forecastText).toContain('2026-08-01T06:00:00Z');

  expect(requestedPaths.some(forbiddenAgentPaths)).toBe(false);
});

test('two sites can be compared from their normal HTML pages', async ({ page }) => {
  const requestedPaths = [];
  page.on('request', (request) => {
    requestedPaths.push(new URL(request.url()).pathname);
  });

  await page.goto(`/details/1?date=${today}&metric=XC0`);
  const ranaXc0 = await readXc0(page, 'Raná');

  await page.goto(`/details/3?date=${today}&metric=XC0`);
  const kozakovXc0 = await readXc0(page, 'Kozákov');

  expect(ranaXc0).toBe(72);
  expect(kozakovXc0).toBe(55);
  expect(ranaXc0).toBeGreaterThan(kozakovXc0);
  expect(requestedPaths.some(forbiddenAgentPaths)).toBe(false);
});
