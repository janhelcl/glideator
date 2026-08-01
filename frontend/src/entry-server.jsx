import React from 'react';
import { PassThrough } from 'stream';
import { renderToPipeableStream } from 'react-dom/server';
import { StaticRouter } from 'react-router-dom/server';
import {
  dehydrate,
  HydrationBoundary,
  QueryClientProvider,
} from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';

import api, { fetchSiteInfo, fetchSitePredictions, fetchSites } from './api';
import { AppContent, AppProviders } from './App.jsx';
import { createQueryClient } from './queryClient';

const PUBLIC_ORIGIN = process.env.PUBLIC_ORIGIN || 'https://www.parra-glideator.com';
const BACKEND_API_URL = process.env.BACKEND_API_URL || 'https://glideator-web.onrender.com';
const SSR_TIMEOUT_MS = Number(process.env.SSR_TIMEOUT_MS || 10000);

api.defaults.baseURL = BACKEND_API_URL;
api.defaults.withCredentials = false;

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

const isNotFoundError = (error) => error?.response?.status === 404;

const prefetchPageData = async (url, queryClient) => {
  if (url.pathname === '/') {
    await Promise.allSettled([
      queryClient.prefetchQuery({
        queryKey: ['sites', 'map'],
        queryFn: () => fetchSites(null, null, 1000),
      }),
    ]);
    return 200;
  }

  const detailMatch = url.pathname.match(/^\/details\/(\d+)\/?$/);
  if (!detailMatch) return 200;

  const siteId = detailMatch[1];
  const numericSiteId = Number(siteId);
  const [predictionsResult] = await Promise.allSettled([
    queryClient.fetchQuery({
      queryKey: ['site', numericSiteId, 'predictions'],
      queryFn: () => fetchSitePredictions(siteId),
    }),
    queryClient.prefetchQuery({
      queryKey: ['site', numericSiteId, 'info'],
      queryFn: async () => {
        try {
          return await fetchSiteInfo(siteId);
        } catch (error) {
          if (isNotFoundError(error)) return null;
          throw error;
        }
      },
    }),
  ]);

  if (predictionsResult.status === 'rejected' && isNotFoundError(predictionsResult.reason)) {
    return 404;
  }

  if (
    predictionsResult.status === 'fulfilled'
    && (!Array.isArray(predictionsResult.value) || predictionsResult.value.length === 0)
  ) {
    return 404;
  }

  return 200;
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

const renderPageInternal = async (requestUrl = '/') => {
  const url = new URL(requestUrl, PUBLIC_ORIGIN);
  const previousWindow = global.window;
  global.window = createServerWindow(url);

  const queryClient = createQueryClient();
  const helmetContext = {};

  try {
    const statusCode = await prefetchPageData(url, queryClient);
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
      statusCode,
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

let renderQueue = Promise.resolve();

export const renderPage = (requestUrl = '/') => {
  const currentRender = renderQueue.then(() => renderPageInternal(requestUrl));
  renderQueue = currentRender.catch(() => undefined);
  return currentRender;
};
