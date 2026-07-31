import apiClient from './api';

export const fetchAdminOverview = async () => {
  const response = await apiClient.get('/admin/overview');
  return response.data;
};

export const fetchAdminForecastRuns = async (limit = 20) => {
  const response = await apiClient.get('/admin/forecast-runs', { params: { limit } });
  return response.data;
};

export const triggerAdminForecastCheck = async () => {
  const response = await apiClient.post('/admin/forecast/check');
  return response.data;
};

export const fetchAdminSites = async (limit = 1000) => {
  const response = await apiClient.get('/admin/sites', { params: { limit } });
  return response.data;
};

export const updateAdminSite = async (siteId, payload) => {
  const response = await apiClient.patch(`/admin/sites/${siteId}`, payload);
  return response.data;
};

export const fetchAdminResources = async ({ missingOnly = false, limit = 250 } = {}) => {
  const response = await apiClient.get('/admin/resources', {
    params: {
      missing_only: missingOnly,
      limit,
    },
  });
  return response.data;
};
