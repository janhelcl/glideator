import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import SearchBar from '../SearchBar';
import apiClient from '../../api';

vi.mock('../../api', () => ({
  default: {
    get: vi.fn(),
  },
}));

vi.mock('../../context/AuthContext', () => {
  const stableFavorites = [2];

  return {
    useAuth: () => ({
      isAuthenticated: true,
      favorites: stableFavorites,
    }),
  };
});

const sites = [
  { site_id: 1, name: 'Bassano' },
  { site_id: 2, name: 'Raná' },
];

const renderSearchBar = () => render(
  <MemoryRouter>
    <SearchBar sites={sites} onSiteSelect={vi.fn()} />
  </MemoryRouter>,
);

describe('SearchBar', () => {
  beforeEach(() => {
    apiClient.get.mockReset();
  });

  it('uses the shared REST search endpoint after a short debounce', async () => {
    const user = userEvent.setup();
    apiClient.get.mockResolvedValue({ data: [{ site_id: 1, name: 'Bassano' }] });
    renderSearchBar();

    await user.type(screen.getByRole('combobox', { name: 'Search sites' }), 'Basano');

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledWith('/sites/search', expect.objectContaining({
        params: { query: 'Basano', limit: 10 },
      }));
    }, { timeout: 1000 });
  });

  it('does not call the search endpoint for an empty query', () => {
    renderSearchBar();
    expect(apiClient.get).not.toHaveBeenCalled();
  });
});
