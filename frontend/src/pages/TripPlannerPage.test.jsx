import React from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HelmetProvider } from 'react-helmet-async';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import TripPlannerPage from './TripPlannerPage';
import { planTrip } from '../api';

jest.mock('../api', () => ({
  planTrip: jest.fn(),
}));

jest.mock('../hooks/useDefaultMetric', () => ({
  useDefaultMetric: () => ({ preferredMetric: 'XC0' }),
}));

jest.mock('../context/AuthContext', () => ({
  useAuth: () => ({
    profile: {
      home_lat: 50.1,
      home_lon: 14.4,
    },
  }),
}));

jest.mock('../components/TripPlannerControls', () => {
  const React = require('react');

  return function MockTripPlannerControls({ setState, onSubmit }) {
    return React.createElement(
      'div',
      null,
      React.createElement(
        'button',
        {
          type: 'button',
          onClick: () => setState((previous) => ({
            ...previous,
            selectedMetric: 'XC50',
            flightQuality: {
              ...previous.flightQuality,
              enabled: true,
              selectedValues: ['XC0', 'XC10', 'XC20', 'XC30', 'XC40', 'XC50'],
            },
            altitude: {
              enabled: true,
              min: 800,
              max: 1600,
            },
            tags: ['ridge'],
          })),
        },
        'Apply filters',
      ),
      React.createElement(
        'button',
        {
          type: 'button',
          onClick: () => onSubmit([
            new Date('2000-01-02T12:00:00Z'),
            new Date('2000-01-01T12:00:00Z'),
          ]),
        },
        'Submit invalid dates',
      ),
    );
  };
});

jest.mock('../components/SiteList', () => {
  const React = require('react');

  return function MockSiteList({ sites, onSiteClick }) {
    return React.createElement(
      'div',
      { 'data-testid': 'site-list' },
      sites.map((site) => React.createElement(
        'button',
        {
          type: 'button',
          key: site.site_id,
          onClick: (event) => onSiteClick(site, event),
        },
        site.site_name,
      )),
    );
  };
});

jest.mock('../components/PlannerMapView', () => {
  const React = require('react');
  return function MockPlannerMapView({ sites }) {
    return React.createElement('div', null, `Map with ${sites.length} sites`);
  };
});

jest.mock('../components/LoadingSpinner', () => {
  const React = require('react');
  return function MockLoadingSpinner() {
    return React.createElement('div', null, 'Loading planner');
  };
});

const dateString = (daysFromToday) => {
  const value = new Date();
  value.setHours(12, 0, 0, 0);
  value.setDate(value.getDate() + daysFromToday);
  return value.toISOString().split('T')[0];
};

const makeSite = (siteId, overrides = {}) => ({
  site_id: String(siteId),
  site_name: `Site ${siteId}`,
  latitude: 50 + siteId / 100,
  longitude: 14 + siteId / 100,
  altitude: 500 + siteId,
  average_flyability: 1 - siteId / 100,
  daily_probabilities: [],
  distance_km: siteId,
  ...overrides,
});

const makePage = (sites, totalCount = sites.length, hasMore = false) => ({
  sites,
  total_count: totalCount,
  has_more: hasMore,
});

const renderPlanner = (query = '') => {
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
        <MemoryRouter initialEntries={[`/trip-planner${query}`]}>
          <Routes>
            <Route path="/trip-planner" element={<TripPlannerPage />} />
            <Route path="/details/:siteId" element={<div>Details page</div>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </HelmetProvider>,
  );

  return queryClient;
};

const deferred = () => {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
};

describe('TripPlannerPage', () => {
  beforeAll(() => {
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      writable: true,
      value: jest.fn().mockImplementation((query) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(),
      })),
    });
  });

  beforeEach(() => {
    jest.clearAllMocks();
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: {
        getCurrentPosition: jest.fn(),
      },
    });
  });

  it('restores URL filters and uses the saved home location', async () => {
    const startDate = dateString(1);
    const endDate = dateString(3);
    planTrip.mockResolvedValue(makePage([makeSite(1)]));

    renderPlanner(
      `?startDate=${startDate}`
      + `&endDate=${endDate}`
      + '&metric=XC20'
      + '&distEnabled=true'
      + '&distKm=120'
      + '&locSrc=home'
      + '&altMin=500'
      + '&altMax=1800'
      + '&tags=official,alps',
    );

    await waitFor(() => expect(planTrip).toHaveBeenCalled());
    const call = planTrip.mock.calls.at(-1);

    expect(call[0]).toBe(startDate);
    expect(call[1]).toBe(endDate);
    expect(call[2]).toBe('XC20');
    expect(call[3]).toEqual({ latitude: 50.1, longitude: 14.4 });
    expect(call[4]).toBe(120);
    expect(call[5]).toEqual({ min: 500, max: 1800 });
    expect(call[6]).toBe(0);
    expect(call[7]).toBe(10);
    expect(call[8]).toEqual(['alps', 'official']);
    expect(call[9].signal).toBeDefined();
    expect(await screen.findByText('Site 1')).toBeInTheDocument();
  });

  it('requests the next offset, appends results, and can collapse them again', async () => {
    const startDate = dateString(1);
    const endDate = dateString(2);
    planTrip.mockImplementation((...args) => {
      const offset = args[6];
      if (offset === 0) {
        return Promise.resolve(makePage(
          Array.from({ length: 10 }, (_, index) => makeSite(index + 1)),
          15,
          true,
        ));
      }
      return Promise.resolve(makePage(
        Array.from({ length: 5 }, (_, index) => makeSite(index + 11)),
        15,
        false,
      ));
    });

    renderPlanner(`?startDate=${startDate}&endDate=${endDate}`);

    expect(await screen.findByText('Top 10 sites (15 total)')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'More' }));

    expect(await screen.findByText('Site 15')).toBeInTheDocument();
    expect(planTrip.mock.calls.map((call) => call[6])).toEqual([0, 10]);
    expect(screen.getByText('Top 15 sites (15 total)')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Less' }));
    await waitFor(() => expect(screen.queryByText('Site 11')).not.toBeInTheDocument());
    expect(screen.getByText('Top 10 sites (15 total)')).toBeInTheDocument();
  });

  it('aborts an obsolete request when filters change and keeps the new result', async () => {
    const startDate = dateString(1);
    const endDate = dateString(2);
    const firstRequest = deferred();
    planTrip
      .mockImplementationOnce(() => firstRequest.promise)
      .mockResolvedValueOnce(makePage([
        makeSite(50, { site_name: 'Filtered Site', average_flyability: 0.95 }),
      ]));

    renderPlanner(`?startDate=${startDate}&endDate=${endDate}`);

    await waitFor(() => expect(planTrip).toHaveBeenCalledTimes(1));
    const firstSignal = planTrip.mock.calls[0][9].signal;

    fireEvent.click(screen.getByRole('button', { name: 'Apply filters' }));

    await waitFor(() => expect(planTrip).toHaveBeenCalledTimes(2));
    expect(planTrip.mock.calls[1][2]).toBe('XC50');
    expect(planTrip.mock.calls[1][5]).toEqual({ min: 800, max: 1600 });
    expect(planTrip.mock.calls[1][8]).toEqual(['ridge']);
    await waitFor(() => expect(firstSignal.aborted).toBe(true));
    expect(await screen.findByText('Filtered Site')).toBeInTheDocument();

    await act(async () => {
      firstRequest.resolve(makePage([
        makeSite(1, { site_name: 'Obsolete Site' }),
      ]));
      await firstRequest.promise;
    });

    expect(screen.queryByText('Obsolete Site')).not.toBeInTheDocument();
    expect(screen.getByText('Filtered Site')).toBeInTheDocument();
  });

  it('rejects an invalid submitted date range without another API request', async () => {
    const startDate = dateString(1);
    const endDate = dateString(2);
    planTrip.mockResolvedValue(makePage([makeSite(1)]));

    renderPlanner(`?startDate=${startDate}&endDate=${endDate}`);
    await waitFor(() => expect(planTrip).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole('button', { name: 'Submit invalid dates' }));

    expect(await screen.findByText('End date cannot be before start date')).toBeInTheDocument();
    await new Promise((resolve) => setTimeout(resolve, 300));
    expect(planTrip).toHaveBeenCalledTimes(1);
  });

  it('shows a useful empty-result message', async () => {
    const startDate = dateString(1);
    const endDate = dateString(2);
    planTrip.mockResolvedValue(makePage([], 0, false));

    renderPlanner(`?startDate=${startDate}&endDate=${endDate}`);

    expect(
      await screen.findByText('No suitable sites found for the selected criteria'),
    ).toBeInTheDocument();
  });

  it('shows a useful API failure message', async () => {
    const startDate = dateString(1);
    const endDate = dateString(2);
    planTrip.mockRejectedValue(new Error('network failure'));

    renderPlanner(`?startDate=${startDate}&endDate=${endDate}`);

    expect(
      await screen.findByText('Failed to plan trip. Please try again.'),
    ).toBeInTheDocument();
  });
});
