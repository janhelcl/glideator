import axios from 'axios';

// Use environment variable for dev, fallback to relative path for production (handled by Render rewrite)
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || '/api'; 

// Fetch all sites with optional metric and date filters
export const fetchSites = async (metric = null, date = null, limit = 1000) => {
  try {
    const params = {
      limit
    };
    if (metric) params.metric = metric;
    if (date) params.date = date;

    const response = await axios.get(`${API_BASE_URL}/sites/`, {
      params,
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching sites:', error);
    throw error;
  }
};

// Fetch list of all sites (ID and Name only)
export const fetchSitesList = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/sites/list`);
    return response.data;
  } catch (error) {
    console.error('Error fetching sites list:', error);
    throw error;
  }
};

// Fetch site information
export const fetchSiteInfo = async (siteId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/sites/${siteId}/info`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching info for site ID ${siteId}:`, error);
    throw error;
  }
};

// Fetch predictions using site_id
export const fetchSitePredictions = async (siteId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/sites/${siteId}/predictions`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching predictions for site ID ${siteId}:`, error);
    throw error;
  }
};

// Fetch forecast using site_id
export const fetchSiteForecast = async (siteId, queryDate) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/sites/${siteId}/forecast`, {
      params: {
        query_date: queryDate,
      },
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching forecast data:', error);
    throw error;
  }
};

// Fetch flight statistics using site_id
export const fetchFlightStats = async (siteId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/sites/${siteId}/flight_stats`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching flight statistics for site ID ${siteId}:`, error);
    throw error;
  }
};

// Fetch spots using site_id
export const fetchSiteSpots = async (siteId) => {
  try {
    const response = await axios.get(`${API_BASE_URL}/sites/${siteId}/spots`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching spots for site ID ${siteId}:`, error);
    throw error;
  }
};

// Plan trip - fetch recommended sites for date range
export const planTrip = async (startDate, endDate, metric = 'XC0', userLocation = null, maxDistanceKm = null, altitudeRange = null, offset = 0, limit = 10) => {
  try {
    const requestBody = {
      start_date: startDate,
      end_date: endDate,
      metric: metric,
      offset: offset,
      limit: limit
    };

    // Add location and distance parameters if provided
    if (userLocation && userLocation.latitude && userLocation.longitude) {
      requestBody.user_latitude = userLocation.latitude;
      requestBody.user_longitude = userLocation.longitude;
    }
    
    if (maxDistanceKm !== null && maxDistanceKm > 0) {
      requestBody.max_distance_km = maxDistanceKm;
    }

    // Add altitude filtering if provided
    if (altitudeRange) {
      if (altitudeRange.min !== null && altitudeRange.min >= 0) {
        requestBody.min_altitude_m = altitudeRange.min;
      }
      if (altitudeRange.max !== null && altitudeRange.max >= 0) {
        requestBody.max_altitude_m = altitudeRange.max;
      }
    }

    const response = await axios.post(`${API_BASE_URL}/plan-trip`, requestBody);
    return response.data;
  } catch (error) {
    console.error('Error planning trip:', error);
    throw error;
  }
};
