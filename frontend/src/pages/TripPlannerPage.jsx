import React, { useState, useEffect, useCallback } from 'react';
import { Box, Container, Typography, Alert, Snackbar } from '@mui/material';
import DateRangePicker from '../components/DateRangePicker';
import SiteList from '../components/SiteList';
import PlannerMapView from '../components/PlannerMapView';
import StandaloneMetricControl from '../components/StandaloneMetricControl';
import LoadingSpinner from '../components/LoadingSpinner';
import { planTrip } from '../api';

// Cache for API requests (5 minutes)
const REQUEST_CACHE = new Map();
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes in milliseconds

// Available metrics (consistent with other pages)
const METRICS = ['XC0', 'XC10', 'XC20', 'XC30', 'XC40', 'XC50', 'XC60', 'XC70', 'XC80', 'XC90', 'XC100'];

// Utility functions to replace date-fns
const formatDate = (date) => {
  if (!date) return '';
  return date.toISOString().split('T')[0];
};

const addDays = (date, days) => {
  const result = new Date(date);
  result.setDate(result.getDate() + days);
  return result;
};

const getNextFriday = () => {
  const today = new Date();
  const dayOfWeek = today.getDay(); // 0 = Sunday, 1 = Monday, ..., 5 = Friday
  const daysUntilFriday = (5 - dayOfWeek + 7) % 7 || 7; // If today is Friday, get next Friday
  return addDays(today, daysUntilFriday);
};

const TripPlannerPage = () => {
  const [startDate, setStartDate] = useState(() => {
    // Default to next Friday
    return getNextFriday();
  });
  
  const [endDate, setEndDate] = useState(() => {
    // Default to next Sunday (2 days after Friday)
    return addDays(getNextFriday(), 2);
  });
  
  const [selectedMetric, setSelectedMetric] = useState('XC0');
  const [sites, setSites] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Error handling
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  
  // Generate cache key for requests
  const getCacheKey = (start, end, metric) => {
    return `${formatDate(start)}_${formatDate(end)}_${metric}`;
  };
  
  // Clean up expired cache entries
  const cleanupCache = () => {
    const now = Date.now();
    for (const [key, value] of REQUEST_CACHE.entries()) {
      if (now - value.timestamp > CACHE_DURATION) {
        REQUEST_CACHE.delete(key);
      }
    }
  };
  
  // Handle trip planning
  const handlePlanTrip = useCallback(async () => {
    if (!startDate || !endDate) {
      setError('Please select both start and end dates');
      setSnackbarOpen(true);
      return;
    }
    
    if (startDate > endDate) {
      setError('End date cannot be before start date');
      setSnackbarOpen(true);
      return;
    }
    
    const cacheKey = getCacheKey(startDate, endDate, selectedMetric);
    
    // Check cache first
    cleanupCache();
    const cachedResult = REQUEST_CACHE.get(cacheKey);
    if (cachedResult && Date.now() - cachedResult.timestamp < CACHE_DURATION) {
      setSites(cachedResult.data.sites || []);
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const startDateStr = formatDate(startDate);
      const endDateStr = formatDate(endDate);
      
      const result = await planTrip(startDateStr, endDateStr, selectedMetric);
      
      // Debug: Log the API response to understand its structure
      console.log('Plan Trip API Response:', result);
      if (result.sites && result.sites.length > 0) {
        console.log('First site example:', result.sites[0]);
      }
      
      // Cache the result
      REQUEST_CACHE.set(cacheKey, {
        data: result,
        timestamp: Date.now()
      });
      
      setSites(result.sites || []);
      
      if (!result.sites || result.sites.length === 0) {
        setError('No suitable sites found for the selected date range');
        setSnackbarOpen(true);
      }
    } catch (err) {
      console.error('Error planning trip:', err);
      setError('Failed to plan trip. Please try again.');
      setSnackbarOpen(true);
      setSites([]);
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate, selectedMetric]);
  
  // Handle site click from map
  const handleSiteClick = (site) => {
    // Open site details in new tab with selected metric
    const url = `/details/${site.site_id}?metric=${selectedMetric}`;
    window.open(url, '_blank');
  };
  
  // Auto-search on initial load with default dates
  useEffect(() => {
    handlePlanTrip();
  }, [handlePlanTrip]);
  
  return (
    <Container maxWidth="lg" sx={{ py: 3, height: '100%', overflow: 'auto' }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" sx={{ mb: 1, fontWeight: 'bold' }}>
          Plan a Trip
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Select your travel dates to find the best paragliding sites with optimal flying conditions
        </Typography>
        
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, flexWrap: 'wrap' }}>
          <Box sx={{ flex: 1, minWidth: '300px' }}>
            <DateRangePicker
              startDate={startDate}
              endDate={endDate}
              onStartDateChange={setStartDate}
              onEndDateChange={setEndDate}
              onSearch={handlePlanTrip}
              loading={loading}
            />
          </Box>
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
              Flight Quality
            </Typography>
            <StandaloneMetricControl
              metrics={METRICS}
              selectedMetric={selectedMetric}
              onMetricChange={setSelectedMetric}
            />
          </Box>
        </Box>
      </Box>
      
      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <LoadingSpinner />
        </Box>
      )}
      
      {/* Map View */}
      {!loading && sites.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>
            Map View
          </Typography>
          <PlannerMapView
            sites={sites}
            onSiteClick={handleSiteClick}
            isVisible={true}
            maxSites={15}
            selectedMetric={selectedMetric}
          />
        </Box>
      )}

      {!loading && sites.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <SiteList 
            sites={sites} 
            onSiteClick={handleSiteClick}
            selectedMetric={selectedMetric}
          />
        </Box>
      )}
      
      {!loading && sites.length === 0 && !error && (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography variant="h6" color="text.secondary">
            Select dates and click GO to find the best flying sites
          </Typography>
        </Box>
      )}
      
      {/* Error Snackbar */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={6000}
        onClose={() => setSnackbarOpen(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert 
          onClose={() => setSnackbarOpen(false)} 
          severity="error" 
          sx={{ width: '100%' }}
        >
          {error}
        </Alert>
      </Snackbar>
    </Container>
  );
};

export default TripPlannerPage; 