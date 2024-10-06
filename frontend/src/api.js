import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000'; // Update with your backend URL

export const fetchSites = async (metric, date) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/sites`, {
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