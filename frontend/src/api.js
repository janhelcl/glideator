import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000'; // Update with your backend URL

// Fetch all sites with optional metric and date filters
export const fetchSites = async (metric = null, date = null) => {
  try {
    const params = {};
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

export const fetchSitePredictions = async (siteName) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/sites/${siteName}/predictions/`); // Added trailing slash
    return response.data;
  } catch (error) {
    console.error(`Error fetching predictions for site ${siteName}:`, error);
    return [];
  }
};

export const fetchSiteForecast = async (siteName, queryDate) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/sites/${siteName}/forecast/`, {
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
