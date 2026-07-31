import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import Details from './Details';
import {
  fetchFlightStats,
  fetchSiteForecast,
  fetchSiteInfo,
  fetchSitePredictions,
  fetchSiteResources,
} from '../api';

jest.mock('@mui/material', () => ({
  ...jest.requireActual('@mui/material'),
  useMediaQuery: () => false,
}));

jest.mock('../api', () => ({
  fetchFlightStats: jest.fn(),
  fetchSiteForecast: jest.fn(),
  fetchSiteInfo: jest.fn(),
  fetchSitePredictions: jest.fn(),
  fetchSiteResources: jest.fn(),
}));

jest.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    isAuthenticated: false,
    toggleFavoriteSite: jest.fn(),
    isFavorite: jest.fn(() => false),
  }),
}));

jest.mock('../hooks/useDefaultMetric', () => ({
  useDefaultMetric: () => ({ preferredMetric: 'XC0' }),
}));

jest.mock('../components/GlideatorForecast', () => () => <div>Forecast summary</div>);
jest.mock('../components/LoadingSpinner', () => () => <div>Loading</div>);
jest.mock('../components/D3Forecast', () => ({
  __esModule: true,
  default: () => <div>Atmospheric profile</div>,
}));
jest.mock('../components/FlightStatsChart', () => ({
  __esModule: true,
  default: () => <div>Season chart</div>,
}));
jest.mock('../components/SearchRecs', () => ({
  __esModule: true,
  default: () => <div>Search recommendations</div>,
}));
jest.mock('../components/SimilarDaysPanel', () => ({
  __esModule: true,
  default: () => <div>Similar days</div>,
}));
jest.mock('../components/SiteMap', () => ({
  __esModule: true,
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
    jest.clearAllMocks();

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
