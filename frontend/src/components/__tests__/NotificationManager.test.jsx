import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import NotificationManager from '../NotificationManager';
import { useNotifications } from '../../context/NotificationContext';

jest.mock('../../api', () => ({
  fetchSitesList: jest.fn().mockResolvedValue([]),
}));

jest.mock('../../context/AuthContext', () => ({
  useAuth: () => ({ user: null, profile: null, favorites: [] }),
}));

jest.mock('../../context/NotificationContext', () => {
  const actual = jest.requireActual('../../context/NotificationContext');
  return {
    ...actual,
    useNotifications: jest.fn(),
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
      registerCurrentDevice: jest.fn(),
      deactivateSubscription: jest.fn(),
      createRule: jest.fn(),
      updateRule: jest.fn(),
      deleteRule: jest.fn(),
      loadNotificationEvents: jest.fn(),
      isLoading: false,
      error: null,
      clearError: jest.fn(),
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
