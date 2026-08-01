# Glideator frontend

React frontend for Parra-Glideator, including the forecast map, site details, trip planner, accounts, notifications, feedback, and the administrator cockpit.

## Stack

- React 18
- Vite for development, client builds, and SSR builds
- Vitest and React Testing Library
- Playwright smoke and crawler tests
- Material UI
- React Router
- TanStack Query
- Leaflet / React Leaflet
- D3
- Axios

## Requirements

- Node.js 22.12 or newer
- npm
- A running Glideator backend for API-backed development

## Local development

```bash
npm ci
npm start
```

The Vite development server listens on port 3000 and proxies `/api` and `/mcp` to `BACKEND_API_URL`, which defaults to `http://localhost:8000`.

The root `docker-compose.dev.yml` also runs the frontend and backend together.

## Environment variables

The frontend accepts both the existing CRA-style names and their Vite equivalents during the migration:

| Existing name | Vite equivalent | Purpose |
|---|---|---|
| `REACT_APP_API_BASE_URL` | `VITE_API_BASE_URL` | Browser API base URL; defaults to `/api` |
| `REACT_APP_PUBLIC_ORIGIN` | `VITE_PUBLIC_ORIGIN` | Canonical public origin |
| `REACT_APP_VAPID_PUBLIC_KEY` | `VITE_VAPID_PUBLIC_KEY` | Browser push public key |
| `REACT_APP_ANALYTICS_ENABLED` | `VITE_ANALYTICS_ENABLED` | Set to `false` to disable product analytics |

Server-only settings remain ordinary Node environment variables:

- `BACKEND_API_URL`
- `PUBLIC_ORIGIN`
- `SSR_TIMEOUT_MS`
- `PORT`
- `HOST`

## Tests

```bash
npm test
npm run test:coverage
npm run test:e2e
```

The Playwright command expects the production client and SSR bundles. Build them first with:

```bash
npm run build:e2e
```

## Production build

```bash
npm run build
```

This generates:

- `dist/client` — browser bundle and public assets
- `dist/server` — Node SSR bundle
- `sitemap.xml` — public discovery URLs

Run the production frontend server with:

```bash
BACKEND_API_URL=https://glideator-web.onrender.com \
PUBLIC_ORIGIN=https://www.parra-glideator.com \
npm run start:ssr
```

The server:

- serves Vite's hashed assets;
- proxies `/api` and `/mcp` to the backend;
- server-renders `/`, `/about`, and `/details/:siteId`;
- serves the client application shell for the remaining routes;
- exposes `/health` for Render health checks;
- falls back to the client application if SSR fails.

See `docs/frontend-ssr.md` for deployment and SSR details.
