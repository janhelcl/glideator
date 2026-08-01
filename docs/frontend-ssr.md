# Frontend server rendering

The frontend keeps the existing Create React App browser bundle and adds a small Node server-rendering layer.
The browser hydrates the same React components, so the interactive map, charts, authentication, favorites,
notifications, styling, and routes remain the existing application after JavaScript loads.

## Why

Public routes now contain useful HTML before JavaScript executes. In particular:

- `/` contains a semantic, screen-reader-only equivalent of the forecast map with normal links to site pages.
- `/details/:siteId` contains the site heading and a semantic forecast table with dates, XC probabilities,
  forecast timestamps, site coordinates, and the decision-support caveat.
- `/about` is rendered from the existing React page.

The hidden tables are accessibility alternatives to visual maps and charts. They contain the same data and are
not selected by user agent.

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

The build still produces the normal CRA output in `frontend/build`. It additionally creates the server bundle in
`frontend/server-build`.

## Render configuration

The frontend must run as a Render **Web Service**, not a Static Site:

- Root directory: `frontend`
- Runtime: Node
- Build command: `npm ci && npm run build`
- Start command: `npm run start:ssr`
- Health check path: `/health`
- Environment:
  - `BACKEND_API_URL=https://glideator-web.onrender.com`
  - `PUBLIC_ORIGIN=https://www.parra-glideator.com`
  - the existing `REACT_APP_*` build variables

The Node server replaces the previous `_redirects` behavior for `/api` and `/mcp` and serves the hashed CRA
assets directly.

## Availability and rollback

SSR is fail-open. If page rendering fails, the server returns the original CRA `index.html`, allowing the browser
application to start as it did before this change.

A deployment can be rolled back to static hosting because `npm run build` continues to produce the same CRA
`build/` directory.

## Acceptance test

The Playwright crawler test disables JavaScript and verifies that `/details/1` exposes Raná forecast probabilities
and timestamps without requesting MCP, `llms.txt`, or the LLM-specific API.
