import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000'; // Update with your backend URL

// Fetch all sites with optional metric and date filters
export const fetchSites = async (metric = null, date = null, limit = 1000) => {
  try {
    const params = {
      limit
    };
    if (metric) params.metric = metric;
    if (date) params.date = date;

    const response = await axios.get(`${API_BASE_URL}/sites/`, { // Added trailing slash
      params,
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching sites:', error);
    return [];
  }
};

// Fetch predictions using site_id
export const fetchSitePredictions = async (siteId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/sites/${siteId}/predictions/`); // Added trailing slash
    return response.data;
  } catch (error) {
    console.error(`Error fetching predictions for site ID ${siteId}:`, error);
    return [];
  }
};

// Fetch forecast using site_id
export const fetchSiteForecast = async (siteId, queryDate) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/sites/${siteId}/forecast/`, {
      params: {
        query_date: queryDate,
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching forecast data:', error);
    return null;
  }
};
