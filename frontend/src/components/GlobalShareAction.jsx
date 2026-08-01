import React, {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  IconButton,
  Snackbar,
  Tooltip,
} from '@mui/material';
import ShareIcon from '@mui/icons-material/Share';
import { useLocation } from 'react-router-dom';

import { fetchSiteInfo, fetchSitePredictions } from '../api';
import { trackEvent } from '../analytics';
import { useAuth } from '../context/AuthContext';
import { useDefaultMetric } from '../hooks/useDefaultMetric';
import {
  buildAboutShareUrl,
  buildDetailsShareUrl,
  buildMapShareUrl,
  buildTripPlanShareUrl,
  formatShareDate,
  formatShareDateRange,
  getChanceLabel,
  getFlightPhrase,
  getForecastProbability,
  getPluralFlightPhrase,
  normalizeMetric,
} from '../utils/shareUtils';

const PUBLIC_ORIGIN = process.env.REACT_APP_PUBLIC_ORIGIN || 'https://www.parra-glideator.com';
const useIsomorphicLayoutEffect = typeof window === 'undefined' ? useEffect : useLayoutEffect;

const copyText = async (text) => {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', '');
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand('copy');
  document.body.removeChild(textarea);
  if (!copied) throw new Error('Copy command failed');
};

const isValidOrigin = (latitude, longitude) => (
  Number.isFinite(latitude)
  && Number.isFinite(longitude)
  && latitude >= -90
  && latitude <= 90
  && longitude >= -180
  && longitude <= 180
);

const getBrowserOrigin = () => (
  typeof window !== 'undefined' && window.location?.origin
    ? window.location.origin
    : PUBLIC_ORIGIN
);

const getGeolocation = () => new Promise((resolve, reject) => {
  if (!navigator.geolocation) {
    reject(new Error('Location is not available in this browser'));
    return;
  }

  navigator.geolocation.getCurrentPosition(
    (position) => resolve({
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
    }),
    () => reject(new Error('Could not get your starting area')),
    { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 },
  );
});

const GlobalShareAction = () => {
  const location = useLocation();
  const { profile } = useAuth();
  const { preferredMetric } = useDefaultMetric();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [resolvingLocation, setResolvingLocation] = useState(false);
  const [message, setMessage] = useState(null);
  const [severity, setSeverity] = useState('success');
  const sharedOriginRef = useRef(null);

  const params = useMemo(() => new URLSearchParams(location.search), [location.search]);
  const detailMatch = location.pathname.match(/^\/details\/(\d+)$/);
  const siteId = detailMatch ? Number(detailMatch[1]) : null;

  const predictionsQuery = useQuery({
    queryKey: ['site', siteId, 'predictions'],
    queryFn: ({ signal }) => fetchSitePredictions(siteId, { signal }),
    enabled: Number.isFinite(siteId),
  });

  const siteInfoQuery = useQuery({
    queryKey: ['site', siteId, 'info'],
    queryFn: async ({ signal }) => {
      try {
        return await fetchSiteInfo(siteId, { signal });
      } catch (error) {
        if (error?.response?.status === 404) return null;
        throw error;
      }
    },
    enabled: Number.isFinite(siteId),
  });

  const sharedLatitude = Number(params.get('originLat'));
  const sharedLongitude = Number(params.get('originLng'));
  if (
    location.pathname === '/trip-planner'
    && isValidOrigin(sharedLatitude, sharedLongitude)
  ) {
    sharedOriginRef.current = {
      latitude: sharedLatitude,
      longitude: sharedLongitude,
    };
  }

  const effectiveSharedOrigin = location.pathname === '/trip-planner'
    ? sharedOriginRef.current
    : null;
  const hasSharedOrigin = Boolean(effectiveSharedOrigin);

  useIsomorphicLayoutEffect(() => {
    if (!hasSharedOrigin || typeof navigator === 'undefined' || !navigator.geolocation) {
      return undefined;
    }

    const geolocation = navigator.geolocation;
    const original = geolocation.getCurrentPosition;
    const sharedGetCurrentPosition = (success) => {
      window.setTimeout(() => success({
        coords: {
          latitude: effectiveSharedOrigin.latitude,
          longitude: effectiveSharedOrigin.longitude,
          accuracy: 10000,
          altitude: null,
          altitudeAccuracy: null,
          heading: null,
          speed: null,
        },
        timestamp: Date.now(),
      }), 0);
    };

    try {
      geolocation.getCurrentPosition = sharedGetCurrentPosition;
    } catch {
      return undefined;
    }

    return () => {
      try {
        geolocation.getCurrentPosition = original;
      } catch {
        // Nothing else to restore when the browser exposes a read-only implementation.
      }
    };
  }, [effectiveSharedOrigin, hasSharedOrigin]);

  useEffect(() => {
    if (!hasSharedOrigin || typeof window === 'undefined') return;

    // TripPlannerPage rebuilds its own query string. Keep the coarse shared
    // origin in the address bar so a refresh or second share stays reproducible.
    const currentUrl = new URL(window.location.href);
    if (!currentUrl.searchParams.has('originLat')) {
      currentUrl.searchParams.set('originLat', effectiveSharedOrigin.latitude.toFixed(1));
      currentUrl.searchParams.set('originLng', effectiveSharedOrigin.longitude.toFixed(1));
      window.history.replaceState(window.history.state, '', currentUrl.toString());
    }
  }, [effectiveSharedOrigin, hasSharedOrigin, location.search]);

  useEffect(() => {
    if (hasSharedOrigin) {
      setSeverity('info');
      setMessage('Using the approximate starting area from the shared trip plan');
    }
  }, [hasSharedOrigin]);

  const pageConfig = useMemo(() => {
    const origin = getBrowserOrigin();

    if (location.pathname === '/') {
      const selectedDate = params.get('date');
      const metric = normalizeMetric(params.get('metric') || preferredMetric);
      const formattedDate = formatShareDate(selectedDate);
      return {
        tooltip: 'Share forecast map',
        ariaLabel: 'Share forecast map',
        eventName: 'forecast_map_shared',
        eventProperties: { date: selectedDate, metric },
        copiedMessage: 'Forecast map link copied',
        payload: {
          title: `Paragliding forecast for ${formattedDate}`,
          text: `Compare sites by chance of ${getFlightPhrase(metric)} on ${formattedDate}.`,
          url: buildMapShareUrl({
            origin,
            search: params,
            selectedDate,
            selectedMetric: metric,
          }),
        },
      };
    }

    if (Number.isFinite(siteId)) {
      const site = predictionsQuery.data?.[0];
      if (!site) return null;

      const displayName = siteInfoQuery.data?.site_name || site.name || `Site ${siteId}`;
      const tab = params.get('tab') || 'forecast';
      const selectedDate = params.get('date');
      const metric = normalizeMetric(params.get('metric') || 'XC0');
      const formattedDate = formatShareDate(selectedDate);
      const probability = getForecastProbability({
        predictions: site.predictions,
        selectedDate,
        selectedMetric: metric,
      });
      const percentage = probability == null ? null : Math.round(probability * 100);
      const url = buildDetailsShareUrl({
        origin,
        siteId,
        tab,
        selectedDate,
        selectedMetric: metric,
      });

      if (tab === 'season') {
        const text = metric === 'XC0'
          ? `See ${displayName}’s typical flying season, based on historical activity.`
          : `See when ${displayName} is typically active for ${getPluralFlightPhrase(metric)}, based on historical activity.`;
        return {
          tooltip: 'Share flying season',
          ariaLabel: `Share flying season for ${displayName}`,
          eventName: 'site_section_shared',
          eventProperties: { site_id: siteId, tab, metric },
          copiedMessage: 'Flying season link copied',
          payload: { title: `${displayName} flying season`, text, url },
        };
      }

      if (tab === 'map') {
        return {
          tooltip: 'Share site map',
          ariaLabel: `Share site map for ${displayName}`,
          eventName: 'site_section_shared',
          eventProperties: { site_id: siteId, tab },
          copiedMessage: 'Site map link copied',
          payload: {
            title: `${displayName} site map`,
            text: `See takeoffs and landings for ${displayName}.`,
            url,
          },
        };
      }

      if (tab === 'resources') {
        return {
          tooltip: 'Share flying resources',
          ariaLabel: `Share flying resources for ${displayName}`,
          eventName: 'site_section_shared',
          eventProperties: { site_id: siteId, tab },
          copiedMessage: 'Flying resources link copied',
          payload: {
            title: `${displayName} flying resources`,
            text: `Local clubs, weather links, webcams and other flying resources for ${displayName}.`,
            url,
          },
        };
      }

      const estimate = percentage == null
        ? `${getChanceLabel(metric)} at ${displayName}`
        : `${percentage}% chance of ${getFlightPhrase(metric)} at ${displayName}`;
      return {
        tooltip: 'Share forecast',
        ariaLabel: `Share forecast for ${displayName}`,
        eventName: 'forecast_shared',
        eventProperties: {
          site_id: siteId,
          date: selectedDate,
          metric,
          probability,
        },
        copiedMessage: 'Forecast link copied',
        payload: {
          title: `${displayName} forecast for ${formattedDate}`,
          text: `Glideator estimates a ${estimate.charAt(0).toLowerCase()}${estimate.slice(1)} on ${formattedDate}.`,
          url,
        },
      };
    }

    if (location.pathname === '/trip-planner') {
      const startDate = params.get('startDate');
      const endDate = params.get('endDate');
      const metric = normalizeMetric(params.get('metric') || preferredMetric);
      const formattedRange = formatShareDateRange(startDate, endDate);
      const distanceEnabled = params.get('distEnabled') === 'true';
      const base = {
        tooltip: 'Share trip plan',
        ariaLabel: 'Share trip plan',
        eventName: 'trip_plan_shared',
        eventProperties: { start_date: startDate, end_date: endDate, metric },
        copiedMessage: 'Trip plan link copied',
        requiresLocationChoice: distanceEnabled,
      };

      return {
        ...base,
        buildPayload: ({ includeDistance = false, approximateOrigin = null } = {}) => ({
          title: `Paragliding trip plan for ${formattedRange}`,
          text: `Explore sites for ${formattedRange}, ranked by chance of ${getFlightPhrase(metric)}.`,
          url: buildTripPlanShareUrl({
            origin,
            search: params,
            selectedMetric: metric,
            includeDistance,
            approximateOrigin,
          }),
        }),
      };
    }

    if (location.pathname === '/about') {
      return {
        tooltip: 'Share how it works',
        ariaLabel: 'Share how Parra-Glideator works',
        eventName: 'how_it_works_shared',
        eventProperties: { section: location.hash || null },
        copiedMessage: 'How it works link copied',
        payload: {
          title: 'How Parra-Glideator works',
          text: 'See how Parra-Glideator combines weather forecasts and flight history to estimate flying activity.',
          url: buildAboutShareUrl({ origin, hash: location.hash }),
        },
      };
    }

    return null;
  }, [
    location.hash,
    location.pathname,
    params,
    predictionsQuery.data,
    preferredMetric,
    siteId,
    siteInfoQuery.data,
  ]);

  const performShare = useCallback(async (payload) => {
    if (!payload || !pageConfig) return;

    if (navigator.share) {
      try {
        await navigator.share(payload);
        void trackEvent(pageConfig.eventName, {
          ...pageConfig.eventProperties,
          method: 'native',
        });
        return;
      } catch (error) {
        if (error?.name === 'AbortError') return;
      }
    }

    try {
      await copyText(payload.url);
      setSeverity('success');
      setMessage(pageConfig.copiedMessage);
      void trackEvent(pageConfig.eventName, {
        ...pageConfig.eventProperties,
        method: 'clipboard',
      });
    } catch {
      setSeverity('error');
      setMessage('Could not copy the link');
    }
  }, [pageConfig]);

  const handleShare = useCallback(() => {
    if (!pageConfig) return;
    if (pageConfig.requiresLocationChoice) {
      setDialogOpen(true);
      return;
    }
    const payload = pageConfig.payload || pageConfig.buildPayload?.();
    void performShare(payload);
  }, [pageConfig, performShare]);

  const resolveApproximateOrigin = useCallback(async () => {
    if (effectiveSharedOrigin) return effectiveSharedOrigin;

    const latitude = Number(profile?.home_lat);
    const longitude = Number(profile?.home_lon);
    if (params.get('locSrc') === 'home' && isValidOrigin(latitude, longitude)) {
      return { latitude, longitude };
    }

    return getGeolocation();
  }, [effectiveSharedOrigin, params, profile]);

  const handleIncludeArea = useCallback(async () => {
    if (!pageConfig?.buildPayload) return;
    setResolvingLocation(true);
    try {
      const approximateOrigin = await resolveApproximateOrigin();
      setDialogOpen(false);
      await performShare(pageConfig.buildPayload({
        includeDistance: true,
        approximateOrigin,
      }));
    } catch (error) {
      setSeverity('error');
      setMessage(error?.message || 'Could not get the starting area');
    } finally {
      setResolvingLocation(false);
    }
  }, [pageConfig, performShare, resolveApproximateOrigin]);

  const handleWithoutLocation = useCallback(() => {
    if (!pageConfig?.buildPayload) return;
    setDialogOpen(false);
    void performShare(pageConfig.buildPayload({ includeDistance: false }));
  }, [pageConfig, performShare]);

  if (!pageConfig) return null;

  return (
    <>
      <Tooltip title={pageConfig.tooltip}>
        <IconButton color="inherit" aria-label={pageConfig.ariaLabel} onClick={handleShare}>
          <ShareIcon />
        </IconButton>
      </Tooltip>

      <Dialog open={dialogOpen} onClose={() => !resolvingLocation && setDialogOpen(false)}>
        <DialogTitle>Share starting area?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This trip uses a distance filter. Include an approximate starting area, about 10 km across,
            so other pilots see comparable results?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)} disabled={resolvingLocation}>Cancel</Button>
          <Button onClick={handleWithoutLocation} disabled={resolvingLocation}>Share without location</Button>
          <Button onClick={handleIncludeArea} variant="contained" disabled={resolvingLocation}>
            {resolvingLocation ? 'Getting area…' : 'Include area'}
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={Boolean(message)}
        autoHideDuration={4000}
        onClose={() => setMessage(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity={severity} onClose={() => setMessage(null)} sx={{ width: '100%' }}>
          {message}
        </Alert>
      </Snackbar>
    </>
  );
};

export default GlobalShareAction;
