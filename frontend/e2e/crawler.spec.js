const { test, expect } = require('@playwright/test');

test.use({ javaScriptEnabled: false });

const today = new Date().toISOString().slice(0, 10);
const baseUrl = 'http://127.0.0.1:4173';

const isMcpPath = (pathname) => pathname.startsWith('/mcp');

const readXc0 = async (page, siteName) => {
  const table = page.locator(`table[aria-label="${siteName} seven-day forecast probabilities"]`);
  await expect(table).toHaveCount(1);
  const firstDataRow = table.locator('tbody tr').first();
  const xc0Text = await firstDataRow.locator('td').first().textContent();
  return Number(xc0Text.replace('%', ''));
};

test('homepage HTML exposes a ranked site comparison and normal detail links', async ({ page }) => {
  const requestedPaths = [];
  page.on('request', (request) => {
    requestedPaths.push(new URL(request.url()).pathname);
  });

  const response = await page.goto(`/?date=${today}&metric=XC0`);
  expect(response.status()).toBe(200);

  const ranking = page.locator(`table[aria-label="Paragliding site ranking for ${today} using XC0"]`);
  await expect(ranking).toHaveCount(1);

  const rows = ranking.locator('tbody tr');
  await expect(rows).toHaveCount(2);
  expect(await rows.nth(0).textContent()).toContain('Raná');
  expect(await rows.nth(0).textContent()).toContain('72%');
  expect(await rows.nth(1).textContent()).toContain('Kozákov');
  expect(await rows.nth(1).textContent()).toContain('55%');

  const ranaLink = ranking.locator(`a[href="/details/1?date=${today}&metric=XC0"]`);
  await expect(ranaLink).toHaveCount(1);
  expect(requestedPaths.some(isMcpPath)).toBe(false);
});

test('site forecast is answerable from normal HTML without MCP', async ({ page }) => {
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

  expect(requestedPaths.some(isMcpPath)).toBe(false);
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
  expect(requestedPaths.some(isMcpPath)).toBe(false);
});

test('crawler-facing metadata uses canonical URLs and structured place data', async ({ page }) => {
  const response = await page.goto(`/details/1?date=${today}&metric=XC0`);
  expect(response.status()).toBe(200);

  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
    'href',
    `${baseUrl}/details/1`,
  );
  await expect(page.locator('meta[property="og:url"]')).toHaveAttribute(
    'content',
    `${baseUrl}/details/1`,
  );

  const structuredData = JSON.parse(
    await page.locator('script[type="application/ld+json"]').last().textContent(),
  );
  expect(structuredData['@type']).toBe('Place');
  expect(structuredData.name).toBe('Raná');
  expect(structuredData.geo).toMatchObject({
    '@type': 'GeoCoordinates',
    latitude: 50.403,
    longitude: 13.764,
    elevation: 457,
  });
});

test('robots.txt allows public crawling and points to the canonical sitemap', async ({ request }) => {
  const response = await request.get('/robots.txt');
  expect(response.status()).toBe(200);

  const text = await response.text();
  expect(text).toContain('User-agent: *');
  expect(text).toContain('Allow: /');
  expect(text).toContain('Disallow: /api/');
  expect(text).toContain('Disallow: /mcp');
  expect(text).toContain('Sitemap: https://www.parra-glideator.com/sitemap.xml');
});

test('missing numeric site pages return an HTTP 404', async ({ page }) => {
  const response = await page.goto('/details/999999');
  expect(response.status()).toBe(404);
});

test('representative AI search crawlers receive the same public HTML', async ({ browser }) => {
  const userAgents = [
    'OAI-SearchBot/1.0',
    'Claude-SearchBot/1.0',
    'PerplexityBot/1.0',
  ];

  for (const userAgent of userAgents) {
    const context = await browser.newContext({
      baseURL: baseUrl,
      javaScriptEnabled: false,
      userAgent,
    });
    const page = await context.newPage();
    const response = await page.goto(`/?date=${today}&metric=XC0`);

    expect(response.status()).toBe(200);
    await expect(
      page.locator(`table[aria-label="Paragliding site ranking for ${today} using XC0"]`),
    ).toHaveCount(1);
    await context.close();
  }
});
