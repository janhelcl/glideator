import React, { useState, useEffect, useRef, useMemo, Suspense } from 'react';
import SuspenseDateBoxes from '../components/SuspenseDateBoxes';
import DateBoxesPlaceholder from '../components/DateBoxesPlaceholder';
import ErrorBoundary from '../components/ErrorBoundary';
import MapView from '../components/MapView';
import { fetchSites } from '../api';
import { Box } from '@mui/material';
import LoadingSpinner from '../components/LoadingSpinner';
import { useNavigate, useLocation, useOutletContext } from 'react-router-dom';
import { createSitesResource } from '../utils/suspenseResource';

// Define metrics outside the component to maintain a stable reference
const METRICS = ['XC0', 'XC10', 'XC20', 'XC30', 'XC40', 'XC50', 'XC60', 'XC70', 'XC80', 'XC90', 'XC100'];

const metricIndexMap = METRICS.reduce((acc, metric, index) => {
  acc[metric] = index;
  return acc;
}, {});

// Create a sites resource outside the component to avoid recreation on renders
const sitesResource = createSitesResource(fetchSites);

const Home = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const isFirstRender = useRef(true);
  const { selectedSite } = useOutletContext();
  const markerRefs = useRef({});
  const mapRef = useRef();

  const [selectedMetric, setSelectedMetric] = useState(() => {
    const params = new URLSearchParams(location.search);
    const metric = params.get('metric');
    return metric && METRICS.includes(metric) ? metric : 'XC0';
  });
  const [dates, setDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState(() => {
    const params = new URLSearchParams(location.search);
    return params.get('date') || '';
  });
  const [allSites, setAllSites] = useState([]); // Store all fetched sites
  const [loading, setLoading] = useState(false);

  // Shared map state excluding bounds
  const [mapState, setMapState] = useState({
    center: [45.8403, 10.7336], // Default center changed
    zoom: 6,
    bounds: null
  });

  // Attempt geolocation on mount if no location is in URL params
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const urlLat = params.get('lat');
    const urlLng = params.get('lng');

    if (!urlLat && !urlLng && "geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          setMapState(prevState => ({ ...prevState, center: [latitude, longitude] }));
        },
        (error) => {
          console.warn("Geolocation failed or denied:", error);
          // Keep the default center if geolocation fails
        }
      );
    }
  }, [location.search]); // Run only when search params change (effectively once on mount unless URL changes externally)

  // Generate dates and set initial values
  useEffect(() => {
    const generateDates = () => {
      const dateList = [];
      const today = new Date();
      for (let i = 0; i < 7; i++) {
        const dateObj = new Date(today);
        dateObj.setDate(today.getDate() + i);
        dateList.push(dateObj.toISOString().split('T')[0]);
      }
      setDates(dateList);

      if (!selectedDate || !dateList.includes(selectedDate)) {
        setSelectedDate(dateList[0]);
      }
    };

    generateDates();
  }, [selectedDate]);

  // Update query parameters when selectedMetric or selectedDate changes, preserving mapType
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    
    // Use the current URL parameters (including mapType) as a starting point
    const currentParams = new URLSearchParams(location.search);
    currentParams.set('metric', selectedMetric);
    currentParams.set('date', selectedDate);
    
    navigate(`/?${currentParams.toString()}`, { replace: true });
  }, [selectedMetric, selectedDate, navigate, location.search]);

  // Fetch for the main map only (Suspense will handle date boxes data)
  useEffect(() => {
    const loadMainMapSites = async () => {
      setLoading(true);
      try {
        // We don't call fetchSites directly anymore for the all sites data
        // That's handled by the Suspense resource
        // This is just for the current selected data for main map
        const data = await fetchSites();
        if (Array.isArray(data)) {
          setAllSites(data);
        } else {
          console.error('Fetched data is not an array:', data);
        }
      } catch (error) {
        console.error('Error fetching sites for main map:', error);
      }
      setLoading(false);
    };

    loadMainMapSites();
  }, []);

  // Derive filtered sites based on selectedMetric and selectedDate
  const filteredSites = useMemo(() => {
    console.log('Selected Metric:', selectedMetric);
    console.log('Selected Date:', selectedDate);

    const metricIdx = metricIndexMap[selectedMetric];

    const result = allSites.filter((site) => {
      // Check if site has predictions
      if (!site.predictions || !Array.isArray(site.predictions)) {
        console.warn(`Site "${site.name}" has no predictions.`);
        return false;
      }

      // Find a prediction that matches the selected date
      const predictionForDate = site.predictions.find(pred => pred.date === selectedDate);
      if (!predictionForDate || !Array.isArray(predictionForDate.values)) {
        console.warn(`Site "${site.name}" has no predictions for date ${selectedDate}.`);
        return false;
      }

      // Get the value for the selected metric based on its index
      const value = predictionForDate.values[metricIdx];
      if (value !== undefined && value !== null) {
        console.log(`Site "${site.name}" matches the criteria with value ${value}.`);
        return true;
      } else {
        console.log(`Site "${site.name}" does NOT match the criteria.`);
        return false;
      }
    });

    console.log('Filtered Sites:', result);
    return result;
  }, [allSites, selectedMetric, selectedDate]);

  // Update the effect to handle map centering
  useEffect(() => {
    if (selectedSite && mapRef && mapRef.current) {
      try {
        // Center map on selected site
        mapRef.current.setView(
          [selectedSite.latitude, selectedSite.longitude],
          mapRef.current.getZoom()  // Maintain current zoom level
        );

        // Open the popup
        const markerRef = markerRefs.current[selectedSite.site_id];
        if (markerRef) {
          markerRef.openPopup();
        }
      } catch (error) {
        console.error("Error updating map view:", error);
      }
    }
  }, [selectedSite]);

  // Add this to your MapView component props
  const getMarkerRef = (siteId, ref) => {
    markerRefs.current[siteId] = ref;
  };

  return (
    <div style={{ 
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      overflow: 'hidden'
    }}>
      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" height="100%">
          <LoadingSpinner />
        </Box>
      ) : (
        <>
          <Box sx={{ 
            flex: 1,
            position: 'relative',
            overflow: 'hidden'
          }}>
            <MapView
              sites={filteredSites}
              selectedMetric={selectedMetric}
              setSelectedMetric={setSelectedMetric}
              selectedDate={selectedDate}
              metrics={METRICS}
              center={mapState.center}
              zoom={mapState.zoom}
              setMapState={setMapState}
              bounds={mapState.bounds}
              getMarkerRef={getMarkerRef}
              mapRef={mapRef}
            />
          </Box>
          
          {/* Replace direct DateBoxes rendering with Suspense-wrapped component */}
          <ErrorBoundary>
            <Suspense fallback={<DateBoxesPlaceholder />}>
              <SuspenseDateBoxes
                sitesResource={sitesResource}
                dates={dates}
                selectedDate={selectedDate}
                setSelectedDate={setSelectedDate}
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
    </div>
  );
};

export default Home;