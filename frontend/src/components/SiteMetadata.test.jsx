import React from 'react';
import { cleanup, render, waitFor } from '@testing-library/react';
import { HelmetProvider } from 'react-helmet-async';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import SiteMetadata from './SiteMetadata';

const site = {
  site_id: 1,
  name: 'Raná',
  latitude: 50.4,
  longitude: 13.8,
  altitude: 457,
  predictions: [{
    date: '2026-08-03',
    values: [0.82, 0.76, 0.7, 0.64, 0.58, 0.52, 0.46, 0.4, 0.34, 0.28, 0.22],
  }],
};

const renderMetadata = (props = {}) => render(
  <HelmetProvider>
    <SiteMetadata
      siteId="1"
      site={site}
      siteInfo={{ site_name: 'Raná', country: 'Czechia' }}
      {...props}
    />
  </HelmetProvider>,
);

describe('SiteMetadata', () => {
  beforeEach(() => {
    document.head.innerHTML = '';
    window.history.replaceState({}, '', '/details/1');
  });

  afterEach(() => {
    cleanup();
    document.head.innerHTML = '';
  });

  it('uses human forecast wording while keeping canonical URLs stable', async () => {
    renderMetadata({ selectedDate: '2026-08-03', selectedMetric: 'XC20' });

    await waitFor(() => expect(document.title).toContain('70% chance of a 20+ point flight'));

    expect(document.title).not.toContain('XC20');
    expect(document.querySelector('link[rel="canonical"]')?.getAttribute('href'))
      .toBe(`${window.location.origin}/details/1`);
    expect(document.querySelector('meta[property="og:url"]')?.getAttribute('content'))
      .toBe(`${window.location.origin}/details/1`);
    expect(document.querySelector('meta[property="og:description"]')?.getAttribute('content'))
      .toContain('70% chance of a 20+ point flight at Raná');
    expect(document.querySelector('meta[property="og:image"]')?.getAttribute('content'))
      .toBe(`${window.location.origin}/logo512.png`);
  });

  it('describes the selected site section', async () => {
    renderMetadata({ selectedTab: 'season', selectedMetric: 'XC20' });

    await waitFor(() => expect(document.title).toBe('Raná flying season – Parra-Glideator'));
    expect(document.querySelector('meta[property="og:description"]')?.getAttribute('content'))
      .toContain('20+ point flights');
  });

  it('uses generic site metadata when no forecast date is selected', async () => {
    renderMetadata();

    await waitFor(() => expect(document.title).toBe('Raná – Parra-Glideator'));

    expect(document.querySelector('meta[property="og:url"]')?.getAttribute('content'))
      .toBe(`${window.location.origin}/details/1`);
    expect(document.querySelector('meta[property="og:description"]')?.getAttribute('content'))
      .toContain('Paragliding activity forecasts, seasonality and site information');
  });
});
