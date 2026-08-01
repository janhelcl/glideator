import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { vi } from 'vitest';

import Details from './Details';
import {
  fetchFlightStats,
  fetchSiteForecast,
  fetchSiteInfo,
  fetchSitePredictions,
  fetchSiteResources,
} from '../api';

vi.mock('@mui/material', async () => {
  const actual = await vi.importActual('@mui/material');
  return {
    ...actual,
    useMediaQuery: () => false,
  };
});

vi.mock('../api', () => ({
  fetchFlightStats: vi.fn(),
  fetchSiteForecast: vi.fn(),
  fetchSiteInfo: vi.fn(),
  fetchSitePredictions: vi.fn(),
  fetchSiteResources: vi.fn(),
}));

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    isAuthenticated: false,
    toggleFavoriteSite: vi.fn(),
    isFavorite: vi.fn(() => false),
  }),
}));

vi.mock('../hooks/useDefaultMetric', () => ({
  useDefaultMetric: () => ({ preferredMetric: 'XC0' }),
}));

vi.mock('../components/GlideatorForecast', () => ({
  default: () => <div>Forecast summary</div>,
}));
vi.mock('../components/LoadingSpinner', () => ({
  default: () => <div>Loading</div>,
}));
vi.mock('../components/D3Forecast', () => ({
  default: () => <div>Atmospheric profile</div>,
}));
vi.mock('../components/FlightStatsChart', () => ({
  default: () => <div>Season chart</div>,
}));
vi.mock('../components/SearchRecs', () => ({
  default: () => <div>Search recommendations</div>,
}));
vi.mock('../components/SimilarDaysPanel', () => ({
  default: () => <div>Similar days</div>,
}));
vi.mock('../components/SiteMap', () => ({
  default: () => <div>Site map</div>,
}));

const renderDetails = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: Infinity,
      },
    },
  });

  render(
    <HelmetProvider>
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/details/1?date=2026-08-02&metric=XC0&tab=forecast']}>
          <Routes>
            <Route path="/details/:siteId" element={<Details />} />
            <Route path="/404" element={<div>Not found</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );

  return queryClient;
};

describe('Details data loading', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    fetchSitePredictions.mockResolvedValue([
      {
        site_id: 1,
        name: 'Raná',
        latitude: 50.404,
        longitude: 13.771,
        altitude: 457,
        tags: ['flats'],
        predictions: [
          {
            date: '2026-08-02',
            values: [0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05, 0.02, 0.01],
            computed_at: '2026-08-01T06:00:00',
            gfs_forecast_at: '2026-08-01T00:00:00',
          },
        ],
      },
    ]);
    fetchSiteInfo.mockResolvedValue({
      site_id: 1,
      site_name: 'Raná',
      country: 'Czechia',
      html: '<p>Site information</p>',
    });
    fetchSiteResources.mockResolvedValue({
      site_id: 1,
      local_resources: [],
      webcam_urls: [],
      meteostation_urls: [],
    });
    fetchFlightStats.mockResolvedValue({ 0: [1, 2, 3] });
    fetchSiteForecast.mockResolvedValue({
      date: '2026-08-02',
      computed_at: '2026-08-01T06:00:00',
      gfs_forecast_at: '2026-08-01T00:00:00',
      forecast_9: { wind_speed: 3 },
      forecast_12: { wind_speed: 4 },
      forecast_15: { wind_speed: 5 },
    });
  });

  it('loads expensive tab data only when the user opens it', async () => {
    const queryClient = renderDetails();

    expect(await screen.findByRole('heading', { name: 'Raná' })).toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'Glideator' })).toHaveAttribute('src', '/logo192.png');
    expect(fetchSitePredictions).toHaveBeenCalledTimes(1);
    expect(fetchSiteInfo).toHaveBeenCalledTimes(1);
    expect(fetchSiteForecast).not.toHaveBeenCalled();
    expect(fetchFlightStats).not.toHaveBeenCalled();
    expect(fetchSiteResources).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('tab', { name: /resources/i }));
    await waitFor(() => expect(fetchSiteResources).toHaveBeenCalledTimes(1));
    expect(fetchFlightStats).not.toHaveBeenCalled();
    expect(fetchSiteForecast).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('tab', { name: /season/i }));
    await waitFor(() => expect(fetchFlightStats).toHaveBeenCalledTimes(1));
    expect(fetchSiteForecast).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole('tab', { name: /activity forecast/i }));
    fireEvent.click(screen.getByRole('button', { name: /see what's driving this/i }));
    await waitFor(() => expect(fetchSiteForecast).toHaveBeenCalledTimes(1));

    const forecastCall = fetchSiteForecast.mock.calls[0];
    expect(forecastCall[0]).toBe('1');
    expect(forecastCall[1]).toBe('2026-08-02');
    expect(forecastCall[2].signal).toBeDefined();

    queryClient.clear();
  });
});
