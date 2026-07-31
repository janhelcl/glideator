jest.mock('axios', () => {
  const client = jest.fn();
  client.get = jest.fn();
  client.post = jest.fn();
  client.patch = jest.fn();
  client.delete = jest.fn();
  client.interceptors = {
    request: { use: jest.fn() },
    response: { use: jest.fn() },
  };

  return {
    __esModule: true,
    default: {
      create: jest.fn(() => client),
      isCancel: jest.fn(() => false),
      __mockClient: client,
    },
  };
});

import axios from 'axios';
import {
  fetchSiteForecast,
  getAccessToken,
  loginUser,
  logoutUser,
  planTrip,
  setAccessToken,
} from './api';

const mockApiClient = axios.__mockClient;
const requestInterceptor = mockApiClient.interceptors.request.use.mock.calls[0][0];
const responseErrorInterceptor = mockApiClient.interceptors.response.use.mock.calls[0][1];

describe('API client', () => {
  beforeEach(() => {
    mockApiClient.mockReset();
    mockApiClient.get.mockReset();
    mockApiClient.post.mockReset();
    mockApiClient.patch.mockReset();
    mockApiClient.delete.mockReset();
    setAccessToken(null);
  });

  it('adds the bearer token and request metadata', () => {
    setAccessToken('access-token');
    const config = {
      headers: {},
      method: 'get',
      url: '/sites/list',
    };

    const result = requestInterceptor(config);

    expect(result.headers.Authorization).toBe('Bearer access-token');
    expect(result.metadata.requestId).toMatch(/^api-\d+$/);
    expect(result.metadata.startedAt).toEqual(expect.any(Number));
  });

  it('passes AbortSignal and query parameters to forecast requests', async () => {
    const controller = new AbortController();
    mockApiClient.get.mockResolvedValue({ data: { date: '2026-08-02' } });

    const result = await fetchSiteForecast(42, '2026-08-02', { signal: controller.signal });

    expect(result).toEqual({ date: '2026-08-02' });
    expect(mockApiClient.get).toHaveBeenCalledWith('/sites/42/forecast', {
      params: { query_date: '2026-08-02' },
      signal: controller.signal,
    });
  });

  it('builds a complete cancellable trip-planning request, including zero coordinates', async () => {
    const controller = new AbortController();
    mockApiClient.post.mockResolvedValue({ data: { sites: [], total_count: 0, has_more: false } });

    await planTrip(
      '2026-08-02',
      '2026-08-04',
      'XC20',
      { latitude: 0, longitude: 0 },
      250,
      { min: 0, max: 1800 },
      10,
      5,
      ['official', 'alps'],
      { signal: controller.signal },
    );

    expect(mockApiClient.post).toHaveBeenCalledWith(
      '/plan-trip',
      {
        start_date: '2026-08-02',
        end_date: '2026-08-04',
        metric: 'XC20',
        user_latitude: 0,
        user_longitude: 0,
        max_distance_km: 250,
        min_altitude_m: 0,
        max_altitude_m: 1800,
        required_tags: ['official', 'alps'],
        offset: 10,
        limit: 5,
      },
      { signal: controller.signal },
    );
  });

  it('omits disabled optional trip-planning filters', async () => {
    mockApiClient.post.mockResolvedValue({ data: { sites: [], total_count: 0, has_more: false } });

    await planTrip(
      '2026-08-02',
      '2026-08-04',
      'XC0',
      null,
      0,
      { min: null, max: -1 },
      0,
      10,
      [],
    );

    expect(mockApiClient.post).toHaveBeenCalledWith(
      '/plan-trip',
      {
        start_date: '2026-08-02',
        end_date: '2026-08-04',
        metric: 'XC0',
        offset: 0,
        limit: 10,
      },
      { signal: undefined },
    );
  });

  it('refreshes once after a 401 and retries with the new token', async () => {
    const originalRequest = {
      url: '/users/me/profile',
      method: 'get',
      headers: { Authorization: 'Bearer expired' },
    };
    const retriedResponse = { data: { display_name: 'Pilot' } };
    mockApiClient.post.mockResolvedValue({ data: { access_token: 'fresh-token' } });
    mockApiClient.mockResolvedValue(retriedResponse);

    const result = await responseErrorInterceptor({
      config: originalRequest,
      response: { status: 401 },
      message: 'Unauthorized',
    });

    expect(mockApiClient.post).toHaveBeenCalledWith('/auth/refresh');
    expect(originalRequest._retry).toBe(true);
    expect(originalRequest.headers.Authorization).toBe('Bearer fresh-token');
    expect(mockApiClient).toHaveBeenCalledWith(originalRequest);
    expect(result).toBe(retriedResponse);
    expect(getAccessToken()).toBe('fresh-token');
  });

  it('does not recursively refresh the refresh endpoint', async () => {
    const error = {
      config: { url: '/auth/refresh', method: 'post', headers: {} },
      response: { status: 401 },
      message: 'Unauthorized',
    };

    await expect(responseErrorInterceptor(error)).rejects.toBe(error);
    expect(mockApiClient.post).not.toHaveBeenCalled();
  });

  it('stores a token on login and clears it on logout', async () => {
    mockApiClient.post
      .mockResolvedValueOnce({ data: { access_token: 'login-token' } })
      .mockResolvedValueOnce({ data: { ok: true } });

    await loginUser('pilot@example.com', 'StrongPass1!');
    expect(getAccessToken()).toBe('login-token');

    await logoutUser();
    expect(getAccessToken()).toBeNull();
    expect(mockApiClient.post).toHaveBeenNthCalledWith(2, '/auth/logout');
  });
});
