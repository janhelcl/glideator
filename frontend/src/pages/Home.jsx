import React, { useState, useEffect, useRef, useMemo } from 'react';
import DateBoxes from '../components/DateBoxes';
import MapView from '../components/MapView';
import { fetchSites } from '../api';
import { CircularProgress, Box } from '@mui/material';
import { useNavigate, useLocation, useOutletContext } from 'react-router-dom';

// Define metrics outside the component to maintain a stable reference
const METRICS = ['XC0', 'XC10', 'XC20', 'XC30', 'XC40', 'XC50', 'XC60', 'XC70', 'XC80', 'XC90', 'XC100'];

const metricIndexMap = METRICS.reduce((acc, metric, index) => {
  acc[metric] = index;
  return acc;
}, {});

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
    center: [50.0755, 14.4378],
    zoom: 7,
    bounds: null
  });

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

  // Update query parameters when selectedMetric or selectedDate changes
  useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }

    const newParams = new URLSearchParams();
    newParams.set('metric', selectedMetric);
    newParams.set('date', selectedDate);
    navigate(`/?${newParams.toString()}`, { replace: true });
  }, [selectedMetric, selectedDate, navigate]);

  // Fetch all sites once on component mount
  useEffect(() => {
    const loadAllSites = async () => {
      setLoading(true);
      try {
        const data = await fetchSites(); // Fetch without filters
        if (Array.isArray(data)) {
          // Optional: Log fetched data for debugging
          console.log('Fetched Sites:', data);

          setAllSites(data);
        } else {
          console.error('Fetched data is not an array:', data);
        }
      } catch (error) {
        console.error('Error fetching sites:', error);
      }
      setLoading(false);
    };

    loadAllSites();
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
    if (selectedSite && mapRef.current) {
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
    }
  }, [selectedSite]);

  // Add this to your MapView component props
  const getMarkerRef = (siteId, ref) => {
    markerRefs.current[siteId] = ref;
  };

  return (
    <div style={{ 
      position: 'relative', 
      height: 'calc(100vh - var(--header-height, 94px))',
      margin: 0,
      padding: 0,
      overflow: 'hidden',
      width: '100%',
      display: 'flex',
      flexDirection: 'column'
    }}>
      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" height="100%">
          <CircularProgress />
        </Box>
      ) : (
        <>
          <Box sx={{ 
            position: 'relative',
            flex: 1,
            minHeight: 0,
            width: '100%'
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
          <DateBoxes
            dates={dates}
            selectedDate={selectedDate}
            setSelectedDate={setSelectedDate}
            center={mapState.center}
            zoom={mapState.zoom}
            bounds={mapState.bounds}
            allSites={allSites}
            selectedMetric={selectedMetric}
            metrics={METRICS}
          />
        </>
      )}
    </div>
  );
};

export default Home;