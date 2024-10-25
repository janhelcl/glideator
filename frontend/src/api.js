import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000'; // Update with your backend URL

export const fetchSites = async (metric, date) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/sites/`, { // Added trailing slash
      params: {
        metric,
        date,
      },
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
