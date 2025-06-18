import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Box, Container, Typography, Alert, Snackbar, Button, ButtonGroup } from '@mui/material';
import TripPlannerControls from '../components/TripPlannerControls';
import SiteList from '../components/SiteList';
import PlannerMapView from '../components/PlannerMapView';
import LoadingSpinner from '../components/LoadingSpinner';
import { planTrip } from '../api';
import { DEFAULT_PLANNER_STATE, getDefaultDateRange } from '../types/ui-state';

// Cache for API requests (5 minutes)
const REQUEST_CACHE = new Map();
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes in milliseconds

// Utility functions to replace date-fns
const formatDate = (date) => {
  if (!date) return '';
  return date.toISOString().split('T')[0];
};

const TripPlannerPage = () => {
  // Initialize unified planner state with default values
  const [plannerState, setPlannerState] = useState(() => {
    const [defaultStart, defaultEnd] = getDefaultDateRange();
    return {
      ...DEFAULT_PLANNER_STATE,
      dates: [defaultStart, defaultEnd]
    };
  });
  
  const [sites, setSites] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [totalCount, setTotalCount] = useState(0);
  const [error, setError] = useState(null);
  
  // Error handling
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  
  // Generate cache key for requests
  const getCacheKey = (start, end, state) => {
    const locationStr = state.distance.enabled && state.distance.coords 
      ? `${state.distance.coords.latitude.toFixed(3)}_${state.distance.coords.longitude.toFixed(3)}_${state.distance.km}` 
      : 'no_distance';
    const altitudeStr = state.altitude.enabled 
      ? `${state.altitude.min}_${state.altitude.max}` 
      : 'no_altitude';
    const flightQualityStr = state.flightQuality.enabled 
      ? state.flightQuality.selectedValues.join(',') 
      : 'no_flight_quality';
    return `${formatDate(start)}_${formatDate(end)}_${state.selectedMetric}_${locationStr}_${altitudeStr}_${flightQualityStr}`;
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
  const handlePlanTrip = useCallback(async (dateRange) => {
    const [startDate, endDate] = dateRange;
    
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
    
    const cacheKey = getCacheKey(startDate, endDate, plannerState);
    
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
      const locationForApi = plannerState.distance.enabled && plannerState.distance.coords ? plannerState.distance.coords : null;
      const distanceForApi = plannerState.distance.enabled && plannerState.distance.coords ? plannerState.distance.km : null;
      
      // Prepare altitude range for API call
      const altitudeForApi = plannerState.altitude.enabled ? plannerState.altitude : null;
      
      const result = await planTrip(startDateStr, endDateStr, plannerState.selectedMetric, locationForApi, distanceForApi, altitudeForApi, 0, 10);
      
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
        setError('No suitable sites found for the selected criteria');
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
  }, [plannerState]);
  
  // Handle site click from map
  const handleSiteClick = (site) => {
    // Open site details in new tab with selected metric
    const url = `/details/${site.site_id}?metric=${plannerState.selectedMetric}`;
    window.open(url, '_blank');
  };

  // Handle loading more sites
  const handleLoadMore = useCallback(async () => {
    if (!hasMore || loadingMore) return;

    setLoadingMore(true);
    setError(null);

    try {
      const [startDate, endDate] = plannerState.dates;
      const startDateStr = formatDate(startDate);
      const endDateStr = formatDate(endDate);
      
      // Prepare location and distance for API call
      const locationForApi = plannerState.distance.enabled && plannerState.distance.coords ? plannerState.distance.coords : null;
      const distanceForApi = plannerState.distance.enabled && plannerState.distance.coords ? plannerState.distance.km : null;
      
      // Prepare altitude range for API call
      const altitudeForApi = plannerState.altitude.enabled ? plannerState.altitude : null;
      
      const result = await planTrip(startDateStr, endDateStr, plannerState.selectedMetric, locationForApi, distanceForApi, altitudeForApi, sites.length, 10);
      
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
  }, [plannerState, sites.length, hasMore, loadingMore]);

  // Handle loading less sites (round down to nearest batch of 10)
  const handleLoadLess = useCallback(() => {
    if (sites.length <= 10) return; // Don't go below initial 10 sites
    
    // If current count is not a multiple of 10, round down to nearest multiple
    // If current count is already a multiple of 10, subtract 10
    const remainder = sites.length % 10;
    let targetCount;
    
    if (remainder === 0) {
      // Already a multiple of 10, remove one full batch
      targetCount = sites.length - 10;
    } else {
      // Has remainder, round down to nearest multiple of 10
      targetCount = sites.length - remainder;
    }
    
    // Ensure we don't go below 10
    targetCount = Math.max(10, targetCount);
    
    setSites(prevSites => prevSites.slice(0, targetCount));
    setHasMore(true); // Since we removed sites, there might be more available
  }, [sites.length]);
  
  // Auto-search on initial load with default dates
  useEffect(() => {
    if (plannerState.dates[0] && plannerState.dates[1]) {
      handlePlanTrip(plannerState.dates);
    }
  }, [handlePlanTrip, plannerState.dates]);

  // Sort sites based on selected sort option
  const sortedSites = useMemo(() => {
    if (!sites || sites.length === 0) return sites;
    
    const sitesCopy = [...sites];
    
    if (plannerState.sortBy === 'distance' && plannerState.distance.enabled) {
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
  }, [sites, plannerState.sortBy, plannerState.distance.enabled]);
  
  return (
    <Container maxWidth="lg" sx={{ py: 3, height: '100%', overflow: 'auto' }}>
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" sx={{ mb: 1, fontWeight: 'bold' }}>
          Plan a Trip
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Find the best paragliding sites for your next adventure
        </Typography>
        
        {/* New Unified Controls */}
        <TripPlannerControls
          state={plannerState}
          setState={setPlannerState}
          onSubmit={handlePlanTrip}
          loading={loading}
        />
      </Box>
      
      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <LoadingSpinner />
        </Box>
      )}
      
      {/* Results */}
      {!loading && sites.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <Box sx={{ mb: 2 }}>
            {/* Title row */}
            <Box sx={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              mb: { xs: 1, sm: 0 }
            }}>
              <Typography 
                variant="h6" 
                sx={{ 
                  fontWeight: 'bold',
                  fontSize: { xs: '1.1rem', sm: '1.25rem' }
                }}
              >
                Showing {sites.length} of {totalCount} sites
              </Typography>
              
              {/* Sort buttons - only show on desktop */}
              {plannerState.view === 'list' && (
                <Box sx={{ 
                  display: { xs: 'none', sm: 'flex' },
                  alignItems: 'center', 
                  gap: 1
                }}>
                  <Typography 
                    variant="caption" 
                    color="text.secondary" 
                    sx={{ fontSize: '0.75rem' }}
                  >
                    Sort by:
                  </Typography>
                  <ButtonGroup 
                    size="small" 
                    variant="outlined" 
                    sx={{ 
                      '& .MuiButton-root': { 
                        fontSize: '0.75rem', 
                        px: 1.5, 
                        py: 0.5
                      } 
                    }}
                  >
                    <Button
                      variant={plannerState.sortBy === 'flyability' ? 'contained' : 'outlined'}
                      onClick={() => setPlannerState(prev => ({ ...prev, sortBy: 'flyability' }))}
                    >
                      Best Conditions
                    </Button>
                    {plannerState.distance.enabled && plannerState.distance.coords && (
                      <Button
                        variant={plannerState.sortBy === 'distance' ? 'contained' : 'outlined'}
                        onClick={() => setPlannerState(prev => ({ ...prev, sortBy: 'distance' }))}
                      >
                        Closest
                      </Button>
                    )}
                  </ButtonGroup>
                </Box>
              )}
            </Box>
            
            {/* Sort buttons on mobile - below title, left aligned */}
            {plannerState.view === 'list' && (
              <Box sx={{ 
                display: { xs: 'flex', sm: 'none' },
                alignItems: 'center', 
                gap: 0.5
              }}>
                <ButtonGroup 
                  size="small" 
                  variant="outlined" 
                  sx={{ 
                    '& .MuiButton-root': { 
                      fontSize: '0.7rem', 
                      px: 1, 
                      py: 0.25
                    } 
                  }}
                >
                  <Button
                    variant={plannerState.sortBy === 'flyability' ? 'contained' : 'outlined'}
                    onClick={() => setPlannerState(prev => ({ ...prev, sortBy: 'flyability' }))}
                  >
                    Best
                  </Button>
                  {plannerState.distance.enabled && plannerState.distance.coords && (
                    <Button
                      variant={plannerState.sortBy === 'distance' ? 'contained' : 'outlined'}
                      onClick={() => setPlannerState(prev => ({ ...prev, sortBy: 'distance' }))}
                    >
                      Closest
                    </Button>
                  )}
                </ButtonGroup>
              </Box>
            )}
          </Box>
          
          {plannerState.view === 'list' ? (
            <SiteList 
              sites={sortedSites} 
              onSiteClick={handleSiteClick}
              selectedMetric={plannerState.selectedMetric}
              showRanking={true}
            />
          ) : (
            <PlannerMapView
              sites={sites}
              onSiteClick={handleSiteClick}
              isVisible={true}
              maxSites={sites.length}
              selectedMetric={plannerState.selectedMetric}
              userLocation={plannerState.distance.enabled ? plannerState.distance.coords : null}
            />
          )}
          
          {(sites.length > 10 || hasMore) && (
            <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt: 3 }}>
              {sites.length > 10 && (
                <Button
                  variant="outlined"
                  onClick={handleLoadLess}
                  size="large"
                  sx={{ px: 4 }}
                >
                  Less
                </Button>
              )}
              {hasMore && (
                <Button
                  variant="outlined"
                  onClick={handleLoadMore}
                  disabled={loadingMore}
                  size="large"
                  sx={{ px: 4 }}
                >
                  {loadingMore ? 'Loading...' : 'More'}
                </Button>
              )}
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