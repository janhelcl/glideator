import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
});

const ACCESS_TOKEN_KEY = 'access_token';

let accessToken = null;

// Initialize access token from localStorage on module load
const storedToken = localStorage.getItem(ACCESS_TOKEN_KEY);
if (storedToken) {
  accessToken = storedToken;
}

export const setAccessToken = (token) => {
  accessToken = token;
  if (token) {
    localStorage.setItem(ACCESS_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
  }
};

export const getAccessToken = () => {
  return accessToken;
};

export const hasValidSession = async () => {
  try {
    await refreshAccessToken();
    return true;
  } catch {
    return false;
  }
};

apiClient.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

const refreshAccessToken = async () => {
  try {
    const response = await apiClient.post('/auth/refresh');
    const token = response.data?.access_token;
    if (token) {
      accessToken = token;
    }
    return token;
  } catch (error) {
    // Clear the access token if refresh fails
    accessToken = null;
    throw error;
  }
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url.endsWith('/auth/login') &&
      !originalRequest.url.endsWith('/auth/register') &&
      !originalRequest.url.endsWith('/auth/refresh')
    ) {
      originalRequest._retry = true;
      try {
        const newToken = await refreshAccessToken();
        if (newToken) {
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return apiClient(originalRequest);
        }
      } catch (refreshError) {
        // If refresh fails, clear the token and don't retry
        accessToken = null;
      }
    }
    return Promise.reject(error);
  }
);

export const fetchSites = async (metric = null, date = null, limit = 1000) => {
  const params = { limit };
  if (metric) params.metric = metric;
  if (date) params.date = date;
  const response = await apiClient.get('/sites/', { params });
  return response.data;
};

// Fetch list of all sites (ID and Name only)
export const fetchSitesList = async () => {
  const response = await apiClient.get('/sites/list');
  return response.data;
};

// Fetch site information
export const fetchSiteInfo = async (siteId) => {
  const response = await apiClient.get(`/sites/${siteId}/info`);
  return response.data;
};

// Fetch predictions using site_id
export const fetchSitePredictions = async (siteId) => {
  const response = await apiClient.get(`/sites/${siteId}/predictions`);
  return response.data;
};

// Fetch forecast using site_id
export const fetchSiteForecast = async (siteId, queryDate) => {
  const response = await apiClient.get(`/sites/${siteId}/forecast`, { params: { query_date: queryDate } });
  return response.data;
};

// Fetch flight statistics using site_id
export const fetchFlightStats = async (siteId) => {
  const response = await apiClient.get(`/sites/${siteId}/flight_stats`);
  return response.data;
};

// Fetch spots using site_id
export const fetchSiteSpots = async (siteId) => {
  const response = await apiClient.get(`/sites/${siteId}/spots`);
  return response.data;
};

// Fetch all unique tags
export const fetchAllTags = async (minSites = 2) => {
  const response = await apiClient.get('/sites/tags', { params: { min_sites: minSites } });
  return response.data;
};

// Plan trip - fetch recommended sites for date range
export const planTrip = async (
  startDate,
  endDate,
  metric = 'XC0',
  userLocation = null,
  maxDistanceKm = null,
  altitudeRange = null,
  offset = 0,
  limit = 10,
  requiredTags = null
) => {
  const requestBody = {
    start_date: startDate,
    end_date: endDate,
    metric,
    offset,
    limit,
  };

  if (userLocation?.latitude && userLocation?.longitude) {
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

  const response = await apiClient.post('/plan-trip', requestBody);
  return response.data;
};

// --- Auth API helpers ---

export const registerUser = async (email, password) => {
  const response = await apiClient.post('/auth/register', { email, password });
  return response.data;
};

export const loginUser = async (email, password) => {
  const response = await apiClient.post('/auth/login', { email, password });
  const token = response.data?.access_token;
  if (token) {
    accessToken = token;
  }
  return response.data;
};

export const fetchCurrentUser = async () => {
  const response = await apiClient.get('/auth/me');
  return response.data;
};

export const logoutUser = async () => {
  await apiClient.post('/auth/logout');
  accessToken = null;
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

// --- Push subscriptions ---

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

// --- Notification rules ---

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

export default apiClient;
