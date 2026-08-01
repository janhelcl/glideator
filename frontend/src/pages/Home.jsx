import React, {
  useState,
  useEffect,
  useRef,
  useMemo,
  Suspense,
  useCallback,
} from 'react';
import { useQuery } from '@tanstack/react-query';
import SuspenseDateBoxes from '../components/SuspenseDateBoxes';
import DateBoxesPlaceholder from '../components/DateBoxesPlaceholder';
import ErrorBoundary from '../components/ErrorBoundary';
import { fetchSites } from '../api';
import { Box } from '@mui/material';
import LoadingSpinner from '../components/LoadingSpinner';
import { useNavigate, useLocation, useOutletContext } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { useDefaultMetric } from '../hooks/useDefaultMetric';
import { trackEvent } from '../analytics';

const MapView = React.lazy(() => import('../components/MapView'));

const METRICS = ['XC0', 'XC10', 'XC20', 'XC30', 'XC40', 'XC50', 'XC60', 'XC70', 'XC80', 'XC90', 'XC100'];
const PUBLIC_ORIGIN = process.env.REACT_APP_PUBLIC_ORIGIN || 'https://www.parra-glideator.com';

const SCREEN_READER_ONLY = {
  position: 'absolute',
  width: '1px',
  height: '1px',
  padding: 0,
  margin: '-1px',
  overflow: 'hidden',
  clip: 'rect(0, 0, 0, 0)',
  whiteSpace: 'nowrap',
  border: 0,
};

const metricIndexMap = METRICS.reduce((acc, metric, index) => {
  acc[metric] = index;
  return acc;
}, {});

const fallbackDates = () => {
  const today = new Date();
  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(today);
    date.setUTCDate(today.getUTCDate() + index);
    return date.toISOString().split('T')[0];
  });
};

const ClientOnly = ({ children, fallback }) => {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return mounted ? children : fallback;
};

const Home = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const isFirstRender = useRef(true);
  const { selectedSite } = useOutletContext();
  const markerRefs = useRef({});
  const mapRef = useRef();
  const { preferredMetric } = useDefaultMetric();

  const sitesQuery = useQuery({
    queryKey: ['sites', 'map'],
    queryFn: ({ signal }) => fetchSites(null, null, 1000, { signal }),
  });
  const allSitesData = sitesQuery.data || [];

  const dates = useMemo(() => {
    const predictionDates = new Set();
    allSitesData.forEach((site) => {
      (site.predictions || []).forEach((prediction) => {
        if (prediction.date) predictionDates.add(prediction.date);
      });
    });
    const sortedDates = [...predictionDates].sort();
    return sortedDates.length ? sortedDates : fallbackDates();
  }, [allSitesData]);

  const [selectedMetric, setSelectedMetric] = useState(() => {
    const params = new URLSearchParams(location.search);
    const metric = params.get('metric');
    return metric && METRICS.includes(metric) ? metric : preferredMetric;
  });
  const [selectedDate, setSelectedDate] = useState(() => {
    const params = new URLSearchParams(location.search);
    const requestedDate = params.get('date');
    return requestedDate && dates.includes(requestedDate) ? requestedDate : dates[0];
  });

  const [mapState, setMapState] = useState({
    center: [45.8403, 10.7336],
    zoom: 6,
    bounds: null,
  });

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const urlLat = Number(params.get('lat'));
    const urlLng = Number(params.get('lng'));

    if (Number.isFinite(urlLat) && Number.isFinite(urlLng)) {
      setMapState((previous) => ({ ...previous, center: [urlLat, urlLng] }));
      return;
    }

    if (typeof navigator !== 'undefined' && 'geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          setMapState((previous) => ({ ...previous, center: [latitude, longitude] }));
        },
        (error) => {
          console.warn('Geolocation failed or denied:', error);
        },
      );
    }
  }, [location.search]);

  useEffect(() => {
    if (!selectedDate || !dates.includes(selectedDate)) {
      setSelectedDate(dates[0]);
    }
  }, [dates, selectedDate]);

  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }

    const currentParams = new URLSearchParams(location.search);
    currentParams.set('metric', selectedMetric);
    currentParams.set('date', selectedDate);

    navigate(`/?${currentParams.toString()}`, { replace: true });
  }, [selectedMetric, selectedDate, navigate, location.search]);

  const filteredSites = useMemo(() => {
    if (!selectedDate || !allSitesData.length) {
      return [];
    }

    const metricIdx = metricIndexMap[selectedMetric];
    if (metricIdx === undefined) {
      return [];
    }

    return allSitesData.filter((site) => {
      const predictionForDate = site.predictions?.find((prediction) => prediction.date === selectedDate);
      const value = predictionForDate?.values?.[metricIdx];
      return value !== undefined && value !== null;
    });
  }, [allSitesData, selectedMetric, selectedDate]);

  const rankedSites = useMemo(() => {
    const metricIdx = metricIndexMap[selectedMetric];
    return filteredSites
      .map((site) => {
        const prediction = site.predictions.find((item) => item.date === selectedDate);
        return {
          ...site,
          selectedPrediction: prediction,
          selectedProbability: prediction.values[metricIdx],
        };
      })
      .sort((left, right) => right.selectedProbability - left.selectedProbability);
  }, [filteredSites, selectedDate, selectedMetric]);

  useEffect(() => {
    if (selectedSite?.site_id && mapRef.current && allSitesData) {
      const fullSiteData = allSitesData.find((site) => site.site_id === selectedSite.site_id);

      if (fullSiteData) {
        try {
          mapRef.current.setView(
            [fullSiteData.latitude, fullSiteData.longitude],
            mapRef.current.getZoom(),
          );

          const markerRef = markerRefs.current[fullSiteData.site_id];
          if (markerRef) markerRef.openPopup();
        } catch (error) {
          console.error('Error updating map view:', error);
        }
      }
    }
  }, [selectedSite, allSitesData]);

  const getMarkerRef = (siteId, ref) => {
    markerRefs.current[siteId] = ref;
  };

  const handleMetricChange = useCallback((metric) => {
    if (metric !== selectedMetric) {
      trackEvent('map_metric_changed', {
        previous_metric: selectedMetric,
        metric,
      });
    }
    setSelectedMetric(metric);
  }, [selectedMetric]);

  const handleDateChange = useCallback((date) => {
    if (date !== selectedDate) {
      trackEvent('map_date_changed', {
        previous_date: selectedDate || null,
        date,
        metric: selectedMetric,
      });
    }
    setSelectedDate(date);
  }, [selectedDate, selectedMetric]);

  const mapFallback = (
    <Box display="flex" justifyContent="center" alignItems="center" height="100%">
      <LoadingSpinner />
    </Box>
  );

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      overflow: 'hidden',
    }}>
      <Helmet>
        <title>Parra-Glideator – Paragliding site forecasts and trip planning</title>
        <meta name="description" content="Find the best paragliding sites by date and flyability. Plan trips with real forecasts and historical activity." />
        <link rel="canonical" href={`${PUBLIC_ORIGIN}/`} />
        <meta property="og:title" content="Parra-Glideator" />
        <meta property="og:description" content="Plan your next paragliding adventure with Parra-Glideator." />
        <meta property="og:type" content="website" />
        <meta name="twitter:card" content="summary_large_image" />
        <script type="application/ld+json">{JSON.stringify({
          '@context': 'https://schema.org',
          '@type': 'WebSite',
          name: 'Parra-Glideator',
          url: `${PUBLIC_ORIGIN}/`,
          description: 'Paragliding site forecasts and trip planning.',
          inLanguage: 'en',
        })}</script>
      </Helmet>

      {rankedSites.length > 0 && (
        <Box component="section" sx={SCREEN_READER_ONLY}>
          <h1>Paragliding site forecasts for {selectedDate}</h1>
          <p>
            Sites are ranked by {selectedMetric}. XC0 is the probability of any recorded flying activity;
            higher XC thresholds represent increasingly ambitious flights. These predictions support planning
            and are not a safety guarantee.
          </p>
          <table aria-label={`Paragliding site ranking for ${selectedDate} using ${selectedMetric}`}>
            <caption>Current Parra-Glideator site ranking</caption>
            <thead>
              <tr>
                <th scope="col">Rank</th>
                <th scope="col">Site</th>
                <th scope="col">Date</th>
                <th scope="col">Metric</th>
                <th scope="col">Probability</th>
                <th scope="col">Forecast computed</th>
              </tr>
            </thead>
            <tbody>
              {rankedSites.map((site, index) => (
                <tr key={site.site_id}>
                  <td>{index + 1}</td>
                  <td>
                    <a href={`/details/${site.site_id}?date=${selectedDate}&metric=${selectedMetric}`}>
                      {site.name}
                    </a>
                  </td>
                  <td>{selectedDate}</td>
                  <td>{selectedMetric}</td>
                  <td>{Math.round(site.selectedProbability * 100)}%</td>
                  <td>{site.selectedPrediction.computed_at || 'Not provided'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Box>
      )}

      {sitesQuery.isPending ? mapFallback : (
        <>
          <Box sx={{
            flex: 1,
            position: 'relative',
            overflow: 'hidden',
          }}>
            <ClientOnly fallback={mapFallback}>
              <Suspense fallback={mapFallback}>
                <MapView
                  sites={filteredSites}
                  selectedMetric={selectedMetric}
                  setSelectedMetric={handleMetricChange}
                  selectedDate={selectedDate}
                  metrics={METRICS}
                  center={mapState.center}
                  zoom={mapState.zoom}
                  setMapState={setMapState}
                  bounds={mapState.bounds}
                  getMarkerRef={getMarkerRef}
                  mapRef={mapRef}
                />
              </Suspense>
            </ClientOnly>
          </Box>

          <ErrorBoundary>
            <Suspense fallback={<DateBoxesPlaceholder />}>
              <SuspenseDateBoxes
                allSites={allSitesData}
                dates={dates}
                selectedDate={selectedDate}
                setSelectedDate={handleDateChange}
                center={mapState.center}
                zoom={mapState.zoom}
                bounds={mapState.bounds}
                selectedMetric={selectedMetric}
                metrics={METRICS}
              />
            </Suspense>
          </ErrorBoundary>
        </>
      )}

      {sitesQuery.isError && (
        <Box sx={SCREEN_READER_ONLY} role="alert">
          Current site forecasts could not be loaded.
        </Box>
      )}
    </div>
  );
};

export default Home;
