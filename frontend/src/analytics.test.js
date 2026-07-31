import apiClient from './api';
import { analyticsEnabled, resetAnalyticsIdsForTests, trackEvent } from './analytics';

jest.mock('./api', () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
  },
}));

describe('product analytics', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    resetAnalyticsIdsForTests();
    process.env.REACT_APP_ANALYTICS_ENABLED = 'true';
    Object.defineProperty(navigator, 'doNotTrack', {
      configurable: true,
      value: null,
    });
    Object.defineProperty(navigator, 'globalPrivacyControl', {
      configurable: true,
      value: false,
    });
    window.history.pushState({}, '', '/details/42?lat=50.1234&lng=14.4321');
    apiClient.post.mockResolvedValue({ data: { accepted: true } });
  });

  it('stores only the pathname and removes sensitive property keys', async () => {
    await trackEvent('site_detail_viewed', {
      metric: 'XC20',
      email: 'pilot@example.com',
      latitude: 50.1234,
      nested: {
        coords: [50.1234, 14.4321],
        source: 'map',
      },
    });

    expect(apiClient.post).toHaveBeenCalledTimes(1);
    const [url, payload] = apiClient.post.mock.calls[0];

    expect(url).toBe('/analytics/events');
    expect(payload.path).toBe('/details/42');
    expect(payload.anonymous_id).toMatch(/^anon-/);
    expect(payload.session_id).toMatch(/^session-/);
    expect(payload.properties).toEqual({
      metric: 'XC20',
      nested: { source: 'map' },
    });
  });

  it('respects browser privacy signals', async () => {
    Object.defineProperty(navigator, 'doNotTrack', {
      configurable: true,
      value: '1',
    });

    expect(analyticsEnabled()).toBe(false);
    await trackEvent('page_view');

    expect(apiClient.post).not.toHaveBeenCalled();
  });
});
