import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useInfiniteQuery } from '@tanstack/react-query';
import { Alert, Box, Button, ButtonGroup, Paper, Snackbar, Typography } from '@mui/material';
import { Helmet } from 'react-helmet-async';
import { useNavigate, useSearchParams } from 'react-router-dom';
import TripPlannerControls from '../components/TripPlannerControls';
import SiteList from '../components/SiteList';
import PlannerMapView from '../components/PlannerMapView';
import LoadingSpinner from '../components/LoadingSpinner';
import QuickFeedback from '../components/QuickFeedback';
import { planTrip } from '../api';
import { trackEvent } from '../analytics';
import { AVAILABLE_METRICS, DEFAULT_PLANNER_STATE, getDefaultDateRange } from '../types/ui-state';
import { useDefaultMetric } from '../hooks/useDefaultMetric';
import { useAuth } from '../context/AuthContext';

const PAGE_SIZE = 10;
const SEARCH_DEBOUNCE_MS = 250;

const formatDate = (date) => {
  if (!date) return '';
  return date.toISOString().split('T')[0];
};

const getInitialStateFromURL = (searchParams, preferredMetric = 'XC0') => {
  const state = JSON.parse(JSON.stringify(DEFAULT_PLANNER_STATE));
  state.selectedMetric = preferredMetric;
  state.flightQuality.selectedValues = [preferredMetric];

  const [defaultStart, defaultEnd] = getDefaultDateRange();
  state.dates = [defaultStart, defaultEnd];

  const startDateParam = searchParams.get('startDate');
  const endDateParam = searchParams.get('endDate');
  if (startDateParam && endDateParam) {
    const startDate = new Date(startDateParam);
    const endDate = new Date(endDateParam);
    if (!Number.isNaN(startDate.getTime()) && !Number.isNaN(endDate.getTime())) {
      state.dates = [startDate, endDate];
    }
  }

  if (searchParams.get('distEnabled') === 'true') {
    state.distance.enabled = true;
    state.distance.km = Number.parseInt(searchParams.get('distKm'), 10) || state.distance.km;
  } else if (searchParams.get('distEnabled') === 'false') {
    state.distance.enabled = false;
  }

  const locationSource = searchParams.get('locSrc');
  if (locationSource === 'home' || locationSource === 'current') {
    state.distance.locationSource = locationSource;
  }

  if (searchParams.get('altEnabled') === 'false') {
    state.altitude.enabled = false;
  } else {
    const altitudeMin = Number.parseInt(searchParams.get('altMin'), 10);
    const altitudeMax = Number.parseInt(searchParams.get('altMax'), 10);
    state.altitude.enabled = true;
    if (!Number.isNaN(altitudeMin)) state.altitude.min = altitudeMin;
    if (!Number.isNaN(altitudeMax)) state.altitude.max = altitudeMax;
  }

  const metricParam = searchParams.get('metric');
  if (metricParam && AVAILABLE_METRICS.includes(metricParam)) {
    state.selectedMetric = metricParam;
    const metricIndex = AVAILABLE_METRICS.indexOf(metricParam);
    state.flightQuality.selectedValues = AVAILABLE_METRICS.slice(0, metricIndex + 1);
  }

  if (metricParam && metricParam !== preferredMetric) state.flightQuality.enabled = true;
  if (searchParams.get('fqEnabled') === 'true') state.flightQuality.enabled = true;
  if (searchParams.get('fqEnabled') === 'false') state.flightQuality.enabled = false;

  const view = searchParams.get('view');
  if (view === 'list' || view === 'map') state.view = view;

  const sortBy = searchParams.get('sortBy');
  if (sortBy === 'flyability' || sortBy === 'distance') state.sortBy = sortBy;

  const tags = searchParams.get('tags');
  if (tags) state.tags = tags.split(',').filter(Boolean);

  return state;
};

const validateDates = (dates) => {
  const [startDate, endDate] = dates;

  if (!startDate || !endDate) return 'Please select both start and end dates';
  if (startDate > endDate) return 'End date cannot be before start date';

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const normalizedStart = new Date(startDate);
  normalizedStart.setHours(0, 0, 0, 0);

  if (normalizedStart < today) return 'Start date cannot be in the past';
  return null;
};

const buildRequestInput = (state, userLocation) => {
  const dateError = validateDates(state.dates);
  if (dateError) return null;

  const location = userLocation || (
    state.distance.enabled && state.distance.coords ? state.distance.coords : null
  );

  return {
    startDate: formatDate(state.dates[0]),
    endDate: formatDate(state.dates[1]),
    metric: state.selectedMetric,
    location: location ? {
      latitude: Number(location.latitude),
      longitude: Number(location.longitude),
    } : null,
    maxDistanceKm: state.distance.enabled && state.distance.coords ? state.distance.km : null,
    altitudeRange: state.altitude.enabled ? {
      min: state.altitude.min,
      max: state.altitude.max,
    } : null,
    requiredTags: state.tags?.length ? [...state.tags].sort() : null,
  };
};

const TripPlannerPage = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { preferredMetric } = useDefaultMetric();
  const { profile } = useAuth();

  const [plannerState, setPlannerState] = useState(() => getInitialStateFromURL(searchParams, preferredMetric));
  const [sortBy, setSortBy] = useState(plannerState.sortBy);
  const [view, setView] = useState(plannerState.view);
  const [userLocation, setUserLocation] = useState(null);
  const [locationRequested, setLocationRequested] = useState(false);
  const [queryInput, setQueryInput] = useState(null);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const [snackbarMessage, setSnackbarMessage] = useState(null);
  const initializedRef = useRef(false);
  const lastTrackedResultsRef = useRef(null);

  useEffect(() => {
    if (initializedRef.current) return;

    const latitude = Number(profile?.home_lat);
    const longitude = Number(profile?.home_lon);
    const hasHomeLocation = Number.isFinite(latitude) && Number.isFinite(longitude);

    if (searchParams.get('locSrc') === 'home' && hasHomeLocation) {
      setPlannerState((previous) => ({
        ...previous,
        distance: {
          ...previous.distance,
          coords: { latitude, longitude },
        },
      }));
    }

    initializedRef.current = true;
  }, [profile, searchParams]);

  useEffect(() => {
    if (userLocation || locationRequested) return;

    setLocationRequested(true);
    if (!navigator.geolocation) return;

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setUserLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        });
      },
      () => {},
      { enableHighAccuracy: false, timeout: 5000, maximumAge: 300000 },
    );
  }, [locationRequested, userLocation]);

  useEffect(() => {
    const newParams = new URLSearchParams();
    const { dates, distance, altitude, flightQuality, selectedMetric, tags } = plannerState;

    newParams.set('startDate', formatDate(dates[0]));
    newParams.set('endDate', formatDate(dates[1]));

    if (distance.enabled) {
      newParams.set('distEnabled', 'true');
      if (distance.km !== DEFAULT_PLANNER_STATE.distance.km) newParams.set('distKm', distance.km);
      if (distance.locationSource && distance.locationSource !== 'current') {
        newParams.set('locSrc', distance.locationSource);
      }
    }

    if (!altitude.enabled) {
      newParams.set('altEnabled', 'false');
    } else {
      if (altitude.min !== DEFAULT_PLANNER_STATE.altitude.min) newParams.set('altMin', altitude.min);
      if (altitude.max !== DEFAULT_PLANNER_STATE.altitude.max) newParams.set('altMax', altitude.max);
    }

    if (flightQuality.enabled) newParams.set('fqEnabled', 'true');
    if (selectedMetric !== preferredMetric) newParams.set('metric', selectedMetric);
    if (view !== DEFAULT_PLANNER_STATE.view) newParams.set('view', view);
    if (sortBy !== DEFAULT_PLANNER_STATE.sortBy) newParams.set('sortBy', sortBy);
    if (tags?.length) newParams.set('tags', tags.join(','));

    setSearchParams(newParams, { replace: true });
  }, [plannerState, preferredMetric, setSearchParams, sortBy, view]);

  const filtersSignature = useMemo(() => JSON.stringify({
    dates: plannerState.dates.map(formatDate),
    altitude: plannerState.altitude,
    distance: plannerState.distance,
    flightQuality: plannerState.flightQuality,
    metric: plannerState.selectedMetric,
    tags: plannerState.tags,
    userLocation,
  }), [plannerState, userLocation]);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      setQueryInput(buildRequestInput(plannerState, userLocation));
    }, SEARCH_DEBOUNCE_MS);

    return () => window.clearTimeout(timeoutId);
  }, [filtersSignature, plannerState, userLocation]);

  const querySignature = useMemo(() => JSON.stringify(queryInput), [queryInput]);

  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
  }, [querySignature]);

  const tripQuery = useInfiniteQuery({
    queryKey: ['trip-plan', queryInput],
    queryFn: ({ pageParam, signal }) => planTrip(
      queryInput.startDate,
      queryInput.endDate,
      queryInput.metric,
      queryInput.location,
      queryInput.maxDistanceKm,
      queryInput.altitudeRange,
      pageParam,
      PAGE_SIZE,
      queryInput.requiredTags,
      { signal },
    ),
    enabled: Boolean(queryInput),
    initialPageParam: 0,
    getNextPageParam: (lastPage, pages) => {
      if (!lastPage?.has_more) return undefined;
      return pages.reduce((count, page) => count + (page.sites?.length || 0), 0);
    },
    placeholderData: (previousData) => previousData,
  });

  const allSites = useMemo(
    () => tripQuery.data?.pages.flatMap((page) => page.sites || []) || [],
    [tripQuery.data],
  );

  const sites = useMemo(() => allSites.slice(0, visibleCount), [allSites, visibleCount]);
  const totalCount = tripQuery.data?.pages[0]?.total_count || 0;
  const hasMore = visibleCount < allSites.length || tripQuery.hasNextPage;
  const loading = Boolean(queryInput) && (tripQuery.isPending || (tripQuery.isFetching && allSites.length === 0));

  useEffect(() => {
    if (
      !queryInput
      || !tripQuery.isSuccess
      || tripQuery.isPlaceholderData
      || lastTrackedResultsRef.current === querySignature
    ) {
      return;
    }

    lastTrackedResultsRef.current = querySignature;
    trackEvent('trip_plan_results_viewed', {
      start_date: queryInput.startDate,
      end_date: queryInput.endDate,
      metric: queryInput.metric,
      distance_enabled: queryInput.maxDistanceKm != null,
      altitude_enabled: queryInput.altitudeRange != null,
      tags_count: queryInput.requiredTags?.length || 0,
      returned_count: allSites.length,
      total_count: totalCount,
      has_results: totalCount > 0,
    });
  }, [allSites.length, queryInput, querySignature, totalCount, tripQuery.isPlaceholderData, tripQuery.isSuccess]);

  useEffect(() => {
    if (tripQuery.isError) {
      setSnackbarMessage('Failed to plan trip. Please try again.');
    }
  }, [tripQuery.isError]);

  useEffect(() => {
    if (tripQuery.isSuccess && queryInput && allSites.length === 0) {
      setSnackbarMessage('No suitable sites found for the selected criteria');
    }
  }, [allSites.length, queryInput, tripQuery.isSuccess]);

  const showError = useCallback((message) => {
    setSnackbarMessage(message);
  }, []);

  const requestLocation = useCallback(() => {
    if (!navigator.geolocation) {
      showError('Geolocation is not supported by this browser');
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setUserLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        });
        setSortBy('distance');
      },
      (error) => {
        const messages = {
          [error.PERMISSION_DENIED]: 'Location access denied. Please enable location permissions.',
          [error.POSITION_UNAVAILABLE]: 'Location information is unavailable.',
          [error.TIMEOUT]: 'Location request timed out.',
        };
        showError(messages[error.code] || 'Unable to get location');
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 },
    );
  }, [showError]);

  const handlePlanTrip = useCallback((dates) => {
    const dateError = validateDates(dates);
    if (dateError) {
      showError(dateError);
      return;
    }

    const nextState = { ...plannerState, dates };
    const nextQueryInput = buildRequestInput(nextState, userLocation);

    trackEvent('trip_plan_submitted', {
      start_date: formatDate(dates[0]),
      end_date: formatDate(dates[1]),
      metric: nextState.selectedMetric,
      distance_enabled: nextState.distance.enabled,
      max_distance_km: nextState.distance.enabled ? nextState.distance.km : null,
      altitude_enabled: nextState.altitude.enabled,
      tags_count: nextState.tags?.length || 0,
    });

    setPlannerState(nextState);
    setQueryInput(nextQueryInput);
  }, [plannerState, showError, userLocation]);

  const handleSiteClick = useCallback((site, event) => {
    const url = `/details/${site.site_id}?metric=${plannerState.selectedMetric}`;
    trackEvent('trip_plan_site_opened', {
      site_id: Number(site.site_id),
      metric: plannerState.selectedMetric,
      average_flyability: site.average_flyability,
      view,
      sort_by: sortBy,
      opened_in_new_tab: Boolean(event && (event.button === 1 || event.ctrlKey || event.metaKey)),
    });

    if (event && (event.button === 1 || event.ctrlKey || event.metaKey)) {
      window.open(url, '_blank', 'noopener,noreferrer');
      return;
    }
    navigate(url);
  }, [navigate, plannerState.selectedMetric, sortBy, view]);

  const handleLoadMore = useCallback(async () => {
    trackEvent('trip_plan_more_requested', {
      visible_count: visibleCount,
      total_count: totalCount,
    });

    if (visibleCount < allSites.length) {
      setVisibleCount((count) => Math.min(count + PAGE_SIZE, allSites.length));
      return;
    }

    if (!tripQuery.hasNextPage || tripQuery.isFetchingNextPage) return;

    const result = await tripQuery.fetchNextPage();
    const loadedCount = result.data?.pages.reduce(
      (count, page) => count + (page.sites?.length || 0),
      0,
    ) || visibleCount;
    setVisibleCount((count) => Math.min(count + PAGE_SIZE, loadedCount));
  }, [allSites.length, totalCount, tripQuery, visibleCount]);

  const handleLoadLess = useCallback(() => {
    setVisibleCount((count) => Math.max(PAGE_SIZE, count - PAGE_SIZE));
  }, []);

  const handleViewChange = useCallback((nextView) => {
    if (nextView !== view) {
      trackEvent('trip_plan_view_changed', {
        previous_view: view,
        view: nextView,
      });
    }
    setView(nextView);
  }, [view]);

  const handleSortChange = useCallback((nextSort) => {
    if (nextSort !== sortBy) {
      trackEvent('trip_plan_sort_changed', {
        previous_sort: sortBy,
        sort: nextSort,
      });
    }
    setSortBy(nextSort);
  }, [sortBy]);

  const sortedSites = useMemo(() => {
    const sorted = [...sites];

    if (sortBy === 'distance') {
      return sorted.sort((a, b) => {
        if (a.distance_km != null && b.distance_km != null) {
          const distanceDifference = a.distance_km - b.distance_km;
          if (Math.abs(distanceDifference) >= 0.1) return distanceDifference;
        }
        return b.average_flyability - a.average_flyability;
      });
    }

    return sorted.sort((a, b) => b.average_flyability - a.average_flyability);
  }, [sites, sortBy]);

  return (
    <Box sx={{ maxWidth: '1200px', margin: '0 auto', p: 2, minHeight: '100%' }}>
      <Helmet>
        <title>Plan a Trip – Parra-Glideator</title>
        <meta name="description" content="Plan your paragliding trip by dates, distance, altitude, tags and flyability metrics. Discover top sites near you." />
        <link rel="canonical" href={window.location.origin + '/trip-planner'} />
        <meta property="og:title" content="Plan a Paragliding Trip" />
        <meta property="og:description" content="Find the best paragliding sites for your dates and preferences." />
        <meta property="og:type" content="website" />
        <meta name="twitter:card" content="summary_large_image" />
      </Helmet>

      <Paper elevation={2}>
        <Box sx={{ p: 3 }}>
          <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider', display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold' }}>Plan a Trip</Typography>
            <img src="/logo192.png" alt="Glideator Logo" style={{ height: '60px', width: 'auto' }} />
          </Box>

          <Box sx={{ mb: 4 }}>
            <TripPlannerControls
              state={{ ...plannerState, view }}
              setState={setPlannerState}
              onViewChange={handleViewChange}
              onSubmit={handlePlanTrip}
              loading={loading}
            />
          </Box>

          {(loading || sites.length > 0) && (
            <Box sx={{ mb: 2 }}>
              {sites.length > 0 && (
                <Box sx={{ mb: 2 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: { xs: 1, sm: 0 } }}>
                    <Typography variant="h6" sx={{ fontWeight: 'bold', fontSize: { xs: '1.1rem', sm: '1.25rem' } }}>
                      Top {sites.length} sites ({totalCount} total)
                    </Typography>

                    {view === 'list' && (
                      <Box sx={{ display: { xs: 'none', sm: 'flex' }, alignItems: 'center', gap: 1 }}>
                        <Typography variant="caption" color="text.secondary">Sort by:</Typography>
                        <ButtonGroup size="small" variant="outlined">
                          <Button
                            variant={sortBy === 'flyability' ? 'contained' : 'outlined'}
                            onClick={() => handleSortChange('flyability')}
                          >
                            Best Conditions
                          </Button>
                          <Button
                            variant={sortBy === 'distance' ? 'contained' : 'outlined'}
                            onClick={() => (userLocation ? handleSortChange('distance') : requestLocation())}
                          >
                            Closest
                          </Button>
                        </ButtonGroup>
                      </Box>
                    )}
                  </Box>

                  {view === 'list' && (
                    <Box sx={{ display: { xs: 'flex', sm: 'none' }, alignItems: 'center', gap: 0.5 }}>
                      <ButtonGroup size="small" variant="outlined">
                        <Button
                          variant={sortBy === 'flyability' ? 'contained' : 'outlined'}
                          onClick={() => handleSortChange('flyability')}
                        >
                          Best
                        </Button>
                        <Button
                          variant={sortBy === 'distance' ? 'contained' : 'outlined'}
                          onClick={() => (userLocation ? handleSortChange('distance') : requestLocation())}
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
                    showRanking
                  />
                ) : loading ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}><LoadingSpinner /></Box>
                ) : null
              ) : (
                <PlannerMapView
                  sites={sortedSites}
                  onSiteClick={handleSiteClick}
                  isVisible
                  maxSites={sortedSites.length}
                  selectedMetric={plannerState.selectedMetric}
                  userLocation={plannerState.distance.enabled ? plannerState.distance.coords : null}
                  loading={loading && sites.length === 0}
                />
              )}

              {sites.length > 0 && queryInput && (
                <Box sx={{ mt: 3 }}>
                  <QuickFeedback
                    key={querySignature}
                    question="Were these trip suggestions useful?"
                    context={{
                      surface: 'trip_planner',
                      start_date: queryInput.startDate,
                      end_date: queryInput.endDate,
                      metric: queryInput.metric,
                      result_count: totalCount,
                      distance_enabled: queryInput.maxDistanceKm != null,
                      altitude_enabled: queryInput.altitudeRange != null,
                      tags_count: queryInput.requiredTags?.length || 0,
                    }}
                  />
                </Box>
              )}

              {sites.length > 0 && (sites.length > PAGE_SIZE || hasMore) && (
                <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2, mt: 3 }}>
                  {sites.length > PAGE_SIZE && (
                    <Button variant="outlined" onClick={handleLoadLess} size="large" sx={{ px: 4 }}>
                      Less
                    </Button>
                  )}
                  {hasMore && (
                    <Button
                      variant="outlined"
                      onClick={handleLoadMore}
                      disabled={tripQuery.isFetchingNextPage}
                      size="large"
                      sx={{ px: 4 }}
                    >
                      {tripQuery.isFetchingNextPage ? 'Loading...' : 'More'}
                    </Button>
                  )}
                </Box>
              )}
            </Box>
          )}

          {!loading && sites.length === 0 && !queryInput && (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="h6" color="text.secondary">
                Select dates and click GO to find the best flying sites
              </Typography>
            </Box>
          )}

          <Snackbar
            open={Boolean(snackbarMessage)}
            autoHideDuration={6000}
            onClose={() => setSnackbarMessage(null)}
            anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
          >
            <Alert onClose={() => setSnackbarMessage(null)} severity="error" sx={{ width: '100%' }}>
              {snackbarMessage}
            </Alert>
          </Snackbar>
        </Box>
      </Paper>
    </Box>
  );
};

export default TripPlannerPage;