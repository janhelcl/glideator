import React, { useState, useEffect, useRef } from 'react';
import Controls from '../components/Controls';
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
  const [sites, setSites] = useState([]);
  const [loading, setLoading] = useState(false);

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
  }, [selectedDate]); // Add selectedDate as a dependency

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

  const loadSites = async () => {
    setLoading(true);
    const data = await fetchSites(selectedMetric, selectedDate);
    setSites(data);
    setLoading(false);
  };

  // Load sites whenever selectedMetric or selectedDate changes
  useEffect(() => {
    if (selectedDate) {
      loadSites();
    }
  }, [selectedMetric, selectedDate]); // Removed loadSites from dependencies

  return (
    <div>
      <h1>Paragliding Site Recommendations</h1>
      <Controls
        metrics={METRICS}
        selectedMetric={selectedMetric}
        setSelectedMetric={setSelectedMetric}
        dates={dates}
        selectedDate={selectedDate}
        setSelectedDate={setSelectedDate}
      />
      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" height="60vh">
          <CircularProgress />
        </Box>
      ) : (
        <MapView
          sites={sites}
          selectedMetric={selectedMetric}
          selectedDate={selectedDate}
        />
      )}
    </div>
  );
}

export default Home;