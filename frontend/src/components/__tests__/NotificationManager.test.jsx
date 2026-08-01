import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';

import NotificationManager from '../NotificationManager';
import { useNotifications } from '../../context/NotificationContext';

vi.mock('../../api', () => ({
  fetchSitesList: vi.fn().mockResolvedValue([]),
}));

vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({ user: null, profile: null, favorites: [] }),
}));

vi.mock('../../context/NotificationContext', async () => {
  const actual = await vi.importActual('../../context/NotificationContext');
  return {
    ...actual,
    useNotifications: vi.fn(),
  };
});

describe('NotificationManager', () => {
  beforeEach(() => {
    useNotifications.mockReset();
  });

  it('shows warning when push is not supported', () => {
    useNotifications.mockReturnValue({
      pushSupported: false,
      permission: 'default',
      subscriptions: [],
      notifications: [],
      eventsByNotification: {},
      registerCurrentDevice: vi.fn(),
      deactivateSubscription: vi.fn(),
      createRule: vi.fn(),
      updateRule: vi.fn(),
      deleteRule: vi.fn(),
      loadNotificationEvents: vi.fn(),
      isLoading: false,
      error: null,
      clearError: vi.fn(),
    });

    render(
      <MemoryRouter>
        <NotificationManager />
      </MemoryRouter>,
    );

    expect(
      screen.getByText(/push notifications are not supported in this browser/i),
    ).toBeInTheDocument();
  });
});
