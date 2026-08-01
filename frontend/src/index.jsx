import React from 'react';
import { createRoot, hydrateRoot } from 'react-dom/client';
import { HydrationBoundary, QueryClientProvider } from '@tanstack/react-query';
import './index.css';
import App from './App.jsx';
import reportWebVitals from './reportWebVitals';
import 'leaflet/dist/leaflet.css';
import { HelmetProvider } from 'react-helmet-async';
import { queryClient } from './queryClient';

const rootElement = document.getElementById('root');
const dehydratedState = window.__REACT_QUERY_STATE__ || undefined;

const application = (
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <HydrationBoundary state={dehydratedState}>
        <HelmetProvider>
          <App />
        </HelmetProvider>
      </HydrationBoundary>
    </QueryClientProvider>
  </React.StrictMode>
);

if (rootElement.hasChildNodes()) {
  hydrateRoot(rootElement, application);
} else {
  createRoot(rootElement).render(application);
}

reportWebVitals();
