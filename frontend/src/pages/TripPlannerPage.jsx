import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Box, Typography, Alert, Snackbar, Button, ButtonGroup, Paper } from '@mui/material';
import TripPlannerControls from '../components/TripPlannerControls';
import SiteList from '../components/SiteList';
import PlannerMapView from '../components/PlannerMapView';
import LoadingSpinner from '../components/LoadingSpinner';
import { planTrip } from '../api';
import { DEFAULT_PLANNER_STATE, getDefaultDateRange, AVAILABLE_METRICS } from '../types/ui-state';
import { useSearchParams } from 'react-router-dom';

// Cache for API requests (5 minutes)
const REQUEST_CACHE = new Map();
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes in milliseconds

// Utility functions to replace date-fns
const formatDate = (date) => {
  if (!date) return '';
  return date.toISOString().split('T')[0];
};

const getInitialStateFromURL = (searchParams) => {
    const state = JSON.parse(JSON.stringify(DEFAULT_PLANNER_STATE));
    const [defaultStart, defaultEnd] = getDefaultDateRange();
    state.dates = [defaultStart, defaultEnd];

    // Dates
    const startDateParam = searchParams.get('startDate');
    const endDateParam = searchParams.get('endDate');
    if (startDateParam && endDateParam) {
        const sd = new Date(startDateParam);
        const ed = new Date(endDateParam);
        if (!isNaN(sd.getTime()) && !isNaN(ed.getTime())) {
            state.dates = [sd, ed];
        }
    }

    // Distance
    if (searchParams.get('distEnabled') === 'true') {
        state.distance.enabled = true;
        state.distance.km = parseInt(searchParams.get('distKm'), 10) || state.distance.km;
    } else if (searchParams.get('distEnabled') === 'false') {
        state.distance.enabled = false;
    }

    // Altitude
    const altEnabledParam = searchParams.get('altEnabled');
    if (altEnabledParam === 'false') {
        state.altitude.enabled = false;
    } else {
        // Altitude is enabled by default, or if altEnabled=true
        state.altitude.enabled = true;
        const altMin = parseInt(searchParams.get('altMin'), 10);
        const altMax = parseInt(searchParams.get('altMax'), 10);
        if (!isNaN(altMin)) {
            state.altitude.min = altMin;
        }
        if (!isNaN(altMax)) {
            state.altitude.max = altMax;
        }
    }

    // Flight Quality & Metric
    const fqEnabledParam = searchParams.get('fqEnabled');
    const metricParam = searchParams.get('metric');

    if (metricParam) {
        // Metric from URL is source of truth for slider value
        state.selectedMetric = metricParam;
        const metricIndex = AVAILABLE_METRICS.indexOf(metricParam);
        if (metricIndex > -1) {
            state.flightQuality.selectedValues = AVAILABLE_METRICS.slice(0, metricIndex + 1);
        }
    }
    
    // Enabled state logic: a non-default metric implies enabled, but fqEnabled param has final say.
    if (metricParam && metricParam !== DEFAULT_PLANNER_STATE.selectedMetric) {
        state.flightQuality.enabled = true;
    }
    if (fqEnabledParam === 'true') {
        state.flightQuality.enabled = true;
    }
    if (fqEnabledParam === 'false') {
        state.flightQuality.enabled = false;
    }

    // View
    const view = searchParams.get('view');
    if (view === 'list' || view === 'map') state.view = view;
    
    // SortBy
    const sortBy = searchParams.get('sortBy');
    if (sortBy === 'flyability' || sortBy === 'distance') state.sortBy = sortBy;

    // Tags
    const tagsParam = searchParams.get('tags');
    if (tagsParam) {
        state.tags = tagsParam.split(',').filter(Boolean);
    }

    return state;
};

const TripPlannerPage = () => {
  const [searchParams, setSearchParams] = useSearchParams();

  // Initialize unified planner state with default values, potentially overridden by URL params
  const [plannerState, setPlannerState] = useState(() => getInitialStateFromURL(searchParams));
  
  // Separate UI states (client-side only, don't trigger API calls)
  const [sortBy, setSortBy] = useState(plannerState.sortBy);
  const [view, setView] = useState(plannerState.view);
  
  const [sites, setSites] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [totalCount, setTotalCount] = useState(0);
  const [error, setError] = useState(null);
  
  // Error handling
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  
  // Location detection for distance calculations
  const [userLocation, setUserLocation] = useState(null);
  const [locationRequested, setLocationRequested] = useState(false);
  
  // Generate cache key for requests
  const getCacheKey = (start, end, state, userLoc) => {
    // Include user location for distance calculation
    const userLocationStr = userLoc 
      ? `user_${userLoc.latitude.toFixed(3)}_${userLoc.longitude.toFixed(3)}`
      : 'no_user_location';
    // Include distance filter if enabled
    const distanceFilterStr = state.distance.enabled && state.distance.coords 
      ? `filter_${state.distance.coords.latitude.toFixed(3)}_${state.distance.coords.longitude.toFixed(3)}_${state.distance.km}` 
      : 'no_distance_filter';
    const altitudeStr = state.altitude.enabled 
      ? `${state.altitude.min}_${state.altitude.max}` 
      : 'no_altitude';
    const flightQualityStr = state.flightQuality.enabled 
      ? state.flightQuality.selectedValues.join(',') 
      : 'no_flight_quality';
    const tagsStr = (state.tags && state.tags.length > 0) ? state.tags.join(',') : 'no_tags';
    return `${formatDate(start)}_${formatDate(end)}_${state.selectedMetric}_${userLocationStr}_${distanceFilterStr}_${altitudeStr}_${flightQualityStr}_${tagsStr}`;
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

  // Auto-detect location on page load
  useEffect(() => {
    if (!userLocation && !locationRequested) {
      setLocationRequested(true);
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          (position) => {
            setUserLocation({
              latitude: position.coords.latitude,
              longitude: position.coords.longitude
            });
          },
          (error) => {
            console.log('Location detection failed:', error.message);
            // Don't show error to user, just continue without location
          },
          {
            enableHighAccuracy: false,
            timeout: 5000,
            maximumAge: 300000 // 5 minutes
          }
        );
      }
    }
  }, [userLocation, locationRequested]);

  // Update URL search params when state changes
  useEffect(() => {
    const newParams = new URLSearchParams();
    const { dates, distance, altitude, flightQuality, selectedMetric, tags } = plannerState;
    const defaultState = DEFAULT_PLANNER_STATE;

    // Dates are always present
    newParams.set('startDate', formatDate(dates[0]));
    newParams.set('endDate', formatDate(dates[1]));

    // Distance - default enabled is false
    if (distance.enabled) {
        newParams.set('distEnabled', 'true');
        if (distance.km !== defaultState.distance.km) {
            newParams.set('distKm', distance.km);
        }
    }

    // Altitude - default enabled is true
    if (!altitude.enabled) {
        newParams.set('altEnabled', 'false');
    } else {
        if (altitude.min !== defaultState.altitude.min) newParams.set('altMin', altitude.min);
        if (altitude.max !== defaultState.altitude.max) newParams.set('altMax', altitude.max);
    }

    // Flight Quality - default enabled is false
    if (flightQuality.enabled) {
        newParams.set('fqEnabled', 'true');
    }
    
    if (selectedMetric !== defaultState.selectedMetric) {
         newParams.set('metric', selectedMetric);
    }

    if (view !== defaultState.view) newParams.set('view', view);
    if (sortBy !== defaultState.sortBy) newParams.set('sortBy', sortBy);

    // Tags
    if (tags && tags.length > 0) {
      newParams.set('tags', tags.join(','));
    }

    setSearchParams(newParams, { replace: true });
  }, [plannerState, sortBy, view, setSearchParams]);

  // Function to request location permission
  const requestLocation = useCallback(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setUserLocation({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude
          });
        },
        (error) => {
          let errorMessage = 'Unable to get location';
          switch (error.code) {
            case error.PERMISSION_DENIED:
              errorMessage = 'Location access denied. Please enable location permissions.';
              break;
            case error.POSITION_UNAVAILABLE:
              errorMessage = 'Location information is unavailable.';
              break;
            case error.TIMEOUT:
              errorMessage = 'Location request timed out.';
              break;
            default:
              errorMessage = 'An unknown error occurred while getting location.';
              break;
          }
          setError(errorMessage);
          setSnackbarOpen(true);
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 300000
        }
      );
    } else {
      setError('Geolocation is not supported by this browser');
      setSnackbarOpen(true);
    }
  }, []);
  
  // Handle trip planning
  const handlePlanTrip = useCallback(async (dates) => {
    cleanupCache();
    
    const [startDate, endDate] = dates;
    
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
    
    const cacheKey = getCacheKey(startDate, endDate, plannerState, userLocation);
    
    // Check cache first
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
      
      // Always send location if available (for distance calculation)
      const locationForApi = userLocation || (plannerState.distance.enabled && plannerState.distance.coords ? plannerState.distance.coords : null);
      // Only apply distance filter if distance filter is enabled
      const distanceForApi = plannerState.distance.enabled && plannerState.distance.coords ? plannerState.distance.km : null;
      
      // Prepare altitude range for API call
      const altitudeForApi = plannerState.altitude.enabled ? plannerState.altitude : null;
      
      // Debug: Log what we're sending to the API
      console.log('API Call Parameters:', {
        startDate: startDateStr,
        endDate: endDateStr,
        metric: plannerState.selectedMetric,
        location: locationForApi,
        distance: distanceForApi,
        altitude: altitudeForApi,
        tags: plannerState.tags,
        plannerState: plannerState
      });
      
      const result = await planTrip(startDateStr, endDateStr, plannerState.selectedMetric, locationForApi, distanceForApi, altitudeForApi, 0, 10, plannerState.tags);
      
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
  }, [
    userLocation,
    plannerState
  ]);
  
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
      
      // Always send location if available (for distance calculation)
      const locationForApi = userLocation || (plannerState.distance.enabled && plannerState.distance.coords ? plannerState.distance.coords : null);
      // Only apply distance filter if distance filter is enabled
      const distanceForApi = plannerState.distance.enabled && plannerState.distance.coords ? plannerState.distance.km : null;
      
      // Prepare altitude range for API call
      const altitudeForApi = plannerState.altitude.enabled ? plannerState.altitude : null;
      
      // Debug: Log what we're sending to the API for load more
      console.log('Load More API Call Parameters:', {
        startDate: startDateStr,
        endDate: endDateStr,
        metric: plannerState.selectedMetric,
        location: locationForApi,
        distance: distanceForApi,
        altitude: altitudeForApi,
        tags: plannerState.tags,
        offset: sites.length
      });
      
      const result = await planTrip(startDateStr, endDateStr, plannerState.selectedMetric, locationForApi, distanceForApi, altitudeForApi, sites.length, 10, plannerState.tags);
      
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
  }, [plannerState, sites.length, hasMore, loadingMore, userLocation]);

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

  // Re-search when filters (not site count) change
  const filtersSignature = useMemo(() => {
    return JSON.stringify({
      altitude: plannerState.altitude,
      distance: { enabled: plannerState.distance.enabled, km: plannerState.distance.km },
      flightQuality: { enabled: plannerState.flightQuality.enabled, values: plannerState.flightQuality.selectedValues },
      metric: plannerState.selectedMetric,
      dates: plannerState.dates,
      tags: plannerState.tags,
    });
  }, [
    plannerState.altitude,
    plannerState.distance.enabled,
    plannerState.distance.km,
    plannerState.flightQuality.enabled,
    plannerState.flightQuality.selectedValues,
    plannerState.selectedMetric,
    plannerState.dates,
    plannerState.tags,
  ]);

  const prevFilterSigRef = useRef(filtersSignature);

  useEffect(() => {
    if (sites.length === 0) return; // Nothing to refresh yet

    if (prevFilterSigRef.current !== filtersSignature) {
      // Filters changed – refresh data
      handlePlanTrip(plannerState.dates);
      prevFilterSigRef.current = filtersSignature;
    }
  }, [filtersSignature, sites.length, handlePlanTrip, plannerState.dates]);

  // Sort sites based on selected sort option
  const sortedSites = useMemo(() => {
    if (!sites || sites.length === 0) return sites;
    
    const sitesCopy = [...sites];
    
    if (sortBy === 'distance') {
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
  }, [sites, sortBy]);
  
  return (
    <Box sx={{ 
      maxWidth: '1200px',
      margin: '0 auto',
      p: 2,
      minHeight: '100%',  // Ensure it takes full height if content is short
    }}>
      <Paper elevation={2}>
        <Box sx={{ p: 3 }}>
          {/* Page title with logo */}
          <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider', display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold' }}>
              Plan a Trip
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <img 
                src="/logo192.png" 
                alt="Glideator Logo" 
                style={{ height: '60px', width: 'auto' }} 
              />
            </Box>
          </Box>
          
          <Box sx={{ mb: 4 }}>
            {/* New Unified Controls */}
            <TripPlannerControls
              state={{ ...plannerState, view }}
              setState={setPlannerState}
              onViewChange={setView}
              onSubmit={handlePlanTrip}
              loading={loading}
            />
          </Box>
          
          {/* Results */}
          {(loading || sites.length > 0) && (
            <Box sx={{ mb: 2 }}>
              {sites.length > 0 && (
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
                  {view === 'list' && (
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
                          variant={sortBy === 'flyability' ? 'contained' : 'outlined'}
                          onClick={() => setSortBy('flyability')}
                        >
                          Best Conditions
                        </Button>
                        <Button
                          variant={sortBy === 'distance' ? 'contained' : 'outlined'}
                          onClick={() => {
                            if (!userLocation) {
                              // Prompt for location if not available
                              requestLocation();
                            } else {
                              setSortBy('distance');
                            }
                          }}
                        >
                          Closest
                        </Button>
                      </ButtonGroup>
                    </Box>
                  )}
                </Box>
                
                {/* Sort buttons on mobile - below title, left aligned */}
                {view === 'list' && (
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
                        variant={sortBy === 'flyability' ? 'contained' : 'outlined'}
                        onClick={() => setSortBy('flyability')}
                      >
                        Best
                      </Button>
                      <Button
                        variant={sortBy === 'distance' ? 'contained' : 'outlined'}
                        onClick={() => {
                          if (!userLocation) {
                            // Prompt for location if not available
                            requestLocation();
                          } else {
                            setSortBy('distance');
                          }
                        }}
                      >
                        Closest
                      </Button>
                    </ButtonGroup>
                  </Box>
                )}
              </Box>
              )}
              
              {view === 'list' ? (
                sites.length > 0 ? (
                  <SiteList 
                    sites={sortedSites} 
                    onSiteClick={handleSiteClick}
                    selectedMetric={plannerState.selectedMetric}
                    showRanking={true}
                  />
                ) : loading ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
                    <LoadingSpinner />
                  </Box>
                ) : null
              ) : (
                <PlannerMapView
                  sites={sortedSites}
                  onSiteClick={handleSiteClick}
                  isVisible={true}
                  maxSites={sortedSites.length}
                  selectedMetric={plannerState.selectedMetric}
                  userLocation={plannerState.distance.enabled ? plannerState.distance.coords : null}
                  loading={loading && sites.length === 0}
                />
              )}
              
              {sites.length > 0 && (sites.length > 10 || hasMore) && (
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
        </Box>
      </Paper>
    </Box>
  );
};

export default TripPlannerPage; 