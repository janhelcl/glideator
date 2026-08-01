'use strict';

const { spawn } = require('child_process');
const http = require('http');
const path = require('path');

const backendPort = 4174;
const frontendPort = 4173;

const json = (response, status, body) => {
  response.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' });
  response.end(JSON.stringify(body));
};

const today = new Date();
const dates = Array.from({ length: 7 }, (_, index) => {
  const date = new Date(today);
  date.setUTCDate(today.getUTCDate() + index);
  return date.toISOString().slice(0, 10);
});

const makeSite = ({ siteId, name, latitude, longitude, altitude, xc0 }) => ({
  site_id: siteId,
  name,
  latitude,
  longitude,
  altitude,
  tags: ['Czechia'],
  predictions: dates.map((date, index) => ({
    date,
    values: [xc0 - index * 0.03, 0.61, 0.52, 0.43, 0.35, 0.28, 0.21, 0.16, 0.11, 0.07, 0.04],
    computed_at: '2026-08-01T09:30:00Z',
    gfs_forecast_at: '2026-08-01T06:00:00Z',
  })),
});

const sites = {
  1: makeSite({
    siteId: 1,
    name: 'Raná',
    latitude: 50.403,
    longitude: 13.764,
    altitude: 457,
    xc0: 0.72,
  }),
  3: makeSite({
    siteId: 3,
    name: 'Kozákov',
    latitude: 50.593,
    longitude: 15.263,
    altitude: 744,
    xc0: 0.55,
  }),
};

const flightStats = {
  0: [0.2, 0.5, 2.1, 5.4, 8.2, 9.1, 8.7, 7.9, 5.8, 2.6, 0.7, 0.2],
  10: [0.1, 0.2, 1.1, 3.2, 5.4, 6.2, 5.9, 5.1, 3.4, 1.2, 0.2, 0.1],
  20: [0, 0.1, 0.5, 1.8, 3.7, 4.5, 4.2, 3.6, 2.1, 0.6, 0.1, 0],
  30: [], 40: [], 50: [], 60: [], 70: [], 80: [], 90: [], 100: [],
};

const makeForecastValues = (hour) => ({
  temperature_2m_c: 15 + hour / 6,
  dewpoint_2m_c: 8 + hour / 12,
  wind_speed_10m_ms: 3 + hour / 12,
  wind_direction_10m_dgr: 220 + hour,
  wind_gust_sfc_ms: 6 + hour / 10,
  pressure_sfc_pa: 101200 - hour * 10,
  geopotential_height_sfc_m: 430,
  geopotential_height_iso_m: [3000, 2500, 2000, 1500, 1000, 500],
  temperature_iso_c: [-5, -1, 3, 7, 11, 14],
  dewpoint_iso_c: [-12, -8, -2, 2, 5, 8],
  wind_speed_iso_ms: [12, 10, 8, 6, 5, 4],
  wind_direction_iso_dgr: [240, 235, 230, 225, 220, 215],
  relative_humidity_iso_pct: [40, 45, 50, 55, 60, 65],
  hpa_lvls: [700, 750, 800, 850, 900, 950],
});

const backend = http.createServer((request, response) => {
  const url = new URL(request.url, `http://127.0.0.1:${backendPort}`);
  const predictionMatch = url.pathname.match(/^\/sites\/(\d+)\/predictions$/);
  const infoMatch = url.pathname.match(/^\/sites\/(\d+)\/info$/);
  const statsMatch = url.pathname.match(/^\/sites\/(\d+)\/flight_stats$/);
  const spotsMatch = url.pathname.match(/^\/sites\/(\d+)\/spots$/);
  const resourcesMatch = url.pathname.match(/^\/sites\/(\d+)\/resources$/);
  const forecastMatch = url.pathname.match(/^\/sites\/(\d+)\/forecast$/);
  const similarDaysMatch = url.pathname.match(/^\/d2d\/similar-days\/(\d+)\/(\d{4}-\d{2}-\d{2})$/);

  if (request.method === 'GET' && url.pathname === '/sites/') {
    json(response, 200, Object.values(sites));
    return;
  }

  if (request.method === 'GET' && predictionMatch && sites[predictionMatch[1]]) {
    json(response, 200, [sites[predictionMatch[1]]]);
    return;
  }

  if (request.method === 'GET' && infoMatch && sites[infoMatch[1]]) {
    const matchedSite = sites[infoMatch[1]];
    json(response, 200, {
      site_id: matchedSite.site_id,
      site_name: matchedSite.name,
      country: 'Czechia',
      html: `<p>${matchedSite.name} test overview.</p>`,
    });
    return;
  }

  if (request.method === 'GET' && statsMatch && sites[statsMatch[1]]) {
    json(response, 200, flightStats);
    return;
  }

  if (request.method === 'GET' && spotsMatch && sites[spotsMatch[1]]) {
    json(response, 200, [
      {
        spot_id: Number(spotsMatch[1]) * 10 + 1,
        site_id: Number(spotsMatch[1]),
        name: 'South launch',
        latitude: sites[spotsMatch[1]].latitude,
        longitude: sites[spotsMatch[1]].longitude,
        altitude: sites[spotsMatch[1]].altitude,
        type: 'takeoff',
        wind_direction: 'S-SW',
      },
      {
        spot_id: Number(spotsMatch[1]) * 10 + 2,
        site_id: Number(spotsMatch[1]),
        name: 'Main landing',
        latitude: sites[spotsMatch[1]].latitude - 0.01,
        longitude: sites[spotsMatch[1]].longitude + 0.01,
        altitude: sites[spotsMatch[1]].altitude - 120,
        type: 'landing',
        wind_direction: null,
      },
    ]);
    return;
  }

  if (request.method === 'GET' && resourcesMatch && sites[resourcesMatch[1]]) {
    json(response, 200, {
      site_id: Number(resourcesMatch[1]),
      source_run_id: 42,
      run_extracted_at: '2026-07-31T18:00:00Z',
      local_resources: [
        {
          candidate_id: 101,
          name: `${sites[resourcesMatch[1]].name} flying club`,
          url: 'https://example.com/local-club',
          host: 'example.com',
          rules: true,
          access: true,
        },
      ],
      webcam_urls: ['https://example.com/webcam'],
      meteostation_urls: ['https://example.com/meteo'],
    });
    return;
  }

  if (request.method === 'GET' && forecastMatch && sites[forecastMatch[1]]) {
    json(response, 200, {
      date: url.searchParams.get('query_date') || dates[0],
      computed_at: '2026-08-01T09:30:00Z',
      gfs_forecast_at: '2026-08-01T06:00:00Z',
      lat_gfs: sites[forecastMatch[1]].latitude,
      lon_gfs: sites[forecastMatch[1]].longitude,
      forecast_9: makeForecastValues(9),
      forecast_12: makeForecastValues(12),
      forecast_15: makeForecastValues(15),
    });
    return;
  }

  if (request.method === 'GET' && similarDaysMatch && sites[similarDaysMatch[1]]) {
    json(response, 200, {
      site_id: Number(similarDaysMatch[1]),
      forecast_date: similarDaysMatch[2],
      similar_days: [
        { past_date: '2025-07-15', similarity: 0.91 },
        { past_date: '2024-08-03', similarity: 0.84 },
      ],
    });
    return;
  }

  if (request.method === 'GET' && url.pathname === '/sites/list') {
    json(response, 200, Object.values(sites).map(({ site_id, name }) => ({ site_id, name })));
    return;
  }

  if (request.method === 'POST' && url.pathname === '/auth/refresh') {
    json(response, 401, { detail: 'No active session' });
    return;
  }

  json(response, 404, { detail: 'Not found in SSR test backend' });
});

let frontend;

const shutdown = () => {
  if (frontend && !frontend.killed) frontend.kill('SIGTERM');
  backend.close(() => process.exit(0));
};

backend.listen(backendPort, '127.0.0.1', () => {
  frontend = spawn(process.execPath, [path.resolve(__dirname, '../server/index.js')], {
    cwd: path.resolve(__dirname, '..'),
    env: {
      ...process.env,
      PORT: String(frontendPort),
      HOST: '127.0.0.1',
      BACKEND_API_URL: `http://127.0.0.1:${backendPort}`,
      PUBLIC_ORIGIN: `http://127.0.0.1:${frontendPort}`,
    },
    stdio: 'inherit',
  });

  frontend.on('exit', (code) => {
    backend.close(() => process.exit(code || 0));
  });
});

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
