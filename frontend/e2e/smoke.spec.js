const { test, expect } = require('@playwright/test');

const json = (route, body, status = 200) => route.fulfill({
  status,
  contentType: 'application/json',
  body: JSON.stringify(body),
});

const futureDate = (daysAhead) => {
  const date = new Date();
  date.setUTCDate(date.getUTCDate() + daysAhead);
  return date.toISOString().slice(0, 10);
};

const makePredictionSite = (siteId, name, date = futureDate(1)) => ({
  site_id: siteId,
  name,
  latitude: 50 + siteId / 100,
  longitude: 14 + siteId / 100,
  altitude: 400 + siteId * 10,
  predictions: [{
    date,
    values: [0.82, 0.76, 0.7, 0.64, 0.58, 0.52, 0.46, 0.4, 0.34, 0.28, 0.22],
  }],
});

const makePlannedSite = (siteId, name) => ({
  site_id: siteId,
  site_name: name,
  latitude: 45 + siteId / 100,
  longitude: 10 + siteId / 100,
  altitude: 500 + siteId * 20,
  distance_km: 20 + siteId,
  average_flyability: Math.max(0.1, 0.95 - siteId / 100),
  daily_probabilities: [
    { date: futureDate(1), probability: 0.8, source: 'forecast' },
    { date: futureDate(2), probability: 0.7, source: 'forecast' },
  ],
});

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.setItem('disclaimerAccepted', 'true');
  });
});

async function mockSitesCollection(page, sites) {
  await page.route('**/api/sites/**', async (route) => {
    const { pathname } = new URL(route.request().url());
    if (pathname === '/api/sites/') {
      await json(route, sites);
      return;
    }
    await route.fallback();
  });
}

async function mockSitesList(page, sites = []) {
  await page.route('**/api/sites/**', async (route) => {
    const { pathname } = new URL(route.request().url());
    if (pathname === '/api/sites/list') {
      await json(route, sites);
      return;
    }
    await route.fallback();
  });
}

async function mockLoggedOutSession(page) {
  await page.route('**/api/auth/refresh', (route) => json(route, { detail: 'No active session' }, 401));
  await mockSitesList(page);
}

async function mockDetails(page, siteId, name) {
  const site = makePredictionSite(siteId, name);
  await page.route(`**/api/sites/${siteId}/predictions`, (route) => json(route, [site]));
  await page.route(`**/api/sites/${siteId}/info`, (route) => json(route, {
    site_id: siteId,
    site_name: name,
    country: 'Czechia',
    overview: `${name} test overview`,
  }));
}

async function mockLoginFlow(page, { favorites = [1] } = {}) {
  await mockLoggedOutSession(page);
  let authenticated = false;

  await page.route('**/api/auth/refresh', (route) => {
    if (authenticated) {
      return json(route, {
        access_token: 'e2e-refreshed-access-token',
        token_type: 'bearer',
      });
    }
    return json(route, { detail: 'No active session' }, 401);
  });
  await page.route('**/api/auth/login', (route) => {
    authenticated = true;
    return json(route, {
      access_token: 'e2e-access-token',
      token_type: 'bearer',
    });
  });
  await page.route('**/api/auth/me', (route) => json(route, {
    user_id: 7,
    email: 'pilot@example.com',
  }));
  await page.route('**/api/users/me/profile', (route) => json(route, {
    display_name: 'E2E Pilot',
    preferred_metric: 'XC0',
    home_lat: 50.08,
    home_lon: 14.43,
  }));
  await page.route('**/api/users/me/favorites', async (route) => {
    if (route.request().method() === 'GET') {
      await json(route, favorites);
      return;
    }
    await route.fulfill({ status: 204 });
  });
  await page.route('**/api/users/me/push-subscriptions', (route) => json(route, []));
  await page.route('**/api/users/me/notifications', async (route) => {
    if (route.request().method() === 'GET') {
      await json(route, []);
      return;
    }
    await route.fallback();
  });
  await page.route('**/api/users/me/notification-events**', (route) => json(route, []));
  await mockSitesCollection(page, []);

  await page.goto('/login');
  await page.getByLabel('Email').fill('pilot@example.com');
  await page.getByLabel('Password').fill('test-password');
  await page.getByRole('button', { name: 'Log In' }).click();
  await expect(page).toHaveURL(/\/(?:\?.*)?$/);
}

test('home map opens a site details page', async ({ page }) => {
  const today = new Date().toISOString().slice(0, 10);
  const site = makePredictionSite(1, 'Raná', today);

  await mockLoggedOutSession(page);
  await mockSitesCollection(page, [site]);
  await mockDetails(page, 1, 'Raná');

  await page.goto('/?lat=50.4&lng=13.8&zoom=8');
  await expect(page).toHaveTitle(/Parra-Glideator/);

  const marker = page.locator('.glowing-marker').first();
  await expect(marker).toBeVisible();
  await marker.click({ force: true });
  await page.getByRole('button', { name: 'View Details' }).click();

  await expect(page).toHaveURL(/\/details\/1/);
  await expect(page.getByRole('heading', { name: 'Raná', level: 1 })).toBeVisible();
});

test('trip planner restores filters, paginates, and opens a result', async ({ page }) => {
  const startDate = futureDate(1);
  const endDate = futureDate(2);
  const requestBodies = [];

  await mockLoggedOutSession(page);
  await page.route('**/api/plan-trip', async (route) => {
    const body = route.request().postDataJSON();
    requestBodies.push(body);

    const offset = body.offset || 0;
    if (offset === 0) {
      await json(route, {
        sites: Array.from({ length: 10 }, (_, index) => makePlannedSite(index + 1, `Alpine ${index + 1}`)),
        total_count: 12,
        has_more: true,
      });
      return;
    }

    await json(route, {
      sites: [makePlannedSite(11, 'Alpine 11'), makePlannedSite(12, 'Alpine 12')],
      total_count: 12,
      has_more: false,
    });
  });
  await mockDetails(page, 12, 'Alpine 12');

  await page.goto(`/trip-planner?startDate=${startDate}&endDate=${endDate}&metric=XC20&fqEnabled=true&tags=ridge&view=list`);

  await expect(page.getByRole('heading', { name: 'Plan a Trip', level: 1 })).toBeVisible();
  await expect(page.getByText('Top 10 sites (12 total)')).toBeVisible();
  await page.getByRole('button', { name: 'More' }).click();
  await expect(page.getByText('Top 12 sites (12 total)')).toBeVisible();

  expect(requestBodies).toHaveLength(2);
  expect(requestBodies[0]).toMatchObject({
    start_date: startDate,
    end_date: endDate,
    metric: 'XC20',
    required_tags: ['ridge'],
    offset: 0,
    limit: 10,
  });
  expect(requestBodies[1]).toMatchObject({ offset: 10, limit: 10 });

  await page.getByRole('button', { name: 'View details for Alpine 12', exact: true }).click();
  await expect(page).toHaveURL(/\/details\/12/);
  await expect(page.getByRole('heading', { name: 'Alpine 12', level: 1 })).toBeVisible();
});

test('login allows adding a recommended site to favorites', async ({ page }) => {
  const favoriteSite = makePredictionSite(1, 'Favorite Ridge');
  const recommendation = makePredictionSite(2, 'Recommendation Ridge');
  let favoriteRequest = null;

  await mockLoginFlow(page, { favorites: [1] });
  await mockSitesCollection(page, [favoriteSite, recommendation]);
  await page.route('**/api/s2s/recommendations', (route) => json(route, {
    recommendations: [{ site_id: 2, similarity_score: 0.93 }],
  }));
  await page.route('**/api/users/me/favorites', async (route) => {
    if (route.request().method() === 'POST') {
      favoriteRequest = route.request().postDataJSON();
      await route.fulfill({ status: 204 });
      return;
    }
    await route.fallback();
  });

  await page.goto('/favorites');
  await expect(page.getByRole('heading', { name: 'My Favorites', level: 1 })).toBeVisible();
  await expect(page.getByText('Recommendation Ridge')).toBeVisible();

  const addButton = page.getByRole('button', {
    name: 'Add Recommendation Ridge to favorites',
    exact: true,
  });
  await addButton.click();

  await expect(addButton).toHaveCount(0);
  expect(favoriteRequest).toEqual({ site_id: 2 });
});

test('authenticated pilot creates a notification from site details', async ({ page }) => {
  let notificationPayload = null;

  await mockLoginFlow(page, { favorites: [1] });
  await mockDetails(page, 1, 'Raná');
  await mockSitesList(page, [
    { site_id: 1, name: 'Raná' },
    { site_id: 2, name: 'Kozákov' },
  ]);
  await page.route('**/api/users/me/notifications', async (route) => {
    if (route.request().method() === 'POST') {
      notificationPayload = route.request().postDataJSON();
      await json(route, {
        notification_id: 99,
        ...notificationPayload,
        last_triggered_at: null,
      });
      return;
    }
    await json(route, []);
  });

  await page.goto(`/details/1?date=${futureDate(1)}&metric=XC20`);
  await expect(page.getByRole('heading', { name: 'Raná', level: 1 })).toBeVisible();
  await page.getByRole('button', { name: 'Create notification' }).click();

  await expect(page.getByRole('dialog', { name: 'Create notification' })).toBeVisible();
  await page.getByLabel('Threshold (%)').fill('65');
  await page.getByRole('button', { name: 'Save' }).click();

  await expect(page.getByText('Notification saved.')).toBeVisible();
  expect(notificationPayload).toMatchObject({
    site_id: 1,
    metric: 'XC20',
    comparison: 'gte',
    threshold: 65,
    active: true,
  });
});
