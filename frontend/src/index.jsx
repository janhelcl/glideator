import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import './index.css';
import App from './App.jsx';
import reportWebVitals from './reportWebVitals';
import 'leaflet/dist/leaflet.css';
import { HelmetProvider } from 'react-helmet-async';
import { queryClient } from './queryClient';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <HelmetProvider>
        <App />
      </HelmetProvider>
    </QueryClientProvider>
  </React.StrictMode>
);

reportWebVitals();
