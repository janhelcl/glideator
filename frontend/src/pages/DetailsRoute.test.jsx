import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import { fetchSiteInfo, fetchSitePredictions } from '../api';
import DetailsRoute from './DetailsRoute';

jest.mock('../api', () => ({
  fetchSiteInfo: jest.fn(),
  fetchSitePredictions: jest.fn(),
}));

jest.mock('../analytics', () => ({ trackEvent: jest.fn() }));
jest.mock('../components/AccessibleSiteForecast', () => () => null);
jest.mock('../components/QuickFeedback', () => () => null);
jest.mock('./Details', () => () => <div>Rendered site details</div>);

const renderRoute = (initialEntry) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/details/:siteId" element={<DetailsRoute />} />
          <Route path="/404" element={<div>Not found page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
};

describe('DetailsRoute', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('keeps a valid site page when optional site info is missing', async () => {
    fetchSitePredictions.mockResolvedValue([
      {
        site_id: 55,
        name: 'Stoderzinken',
        predictions: [],
      },
    ]);
    fetchSiteInfo.mockRejectedValue({
      response: {
        status: 404,
        data: { detail: 'Site info not found for site 55' },
      },
    });

    renderRoute('/details/55');

    expect(await screen.findByText('Rendered site details')).toBeInTheDocument();
    expect(screen.queryByText('Not found page')).not.toBeInTheDocument();
  });

  test('redirects when the predictions endpoint confirms the site is missing', async () => {
    fetchSitePredictions.mockRejectedValue({
      response: {
        status: 404,
        data: { detail: 'Site not found' },
      },
    });
    fetchSiteInfo.mockResolvedValue(null);

    renderRoute('/details/999999');

    expect(await screen.findByText('Not found page')).toBeInTheDocument();
  });
});
