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

const site = {
  site_id: 1,
  name: 'Raná',
  latitude: 50.403,
  longitude: 13.764,
  altitude: 457,
  tags: ['Czechia', 'flats'],
  predictions: dates.map((date, index) => ({
    date,
    values: [0.72 - index * 0.03, 0.61, 0.52, 0.43, 0.35, 0.28, 0.21, 0.16, 0.11, 0.07, 0.04],
    computed_at: '2026-08-01T09:30:00Z',
    gfs_forecast_at: '2026-08-01T06:00:00Z',
  })),
};

const backend = http.createServer((request, response) => {
  const url = new URL(request.url, `http://127.0.0.1:${backendPort}`);

  if (request.method === 'GET' && url.pathname === '/sites/1/predictions') {
    json(response, 200, [site]);
    return;
  }

  if (request.method === 'GET' && url.pathname === '/sites/1/info') {
    json(response, 200, {
      site_id: 1,
      site_name: 'Raná',
      country: 'Czechia',
      overview: 'Raná is a well-known Czech paragliding site.',
    });
    return;
  }

  if (request.method === 'GET' && url.pathname === '/sites/list') {
    json(response, 200, [{ site_id: 1, name: 'Raná' }]);
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
