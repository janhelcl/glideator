import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '/api';
const LOG_REQUESTS = process.env.NODE_ENV === 'development';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
});

let accessToken = null;
let requestSequence = 0;

const nextRequestId = () => {
  requestSequence += 1;
  return `api-${requestSequence}`;
};

const getDurationMs = (config) => {
  const startedAt = config?.metadata?.startedAt;
  return startedAt ? Math.round(performance.now() - startedAt) : null;
};

const logRequest = (level, message, details) => {
  if (!LOG_REQUESTS) return;
  const logger = console[level] || console.debug;
  logger(`[api] ${message}`, details);
};

export const setAccessToken = (token) => {
  accessToken = token;
};

export const getAccessToken = () => accessToken;

export const hasValidSession = async () => {
  try {
    await refreshAccessToken();
    return true;
  } catch {
    return false;
  }
};

apiClient.interceptors.request.use((config) => {
  const requestId = nextRequestId();
  config.metadata = {
    requestId,
    startedAt: performance.now(),
  };

  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }

  logRequest('debug', 'request', {
    requestId,
    method: config.method?.toUpperCase(),
    url: config.url,
  });

  return config;
});

const refreshAccessToken = async () => {
  try {
    const response = await apiClient.post('/auth/refresh');
    const token = response.data?.access_token;
    if (token) {
      setAccessToken(token);
    }
    return token;
  } catch (error) {
    setAccessToken(null);
    throw error;
  }
};

apiClient.interceptors.response.use(
  (response) => {
    logRequest('debug', 'response', {
      requestId: response.config?.metadata?.requestId,
      method: response.config?.method?.toUpperCase(),
      url: response.config?.url,
      status: response.status,
      durationMs: getDurationMs(response.config),
    });
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    const requestUrl = originalRequest?.url || '';

    if (
      error.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !requestUrl.endsWith('/auth/login') &&
      !requestUrl.endsWith('/auth/register') &&
      !requestUrl.endsWith('/auth/refresh')
    ) {
      originalRequest._retry = true;
      try {
        const newToken = await refreshAccessToken();
        if (newToken) {
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return apiClient(originalRequest);
        }
      } catch {
        setAccessToken(null);
      }
    }

    const cancelled = axios.isCancel(error) || error.code === 'ERR_CANCELED';
    logRequest(cancelled ? 'debug' : 'warn', cancelled ? 'cancelled' : 'error', {
      requestId: originalRequest?.metadata?.requestId,
      method: originalRequest?.method?.toUpperCase(),
      url: requestUrl,
      status: error.response?.status,
      durationMs: getDurationMs(originalRequest),
      message: error.message,
    });

    return Promise.reject(error);
  }
);

export const fetchSites = async (metric = null, date = null, limit = 1000, options = {}) => {
  const params = { limit };
  if (metric) params.metric = metric;
  if (date) params.date = date;
  const response = await apiClient.get('/sites/', { params, signal: options.signal });
  return response.data;
};

export const fetchSitesList = async (options = {}) => {
  const response = await apiClient.get('/sites/list', { signal: options.signal });
  return response.data;
};

export const fetchSiteInfo = async (siteId, options = {}) => {
  const response = await apiClient.get(`/sites/${siteId}/info`, { signal: options.signal });
  return response.data;
};

export const fetchSiteResources = async (siteId, options = {}) => {
  const response = await apiClient.get(`/sites/${siteId}/resources`, { signal: options.signal });
  return response.data;
};

export const fetchSitePredictions = async (siteId, options = {}) => {
  const response = await apiClient.get(`/sites/${siteId}/predictions`, { signal: options.signal });
  return response.data;
};

export const fetchSiteForecast = async (siteId, queryDate, options = {}) => {
  const response = await apiClient.get(`/sites/${siteId}/forecast`, {
    params: { query_date: queryDate },
    signal: options.signal,
  });
  return response.data;
};

export const fetchFlightStats = async (siteId, options = {}) => {
  const response = await apiClient.get(`/sites/${siteId}/flight_stats`, { signal: options.signal });
  return response.data;
};

export const fetchSiteSpots = async (siteId, options = {}) => {
  const response = await apiClient.get(`/sites/${siteId}/spots`, { signal: options.signal });
  return response.data;
};

export const fetchAllTags = async (minSites = 2, options = {}) => {
  const response = await apiClient.get('/sites/tags', {
    params: { min_sites: minSites },
    signal: options.signal,
  });
  return response.data;
};

export const planTrip = async (
  startDate,
  endDate,
  metric = 'XC0',
  userLocation = null,
  maxDistanceKm = null,
  altitudeRange = null,
  offset = 0,
  limit = 10,
  requiredTags = null,
  options = {}
) => {
  const requestBody = {
    start_date: startDate,
    end_date: endDate,
    metric,
    offset,
    limit,
  };

  if (userLocation?.latitude != null && userLocation?.longitude != null) {
    requestBody.user_latitude = userLocation.latitude;
    requestBody.user_longitude = userLocation.longitude;
  }

  if (maxDistanceKm !== null && maxDistanceKm > 0) {
    requestBody.max_distance_km = maxDistanceKm;
  }

  if (altitudeRange) {
    if (altitudeRange.min !== null && altitudeRange.min >= 0) {
      requestBody.min_altitude_m = altitudeRange.min;
    }
    if (altitudeRange.max !== null && altitudeRange.max >= 0) {
      requestBody.max_altitude_m = altitudeRange.max;
    }
  }

  if (requiredTags?.length) {
    requestBody.required_tags = requiredTags;
  }

  const response = await apiClient.post('/plan-trip', requestBody, { signal: options.signal });
  return response.data;
};

export const registerUser = async (email, password) => {
  const response = await apiClient.post('/auth/register', { email, password });
  return response.data;
};

export const loginUser = async (email, password) => {
  const response = await apiClient.post('/auth/login', { email, password });
  const token = response.data?.access_token;
  if (token) {
    setAccessToken(token);
  }
  return response.data;
};

export const fetchCurrentUser = async () => {
  const response = await apiClient.get('/auth/me');
  return response.data;
};

export const logoutUser = async () => {
  await apiClient.post('/auth/logout');
  setAccessToken(null);
};

export const fetchUserProfile = async () => {
  const response = await apiClient.get('/users/me/profile');
  return response.data;
};

export const updateUserProfile = async (payload) => {
  const response = await apiClient.patch('/users/me/profile', payload);
  return response.data;
};

export const fetchFavorites = async () => {
  const response = await apiClient.get('/users/me/favorites');
  return response.data;
};

export const addFavorite = async (siteId) => {
  await apiClient.post('/users/me/favorites', { site_id: siteId });
};

export const removeFavorite = async (siteId) => {
  await apiClient.delete(`/users/me/favorites/${siteId}`);
};

export const fetchPushSubscriptions = async () => {
  const response = await apiClient.get('/users/me/push-subscriptions');
  return response.data;
};

export const registerPushSubscriptionApi = async (payload) => {
  const response = await apiClient.post('/users/me/push-subscriptions', payload);
  return response.data;
};

export const deactivatePushSubscriptionApi = async (subscriptionId) => {
  await apiClient.delete(`/users/me/push-subscriptions/${subscriptionId}`);
};

export const fetchNotifications = async () => {
  const response = await apiClient.get('/users/me/notifications');
  return response.data;
};

export const createNotification = async (payload) => {
  const response = await apiClient.post('/users/me/notifications', payload);
  return response.data;
};

export const updateNotification = async (notificationId, payload) => {
  const response = await apiClient.patch(`/users/me/notifications/${notificationId}`, payload);
  return response.data;
};

export const deleteNotification = async (notificationId) => {
  await apiClient.delete(`/users/me/notifications/${notificationId}`);
};

export const fetchNotificationEvents = async (notificationId, limit = 20) => {
  const response = await apiClient.get(`/users/me/notifications/${notificationId}/events`, {
    params: { limit },
  });
  return response.data;
};

export const fetchRecentNotificationEvents = async (since = null, limit = 50) => {
  const params = { limit };
  if (since) {
    params.since = since;
  }
  const response = await apiClient.get('/users/me/notification-events', { params });
  return response.data;
};

export const fetchNotificationHistory = async (offset = 0, limit = 20) => {
  const response = await apiClient.get('/users/me/notification-events', {
    params: { offset, limit },
  });
  return response.data;
};

export const fetchSiteRecommendations = async (sourceSiteIds, topK = 5) => {
  const response = await apiClient.post('/s2s/recommendations', {
    source_site_ids: sourceSiteIds,
    top_k: topK,
  });
  return response.data;
};

export const fetchSingleSiteRecommendations = async (siteId, topK = 5) => {
  const response = await apiClient.get(`/s2s/recommendations/${siteId}`, {
    params: { top_k: topK },
  });
  return response.data;
};

export const fetchSimilarDays = async (siteId, forecastDate, n = 3) => {
  const response = await apiClient.get(`/d2d/similar-days/${siteId}/${forecastDate}`, {
    params: { n },
  });
  return response.data;
};

export const fetchPastDateForecast = async (siteId, forecastDate, pastDate) => {
  const response = await apiClient.get(`/d2d/past-forecast/${siteId}/${forecastDate}/${pastDate}`);
  return response.data;
};

export const submitFeedback = async (message) => {
  const response = await apiClient.post('/feedback/submit', { message });
  return response.data;
};

export default apiClient;
