import React from 'react';
import { render, screen, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi } from 'vitest';

import {
  fetchFlightStats,
  fetchSimilarDays,
  fetchSiteForecast,
  fetchSiteResources,
  fetchSiteSpots,
} from '../api';
import AccessibleSitePlanningContext from './AccessibleSitePlanningContext';

vi.mock('../api', () => ({
  fetchFlightStats: vi.fn(),
  fetchSimilarDays: vi.fn(),
  fetchSiteForecast: vi.fn(),
  fetchSiteResources: vi.fn(),
  fetchSiteSpots: vi.fn(),
}));

const site = {
  site_id: 1,
  name: 'Raná',
  latitude: 50.403,
  longitude: 13.764,
  altitude: 457,
};

const selectedDate = '2026-08-02';

const renderFromCache = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: Infinity },
    },
  });

  queryClient.setQueryData(['site', 1, 'flight-stats'], {
    0: [0.2, 0.5, 2.1, 5.4],
  });
  queryClient.setQueryData(['site', 1, 'spots'], [
    {
      spot_id: 11,
      name: 'South launch',
      latitude: 50.403,
      longitude: 13.764,
      altitude: 457,
      type: 'takeoff',
      wind_direction: 'S-SW',
    },
    {
      spot_id: 12,
      name: 'Main landing',
      latitude: 50.393,
      longitude: 13.774,
      altitude: 337,
      type: 'landing',
    },
  ]);
  queryClient.setQueryData(['site', 1, 'resources'], {
    run_extracted_at: '2026-08-01T12:00:00Z',
    local_resources: [
      {
        candidate_id: 101,
        name: 'Raná flying club',
        url: 'https://example.com/club',
      },
    ],
    webcam_urls: ['https://example.com/webcam'],
    meteostation_urls: [],
  });
  queryClient.setQueryData(['site', 1, 'forecast', selectedDate], {
    computed_at: '2026-08-01T09:30:00Z',
    gfs_forecast_at: '2026-08-01T06:00:00Z',
    forecast_9: {
      temperature_2m_c: 16,
      dewpoint_2m_c: 8,
      wind_speed_10m_ms: 3.5,
      wind_direction_10m_dgr: 220,
      wind_gust_sfc_ms: 6.2,
      pressure_sfc_pa: 101200,
    },
    forecast_12: {
      temperature_2m_c: 19,
      dewpoint_2m_c: 9,
      wind_speed_10m_ms: 4,
      wind_direction_10m_dgr: 230,
      wind_gust_sfc_ms: 7.1,
      pressure_sfc_pa: 101100,
    },
    forecast_15: {},
  });
  queryClient.setQueryData(['site', 1, 'similar-days', selectedDate], {
    similar_days: [{ past_date: '2025-07-15', similarity: 0.91 }],
  });

  render(
    <QueryClientProvider client={queryClient}>
      <AccessibleSitePlanningContext
        siteId="1"
        site={site}
        siteName="Raná"
        selectedDate={selectedDate}
        selectedMetric="XC0"
      />
    </QueryClientProvider>,
  );

  return queryClient;
};

describe('AccessibleSitePlanningContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the SSR-prefetched planning context without starting browser requests', () => {
    const queryClient = renderFromCache();

    const context = screen.getByRole('region', { name: 'Raná planning context' });
    const seasonality = within(context).getByRole('table', {
      name: 'Raná monthly XC0 seasonality',
    });
    expect(within(seasonality).getByText('April')).toBeInTheDocument();
    expect(within(seasonality).getByText('5.4 days')).toBeInTheDocument();

    expect(within(context).getByText(/South launch/)).toHaveTextContent('suitable wind S-SW');
    expect(within(context).getByText(/Main landing/)).toBeInTheDocument();
    expect(within(context).getByRole('link', { name: 'Raná flying club' })).toHaveAttribute(
      'href',
      'https://example.com/club',
    );

    const weather = within(context).getByRole('table', {
      name: `Raná weather drivers for ${selectedDate}`,
    });
    expect(within(weather).getByText('4.0 m/s at 230°')).toBeInTheDocument();
    expect(within(context).getByText(/2025-07-15, similarity 91%/)).toBeInTheDocument();

    expect(fetchFlightStats).not.toHaveBeenCalled();
    expect(fetchSiteSpots).not.toHaveBeenCalled();
    expect(fetchSiteResources).not.toHaveBeenCalled();
    expect(fetchSiteForecast).not.toHaveBeenCalled();
    expect(fetchSimilarDays).not.toHaveBeenCalled();

    queryClient.clear();
  });
});
