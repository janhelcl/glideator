/**
 * Shared UI State Interface for Trip Planner Controls
 * Defines the structure for managing all trip planner control states
 */

export const DEFAULT_PLANNER_STATE = {
  // Date range selection
  dates: [null, null], // [startDate, endDate]
  
  // Distance filter
  distance: {
    enabled: false,
    km: 200,
    coords: null // { latitude, longitude, accuracy }
  },
  
  // Altitude filter
  altitude: {
    enabled: true,
    min: 0,
    max: 2500
  },
  
  // Flight quality filter
  flightQuality: {
    enabled: false,
    selectedValues: ['XC0'] // Array of selected XC values
  },
  
  // View mode
  view: 'list', // 'list' | 'map'
  
  // Selected metric for API calls
  selectedMetric: 'XC0',
  
  // Sort preference
  sortBy: 'flyability' // 'flyability' | 'distance'
};

/**
 * Available flight quality options (XC distances in km)
 */
export const FLIGHT_QUALITY_OPTIONS = [
  { value: 'XC0', label: '0' },
  { value: 'XC10', label: '10' },
  { value: 'XC25', label: '25' },
  { value: 'XC50', label: '50' },
  { value: 'XC100', label: '100' }
];

/**
 * Available metrics for API calls
 */
export const AVAILABLE_METRICS = [
  'XC0', 'XC10', 'XC20', 'XC30', 'XC40', 'XC50', 
  'XC60', 'XC70', 'XC80', 'XC90', 'XC100'
];

/**
 * Utility function to get next Friday
 */
export const getNextFriday = () => {
  const today = new Date();
  const dayOfWeek = today.getDay(); // 0 = Sunday, 1 = Monday, ..., 5 = Friday
  const daysUntilFriday = (5 - dayOfWeek + 7) % 7 || 7; // If today is Friday, get next Friday
  const result = new Date(today);
  result.setDate(result.getDate() + daysUntilFriday);
  return result;
};

/**
 * Utility function to add days to a date
 */
export const addDays = (date, days) => {
  const result = new Date(date);
  result.setDate(result.getDate() + days);
  return result;
};

/**
 * Get default date range (next Friday to Sunday)
 */
export const getDefaultDateRange = () => {
  const friday = getNextFriday();
  const sunday = addDays(friday, 2);
  return [friday, sunday];
}; 