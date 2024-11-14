import React, { useState, useEffect, useRef, useMemo } from 'react';
import DateBoxes from '../components/DateBoxes';
import MapView from '../components/MapView';
import { fetchSites } from '../api';
import { CircularProgress, Box } from '@mui/material';
import { useNavigate, useLocation } from 'react-router-dom';

// Define metrics outside the component to maintain a stable reference
const METRICS = ['XC0', 'XC10', 'XC20', 'XC30', 'XC40', 'XC50'];

const Home = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const isFirstRender = useRef(true);

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

    const result = allSites.filter((site) => {
      // Check if site has predictions
      if (!site.predictions || !Array.isArray(site.predictions)) {
        console.warn(`Site "${site.name}" has no predictions.`);
        return false;
      }

      // Find a prediction that matches both metric and date
      const hasMatchingPrediction = site.predictions.some(
        (pred) => pred.metric === selectedMetric && pred.date === selectedDate
      );

      if (hasMatchingPrediction) {
        console.log(`Site "${site.name}" matches the criteria.`);
      } else {
        console.log(`Site "${site.name}" does NOT match the criteria.`);
      }

      return hasMatchingPrediction;
    });

    console.log('Filtered Sites:', result);
    return result;
  }, [allSites, selectedMetric, selectedDate]);

  return (
    <div style={{ position: 'relative', height: '100vh' }}>
      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" height="80vh">
          <CircularProgress />
        </Box>
      ) : (
        <>
          <MapView
            sites={filteredSites}
            selectedMetric={selectedMetric}
            setSelectedMetric={setSelectedMetric}
            selectedDate={selectedDate}
            metrics={METRICS}
            center={mapState.center}
            zoom={mapState.zoom}
            setMapState={setMapState} // Used to update center and zoom
          />
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