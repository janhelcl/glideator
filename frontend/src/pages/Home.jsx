import React, { useState, useEffect } from 'react';
import Controls from '../components/Controls';
import MapView from '../components/MapView';
import { fetchSites } from '../api';
import { CircularProgress, Box } from '@mui/material';

const Home = () => {
  const [metrics] = useState(['XC0', 'XC10', 'XC20', 'XC30', 'XC40', 'XC50']);
  const [selectedMetric, setSelectedMetric] = useState('XC0');
  const [dates, setDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState('');
  const [sites, setSites] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Generate dates for the next 7 days
    const generateDates = () => {
      const dateList = [];
      for (let i = 0; i < 7; i++) {
        const date = new Date();
        date.setDate(date.getDate() + i);
        dateList.push(date.toISOString().split('T')[0]);
      }
      setDates(dateList);
      setSelectedDate(dateList[0]); // Set the first date as default
    };

    generateDates();
  }, []);

  const loadSites = async () => {
    setLoading(true);
    const data = await fetchSites(selectedMetric, selectedDate);
    setSites(data);
    setLoading(false);
  };

  useEffect(() => {
    if (selectedDate) {
      loadSites();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedMetric, selectedDate]);

  return (
    <div>
      <h1>Paragliding Site Recommendations</h1>
      <Controls
        metrics={metrics}
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
        <MapView sites={sites} selectedMetric={selectedMetric} />
      )}
    </div>
  );
};

export default Home;