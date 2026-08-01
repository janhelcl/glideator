const React = require('react');
const { PassThrough } = require('stream');
const { renderToPipeableStream } = require('react-dom/server');
const { StaticRouter } = require('react-router-dom/server');
const {
  dehydrate,
  HydrationBoundary,
  QueryClientProvider,
} = require('@tanstack/react-query');
const { HelmetProvider } = require('react-helmet-async');

const api = require('./api');
const { AppContent, AppProviders } = require('./App.jsx');
const { createQueryClient } = require('./queryClient');

const PUBLIC_ORIGIN = process.env.PUBLIC_ORIGIN || 'https://www.parra-glideator.com';
const BACKEND_API_URL = process.env.BACKEND_API_URL || 'https://glideator-web.onrender.com';
const SSR_TIMEOUT_MS = Number(process.env.SSR_TIMEOUT_MS || 10000);

api.default.defaults.baseURL = BACKEND_API_URL;
api.default.defaults.withCredentials = false;

const createServerWindow = (url) => ({
  location: {
    origin: PUBLIC_ORIGIN,
    href: `${PUBLIC_ORIGIN}${url.pathname}${url.search}`,
    pathname: url.pathname,
    search: url.search,
  },
  matchMedia: () => ({
    matches: false,
    media: '',
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
  addEventListener: () => {},
  removeEventListener: () => {},
  requestAnimationFrame: (callback) => setTimeout(callback, 0),
  cancelAnimationFrame: (id) => clearTimeout(id),
});

const renderReactTree = (element) => new Promise((resolve, reject) => {
  let settled = false;
  let timeoutId;

  const stream = renderToPipeableStream(element, {
    onAllReady() {
      if (settled) return;
      const output = new PassThrough();
      let html = '';

      output.setEncoding('utf8');
      output.on('data', (chunk) => {
        html += chunk;
      });
      output.on('end', () => {
        settled = true;
        clearTimeout(timeoutId);
        resolve(html);
      });
      output.on('error', (error) => {
        settled = true;
        clearTimeout(timeoutId);
        reject(error);
      });

      stream.pipe(output);
    },
    onShellError(error) {
      if (!settled) {
        settled = true;
        clearTimeout(timeoutId);
        reject(error);
      }
    },
    onError(error) {
      console.error('SSR render error:', error);
    },
  });

  timeoutId = setTimeout(() => {
    if (!settled) {
      settled = true;
      stream.abort();
      reject(new Error(`SSR render exceeded ${SSR_TIMEOUT_MS}ms`));
    }
  }, SSR_TIMEOUT_MS);
});

const prefetchPageData = async (url, queryClient) => {
  const tasks = [];

  if (url.pathname === '/') {
    tasks.push(queryClient.prefetchQuery({
      queryKey: ['sites', 'map'],
      queryFn: () => api.fetchSites(null, null, 1000),
    }));
  }

  const detailMatch = url.pathname.match(/^\/details\/(\d+)\/?$/);
  if (detailMatch) {
    const siteId = detailMatch[1];
    const numericSiteId = Number(siteId);
    tasks.push(
      queryClient.prefetchQuery({
        queryKey: ['site', numericSiteId, 'predictions'],
        queryFn: () => api.fetchSitePredictions(siteId),
      }),
      queryClient.prefetchQuery({
        queryKey: ['site', numericSiteId, 'info'],
        queryFn: () => api.fetchSiteInfo(siteId),
      }),
    );
  }

  await Promise.allSettled(tasks);
};

const helmetToString = (helmet) => {
  if (!helmet) return '';
  return [
    helmet.title?.toString(),
    helmet.priority?.toString(),
    helmet.meta?.toString(),
    helmet.link?.toString(),
    helmet.script?.toString(),
  ].filter(Boolean).join('');
};

const renderPage = async (requestUrl = '/') => {
  const url = new URL(requestUrl, PUBLIC_ORIGIN);
  const previousWindow = global.window;
  global.window = createServerWindow(url);

  const queryClient = createQueryClient();
  const helmetContext = {};

  try {
    await prefetchPageData(url, queryClient);
    const dehydratedState = dehydrate(queryClient);

    const application = (
      <StaticRouter location={`${url.pathname}${url.search}`}>
        <QueryClientProvider client={queryClient}>
          <HydrationBoundary state={dehydratedState}>
            <HelmetProvider context={helmetContext}>
              <AppProviders>
                <AppContent />
              </AppProviders>
            </HelmetProvider>
          </HydrationBoundary>
        </QueryClientProvider>
      </StaticRouter>
    );

    const html = await renderReactTree(application);

    return {
      html,
      dehydratedState,
      head: helmetToString(helmetContext.helmet),
      statusCode: 200,
    };
  } finally {
    queryClient.clear();
    if (previousWindow === undefined) {
      delete global.window;
    } else {
      global.window = previousWindow;
    }
  }
};

module.exports = { renderPage };
