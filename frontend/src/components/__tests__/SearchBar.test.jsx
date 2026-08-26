import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import SearchBar from '../SearchBar';
import apiClient from '../../api';

vi.mock('../../api', () => ({
  default: {
    get: vi.fn(),
  },
}));

vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({
    isAuthenticated: true,
    favorites: [2],
  }),
}));

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
    apiClient.get.mockResolvedValue({ data: [{ site_id: 1, name: 'Bassano' }] });
    renderSearchBar();

    fireEvent.change(screen.getByLabelText('Search sites'), {
      target: { value: 'Basano' },
    });

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
