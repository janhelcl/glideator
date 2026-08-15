'use strict';

const fs = require('fs');
const fsp = require('fs/promises');
const http = require('http');
const https = require('https');
const path = require('path');
const { pathToFileURL } = require('url');

const PORT = Number(process.env.PORT || 3000);
const HOST = process.env.HOST || '0.0.0.0';
const BACKEND_API_URL = process.env.BACKEND_API_URL || 'https://glideator-web.onrender.com';
const BUILD_DIR = path.resolve(__dirname, '../dist/client');
const INDEX_PATH = path.join(BUILD_DIR, 'index.html');
const SERVER_ENTRY_PATH = path.resolve(__dirname, '../dist/server/entry-server.mjs');

const MIME_TYPES = {
  '.css': 'text/css; charset=utf-8',
  '.gif': 'image/gif',
  '.html': 'text/html; charset=utf-8',
  '.ico': 'image/x-icon',
  '.jpeg': 'image/jpeg',
  '.jpg': 'image/jpeg',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.map': 'application/json; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8',
  '.webmanifest': 'application/manifest+json',
  '.webp': 'image/webp',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.xml': 'application/xml; charset=utf-8',
};

let indexTemplatePromise;
const getIndexTemplate = () => {
  if (!indexTemplatePromise) {
    indexTemplatePromise = fsp.readFile(INDEX_PATH, 'utf8');
  }
  return indexTemplatePromise;
};

let renderPagePromise;
const getRenderPage = () => {
  if (!renderPagePromise) {
    renderPagePromise = import(pathToFileURL(SERVER_ENTRY_PATH).href)
      .then((module) => module.renderPage)
      .catch((error) => {
        renderPagePromise = null;
        throw error;
      });
  }
  return renderPagePromise;
};

const serializeState = (value) => JSON.stringify(value)
  .replace(/</g, '\\u003c')
  .replace(/>/g, '\\u003e')
  .replace(/&/g, '\\u0026')
  .replace(/\u2028/g, '\\u2028')
  .replace(/\u2029/g, '\\u2029');

const injectSsrMarkup = (template, { html, dehydratedState, head }) => {
  let document = template;

  if (head.includes('<title')) {
    document = document.replace(/<title>[\s\S]*?<\/title>/i, '');
  }
  document = document.replace('</head>', `${head}</head>`);

  const rootMarkup = `<div id="root">${html}</div>`;
  if (document.includes('<div id="root"></div>')) {
    document = document.replace('<div id="root"></div>', rootMarkup);
  } else {
    document = document.replace(/<div id="root"\s*><\/div>/i, rootMarkup);
  }

  const stateScript = `<script>window.__REACT_QUERY_STATE__=${serializeState(dehydratedState)};</script>`;
  document = document.replace(rootMarkup, `${rootMarkup}${stateScript}`);
  return document;
};

const safeStaticPath = (pathname) => {
  let decoded;
  try {
    decoded = decodeURIComponent(pathname);
  } catch {
    return null;
  }

  const resolved = path.resolve(BUILD_DIR, `.${decoded}`);
  if (resolved !== BUILD_DIR && !resolved.startsWith(`${BUILD_DIR}${path.sep}`)) {
    return null;
  }
  return resolved;
};

const serveStaticFile = async (request, response, pathname) => {
  const filePath = safeStaticPath(pathname);
  if (!filePath) return false;

  let stat;
  try {
    stat = await fsp.stat(filePath);
  } catch {
    return false;
  }

  if (!stat.isFile()) return false;

  const extension = path.extname(filePath).toLowerCase();
  response.statusCode = 200;
  response.setHeader('Content-Type', MIME_TYPES[extension] || 'application/octet-stream');
  response.setHeader(
    'Cache-Control',
    pathname.startsWith('/assets/')
      ? 'public, max-age=31536000, immutable'
      : 'public, max-age=300',
  );

  if (request.method === 'HEAD') {
    response.end();
  } else {
    fs.createReadStream(filePath).pipe(response);
  }
  return true;
};

const proxyRequest = (request, response, { stripApiPrefix = false } = {}) => {
  const backend = new URL(BACKEND_API_URL);
  const incoming = new URL(request.url, `http://${request.headers.host || 'localhost'}`);
  let pathname = incoming.pathname;

  if (stripApiPrefix) {
    pathname = pathname.replace(/^\/api(?=\/|$)/, '') || '/';
  }

  const transport = backend.protocol === 'http:' ? http : https;
  const headers = {
    ...request.headers,
    host: backend.host,
    'x-forwarded-host': request.headers.host || '',
    'x-forwarded-proto': request.socket.encrypted ? 'https' : 'http',
  };

  const upstream = transport.request({
    protocol: backend.protocol,
    hostname: backend.hostname,
    port: backend.port || undefined,
    method: request.method,
    path: `${backend.pathname.replace(/\/$/, '')}${pathname}${incoming.search}`,
    headers,
  }, (upstreamResponse) => {
    response.writeHead(upstreamResponse.statusCode || 502, upstreamResponse.headers);
    upstreamResponse.pipe(response);
  });

  upstream.on('error', (error) => {
    console.error('Backend proxy error:', error);
    if (!response.headersSent) {
      response.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
    }
    response.end(JSON.stringify({ detail: 'Backend unavailable' }));
  });

  request.pipe(upstream);
};

const shouldServerRender = (pathname) => (
  pathname === '/'
  || pathname === '/about'
  || pathname === '/privacy'
  || pathname === '/terms'
  || pathname === '/support'
  || /^\/details\/\d+\/?$/.test(pathname)
);

const sendClientApplication = async (request, response) => {
  const template = await getIndexTemplate();
  response.writeHead(200, {
    'Content-Type': 'text/html; charset=utf-8',
    'Cache-Control': 'no-cache',
    'X-Content-Type-Options': 'nosniff',
  });
  response.end(request.method === 'HEAD' ? undefined : template);
};

const serveOpenAIAppsChallenge = (request, response) => {
  const token = process.env.OPENAI_APPS_CHALLENGE_TOKEN?.trim();
  if (!token) {
    response.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
    response.end('Not configured');
    return;
  }

  response.writeHead(200, {
    'Content-Type': 'text/plain; charset=utf-8',
    'Cache-Control': 'no-store',
    'X-Content-Type-Options': 'nosniff',
  });
  response.end(request.method === 'HEAD' ? undefined : token);
};

const server = http.createServer(async (request, response) => {
  const requestUrl = new URL(request.url, `http://${request.headers.host || 'localhost'}`);
  const { pathname } = requestUrl;

  if (pathname === '/health') {
    response.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
    response.end(JSON.stringify({ status: 'ok' }));
    return;
  }

  if (
    pathname === '/.well-known/openai-apps-challenge'
    && (request.method === 'GET' || request.method === 'HEAD')
  ) {
    serveOpenAIAppsChallenge(request, response);
    return;
  }

  if (pathname === '/api' || pathname.startsWith('/api/')) {
    proxyRequest(request, response, { stripApiPrefix: true });
    return;
  }

  if (pathname === '/mcp' || pathname.startsWith('/mcp/')) {
    proxyRequest(request, response);
    return;
  }

  if (request.method === 'GET' || request.method === 'HEAD') {
    if (await serveStaticFile(request, response, pathname)) return;

    if (!shouldServerRender(pathname)) {
      await sendClientApplication(request, response);
      return;
    }

    try {
      const template = await getIndexTemplate();
      const renderPage = await getRenderPage();
      const rendered = await renderPage(`${pathname}${requestUrl.search}`);
      const document = injectSsrMarkup(template, rendered);

      response.statusCode = rendered.statusCode;
      response.setHeader('Content-Type', 'text/html; charset=utf-8');
      response.setHeader('Cache-Control', 'public, max-age=300, stale-while-revalidate=600');
      response.setHeader('X-Content-Type-Options', 'nosniff');

      if (request.method === 'HEAD') {
        response.end();
      } else {
        response.end(document);
      }
    } catch (error) {
      console.error(`SSR failed for ${request.url}; serving the client application:`, error);
      await sendClientApplication(request, response);
    }
    return;
  }

  response.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' });
  response.end(JSON.stringify({ detail: 'Not found' }));
});

server.listen(PORT, HOST, () => {
  console.log(`Glideator SSR frontend listening on http://${HOST}:${PORT}`);
});

module.exports = {
  injectSsrMarkup,
  serializeState,
  server,
  serveOpenAIAppsChallenge,
};
