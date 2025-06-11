import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Box, Container, Typography, Alert, Snackbar, Button, ButtonGroup } from '@mui/material';
import DateRangePicker from '../components/DateRangePicker';
import SiteList from '../components/SiteList';
import PlannerMapView from '../components/PlannerMapView';
import StandaloneMetricControl from '../components/StandaloneMetricControl';
import DistanceFilter from '../components/DistanceFilter';
import AltitudeFilter from '../components/AltitudeFilter';
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
  const [userLocation, setUserLocation] = useState(null);
  const [maxDistance, setMaxDistance] = useState(200);
  const [distanceFilterEnabled, setDistanceFilterEnabled] = useState(false);
  const [altitudeRange, setAltitudeRange] = useState({ min: 0, max: 3000 });
  const [altitudeFilterEnabled, setAltitudeFilterEnabled] = useState(false);
  const [sites, setSites] = useState([]);
  const [sortBy, setSortBy] = useState('flyability'); // 'flyability' or 'distance'
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [totalCount, setTotalCount] = useState(0);
  const [error, setError] = useState(null);
  
  // Error handling
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  
  // Generate cache key for requests
  const getCacheKey = (start, end, metric, location, distance, distanceEnabled, altitude, altitudeEnabled) => {
    const locationStr = distanceEnabled && location ? `${location.latitude.toFixed(3)}_${location.longitude.toFixed(3)}_${distance}` : 'no_distance';
    const altitudeStr = altitudeEnabled ? `${altitude.min}_${altitude.max}` : 'no_altitude';
    return `${formatDate(start)}_${formatDate(end)}_${metric}_${locationStr}_${altitudeStr}`;
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

    // Check if start date is in the past
    const today = new Date();
    today.setHours(0, 0, 0, 0); // Reset time to beginning of day for fair comparison
    const startDateCopy = new Date(startDate);
    startDateCopy.setHours(0, 0, 0, 0);
    
    if (startDateCopy < today) {
      setError('Start date cannot be in the past');
      setSnackbarOpen(true);
      return;
    }
    
    const cacheKey = getCacheKey(startDate, endDate, selectedMetric, userLocation, maxDistance, distanceFilterEnabled, altitudeRange, altitudeFilterEnabled);
    
    // Check cache first
    cleanupCache();
    const cachedResult = REQUEST_CACHE.get(cacheKey);
    if (cachedResult && Date.now() - cachedResult.timestamp < CACHE_DURATION) {
      setSites(cachedResult.data.sites || []);
      setHasMore(cachedResult.data.has_more || false);
      setTotalCount(cachedResult.data.total_count || 0);
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const startDateStr = formatDate(startDate);
      const endDateStr = formatDate(endDate);
      
      // Prepare location and distance for API call
      const locationForApi = distanceFilterEnabled && userLocation ? userLocation : null;
      const distanceForApi = distanceFilterEnabled && userLocation ? maxDistance : null;
      
      // Prepare altitude range for API call
      const altitudeForApi = altitudeFilterEnabled ? altitudeRange : null;
      
      const result = await planTrip(startDateStr, endDateStr, selectedMetric, locationForApi, distanceForApi, altitudeForApi, 0, 10);
      
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
      setHasMore(result.has_more || false);
      setTotalCount(result.total_count || 0);
      
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
  }, [startDate, endDate, selectedMetric, userLocation, maxDistance, distanceFilterEnabled, altitudeRange, altitudeFilterEnabled]);
  
  // Handle site click from map
  const handleSiteClick = (site) => {
    // Open site details in new tab with selected metric
    const url = `/details/${site.site_id}?metric=${selectedMetric}`;
    window.open(url, '_blank');
  };

  // Handle loading more sites
  const handleLoadMore = useCallback(async () => {
    if (!hasMore || loadingMore) return;

    setLoadingMore(true);
    setError(null);

    try {
      const startDateStr = formatDate(startDate);
      const endDateStr = formatDate(endDate);
      
      // Prepare location and distance for API call
      const locationForApi = distanceFilterEnabled && userLocation ? userLocation : null;
      const distanceForApi = distanceFilterEnabled && userLocation ? maxDistance : null;
      
      // Prepare altitude range for API call
      const altitudeForApi = altitudeFilterEnabled ? altitudeRange : null;
      
      const result = await planTrip(startDateStr, endDateStr, selectedMetric, locationForApi, distanceForApi, altitudeForApi, sites.length, 10);
      
      // Append new sites to existing ones
      setSites(prevSites => [...prevSites, ...(result.sites || [])]);
      setHasMore(result.has_more || false);
      setTotalCount(result.total_count || 0);
      
    } catch (err) {
      console.error('Error loading more sites:', err);
      setError('Failed to load more sites. Please try again.');
      setSnackbarOpen(true);
    } finally {
      setLoadingMore(false);
    }
  }, [startDate, endDate, selectedMetric, userLocation, maxDistance, distanceFilterEnabled, altitudeRange, altitudeFilterEnabled, sites.length, hasMore, loadingMore]);
  
  // Auto-search on initial load with default dates
  useEffect(() => {
    handlePlanTrip();
  }, [handlePlanTrip]);

  // Sort sites based on selected sort option
  const sortedSites = useMemo(() => {
    if (!sites || sites.length === 0) return sites;
    
    const sitesCopy = [...sites];
    
    if (sortBy === 'distance' && distanceFilterEnabled) {
      // Sort by distance (closest first), then by flyability as secondary sort
      return sitesCopy.sort((a, b) => {
        if (a.distance_km !== null && b.distance_km !== null) {
          const distanceDiff = a.distance_km - b.distance_km;
          if (Math.abs(distanceDiff) < 0.1) { // If distances are very close, sort by flyability
            return b.average_flyability - a.average_flyability;
          }
          return distanceDiff;
        }
        // If either site doesn't have distance, sort by flyability
        return b.average_flyability - a.average_flyability;
      });
    } else {
      // Sort by flyability (default - highest first)
      return sitesCopy.sort((a, b) => b.average_flyability - a.average_flyability);
    }
  }, [sites, sortBy, distanceFilterEnabled]);
  
  return (
    <Container maxWidth="lg" sx={{ py: 3, height: '100%', overflow: 'auto' }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" sx={{ mb: 1, fontWeight: 'bold' }}>
          Plan a Trip
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Select your travel dates to find the best paragliding sites with optimal flying conditions
          {distanceFilterEnabled && userLocation && (
            <span style={{ fontWeight: 'bold' }}>
              {' '}within {maxDistance < 1000 ? `${maxDistance}km` : `${(maxDistance/1000).toFixed(1)}k km`} of your location
            </span>
          )}
          {altitudeFilterEnabled && (
            <span style={{ fontWeight: 'bold' }}>
              {' '}at {altitudeRange.min >= 1000 ? `${(altitudeRange.min/1000).toFixed(1)}k` : altitudeRange.min}m - {altitudeRange.max >= 1000 ? `${(altitudeRange.max/1000).toFixed(1)}k` : altitudeRange.max}m altitude
            </span>
          )}
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
          
          <Box sx={{ minWidth: '280px' }}>
            <DistanceFilter
              userLocation={userLocation}
              onLocationChange={setUserLocation}
              maxDistance={maxDistance}
              onMaxDistanceChange={setMaxDistance}
              enabled={distanceFilterEnabled}
              onEnabledChange={setDistanceFilterEnabled}
            />
          </Box>
          
          <Box sx={{ minWidth: '280px' }}>
            <AltitudeFilter
              altitudeRange={altitudeRange}
              onAltitudeRangeChange={setAltitudeRange}
              enabled={altitudeFilterEnabled}
              onEnabledChange={setAltitudeFilterEnabled}
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
            userLocation={distanceFilterEnabled ? userLocation : null}
          />
        </Box>
      )}

      {!loading && sites.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
              Recommended Sites ({sortedSites.length}{totalCount > sortedSites.length ? ` of ${totalCount}` : ''})
            </Typography>
            
            {distanceFilterEnabled && userLocation && (
              <ButtonGroup size="small" variant="outlined">
                <Button
                  variant={sortBy === 'flyability' ? 'contained' : 'outlined'}
                  onClick={() => setSortBy('flyability')}
                >
                  Best Conditions
                </Button>
                <Button
                  variant={sortBy === 'distance' ? 'contained' : 'outlined'}
                  onClick={() => setSortBy('distance')}
                >
                  Closest
                </Button>
              </ButtonGroup>
            )}
          </Box>
          
          <SiteList 
            sites={sortedSites} 
            onSiteClick={handleSiteClick}
            selectedMetric={selectedMetric}
            showRanking={true}
          />
          
          {hasMore && (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
              <Button
                variant="outlined"
                onClick={handleLoadMore}
                disabled={loadingMore}
                size="large"
                sx={{ px: 4 }}
              >
                {loadingMore ? 'Loading...' : 'More'}
              </Button>
            </Box>
          )}
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