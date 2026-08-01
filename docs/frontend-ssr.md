# Frontend server rendering

The frontend uses Vite for both the browser bundle and the Node SSR bundle. The browser hydrates the same React components, so the interactive map, charts, authentication, favorites, notifications, styling, and routes remain the existing application after JavaScript loads.

## Why

Public routes contain useful HTML before JavaScript executes. In particular:

- `/` contains a semantic, screen-reader-only equivalent of the forecast map with normal links to site pages.
- `/details/:siteId` contains the site heading, seven-day forecast probabilities, seasonality, takeoff and landing information, validated local resources, selected-day weather drivers, and similar historical weather days.
- `/about` is rendered from the existing React page.

The semantic tables and lists are accessibility alternatives to visual maps, charts and collapsed panels. They contain the same planning information and are not selected by user agent.

Only the public information routes above use SSR. Trip Planner, login, registration, profile, favorites, notifications, feedback, and admin receive the client application shell and follow the existing client-side rendering path.

## Site-detail data strategy

A server-rendered site-detail request prefetches the public planning data in parallel and dehydrates it into the normal TanStack Query cache:

- predictions and optional site information;
- monthly flight statistics;
- takeoff and landing spots;
- validated resources, webcams and meteostations;
- the selected date's 09:00, 12:00 and 15:00 weather forecast;
- similar historical weather days for the selected date.

The semantic planning component reads those prefetched query keys with disabled queries. This is deliberate: hydration receives the complete SSR markup, while a normal client-side visit does not restore the eager requests removed by the frontend data-loading refactor. Interactive tabs continue to fetch their data only when opened and reuse any SSR cache entries already present.

Optional enrichment failures do not turn a valid forecast site into an error page. Only a missing predictions site produces an HTTP 404.

## Discovery contract

- `robots.txt` allows all public pages and keeps application APIs and MCP out of the crawl surface.
- `sitemap.xml` uses `https://www.parra-glideator.com` consistently and includes the homepage, About page, and every numeric site-detail page.
- sitemap generation reads the site list from the backend and fails the build rather than publishing an incomplete site directory.
- site-detail pages publish canonical URLs, Open Graph URLs, and Schema.org `Place` data.
- a missing numeric site returns HTTP 404 from SSR.
- SSR output does not vary by crawler user agent.

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

- `frontend/dist/client`: browser HTML, JavaScript, CSS, public assets, and the generated sitemap;
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
- `/details/1` exposes Raná forecast probabilities and forecast timestamps;
- site HTML also exposes monthly seasonality, takeoffs and landings, validated links, weather drivers and similar historical days;
- the two normal detail pages can be compared using XC0;
- site metadata is canonical and contains structured place data;
- `robots.txt` advertises the canonical sitemap;
- missing sites return HTTP 404;
- representative AI-search user agents receive the same public HTML;
- none of these flows request MCP.

A focused unit test also verifies that the planning component renders from prefetched cache data without starting browser requests. The JavaScript-enabled Playwright smoke tests continue to guard the normal human experience.
