# Frontend server rendering

The frontend uses Vite for both the browser bundle and the Node SSR bundle. The browser hydrates the same React components, so the interactive map, charts, authentication, favorites, notifications, styling, and routes remain the existing application after JavaScript loads.

## Why

Public routes contain useful HTML before JavaScript executes. In particular:

- `/` contains a semantic, screen-reader-only equivalent of the forecast map with normal links to site pages.
- `/details/:siteId` contains the site heading and a semantic forecast table with dates, XC probabilities, forecast timestamps, site coordinates, and the decision-support caveat.
- `/about` is rendered from the existing React page.

The hidden tables are accessibility alternatives to visual maps and charts. They contain the same data and are not selected by user agent.

Only the public information routes above use SSR. Trip Planner, login, registration, profile, favorites, notifications, feedback, and admin receive the client application shell and follow the existing client-side rendering path.

## Development

```bash
cd frontend
npm ci
npm start
```

Vite serves the application on port 3000 with hot-module replacement. Existing `REACT_APP_*` variables remain supported during the migration; equivalent `VITE_*` variables can also be used.

## Build and run

```bash
cd frontend
npm ci
npm run build
BACKEND_API_URL=https://glideator-web.onrender.com \
PUBLIC_ORIGIN=https://www.parra-glideator.com \
PORT=3000 \
npm run start:ssr
```

The build creates:

- `frontend/dist/client`: browser HTML, JavaScript, CSS, and public assets;
- `frontend/dist/server`: the Vite SSR entry and its server-side chunks.

## Render configuration

The frontend runs as a Render **Web Service**, not a Static Site:

- Root directory: `frontend`
- Runtime: Node 22
- Build command: `npm ci && npm run build`
- Start command: `npm run start:ssr`
- Health check path: `/health`
- Environment:
  - `BACKEND_API_URL=https://glideator-web.onrender.com`
  - `PUBLIC_ORIGIN=https://www.parra-glideator.com`
  - the existing `REACT_APP_*` build variables, or their `VITE_*` equivalents

The Node server proxies `/api` and `/mcp` and serves Vite's hashed assets directly.

## Availability and rollback

SSR is fail-open. If page rendering fails, the server returns the Vite client `index.html`, allowing the browser application to start normally.

Rollback is performed by deploying an earlier Render build or reverting the migration commit. The Vite and CRA output directories are different, so a static-hosting rollback requires the corresponding earlier code and build configuration.

## Acceptance test

The Playwright crawler tests disable JavaScript and verify that:

- the homepage exposes a ranked comparison of Raná and Kozákov with normal links to their detail pages;
- `/details/1` exposes Raná forecast probabilities and timestamps;
- the two normal detail pages can be compared using XC0;
- none of these flows request MCP, `llms.txt`, or the LLM-specific API.

The JavaScript-enabled Playwright smoke tests run against the hydrated application to guard the normal human experience.
