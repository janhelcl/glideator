import React, { useState, useEffect, useRef } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import { fetchSitePredictions, fetchSiteForecast } from '../api';
import Plot from 'react-plotly.js';
import { CircularProgress, Box, FormControl, InputLabel, Select, MenuItem, Checkbox, ListItemText, OutlinedInput, Button } from '@mui/material';
import ForecastCharts from '../components/ForecastCharts';
import SiteDetails from '../components/SiteDetails';
import ResponsiveForecast from '../components/ResponsiveForecast';

const Details = () => {
  const { siteId } = useParams();
  const location = useLocation();
  const [predictions, setPredictions] = useState([]);
  const [selectedDate, setSelectedDate] = useState('');
  const [filteredMetrics, setFilteredMetrics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [availableDates, setAvailableDates] = useState([]);
  const [uniqueMetrics, setUniqueMetrics] = useState([]);
  const [selectedMetrics, setSelectedMetrics] = useState([]);
  const [gfsForecastAt, setGfsForecastAt] = useState(''); // New state for gfs_forecast_at
  const weatherRef = useRef(null); // Reference to Weather Forecast section

  // Retrieve query parameter "date" or default to today's date (YYYY-MM-DD)
  const searchParams = new URLSearchParams(window.location.search);
  const queryDate = searchParams.get('date') || new Date().toISOString().split('T')[0];

  // Get today's date in 'YYYY-MM-DD' format
  const today = new Date().toISOString().split('T')[0];

  // Parse query parameters for 'date' and 'metric'
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const date = params.get('date');
    const metric = params.get('metric');

    const loadPredictions = async () => {
      setLoading(true);
      const data = await fetchSitePredictions(siteId);
      
      // Filter out past dates and convert probabilities to percentages
      const filteredData = data
        .filter(pred => pred.date >= today)
        .map(pred => ({ ...pred, value: Math.round(pred.value * 100) }));
      
      setPredictions(filteredData);
      
      // Extract unique dates and sort them
      const dates = [...new Set(filteredData.map((pred) => pred.date))].sort();
      
      setAvailableDates(dates);
      
      if (date && dates.includes(date)) {
        setSelectedDate(date);
      } else if (dates.length > 0) {
        setSelectedDate(dates[0]); // Set the first date as default
      }

      // Extract unique metrics and sort them numerically
      const metrics = [...new Set(filteredData.map((pred) => pred.metric))];
      const sortedMetrics = metrics.sort((a, b) => {
        const numA = parseInt(a.replace('XC', ''), 10);
        const numB = parseInt(b.replace('XC', ''), 10);
        return numA - numB;
      });
      setUniqueMetrics(sortedMetrics);
      
      // Set selectedMetrics based on the 'metric' query parameter
      if (metric && sortedMetrics.includes(metric)) {
        setSelectedMetrics([metric]);
      } else if (sortedMetrics.length > 0) {
        setSelectedMetrics([sortedMetrics[0]]); // Select the first metric by default
      } else {
        setSelectedMetrics([]);
      }

      setLoading(false);
    };

    loadPredictions();
  }, [siteId, location.search, today]);

  useEffect(() => {
    if (selectedDate) {
      const metricsForDate = predictions.filter(
        (pred) => pred.date === selectedDate
      );
      setFilteredMetrics(metricsForDate);

      // Since gfs_forecast_at is constant across metrics for the selected date,
      // we can safely take it from the first metric
      if (metricsForDate.length > 0) {
        setGfsForecastAt(metricsForDate[0].gfs_forecast_at);
      } else {
        setGfsForecastAt('');
      }
    } else {
      setFilteredMetrics([]);
      setGfsForecastAt('');
    }
  }, [selectedDate, predictions]);

  const handleDateChange = (event) => {
    setSelectedDate(event.target.value);
  };

  const handleMetricsChange = (event) => {
    const { value } = event.target;
    setSelectedMetrics(
      typeof value === 'string' ? value.split(',') : value,
    );
  };

  const scrollToWeather = () => {
    if (weatherRef.current) {
      weatherRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="60vh">
        <CircularProgress />
      </Box>
    );
  }

  // Generate custom hover data for bar chart tooltips
  const customHoverData = filteredMetrics.map((m) => {
    if (m.metric === 'XC0') {
      return `Probability of observing a flight is ${m.value}%`;
    } else {
      const number = m.metric.replace('XC', '');
      return `Probability of observing a flight exceeding ${number} points is ${m.value}%`;
    }
  });

  // Sort metrics numerically for the bar chart
  const sortedFilteredMetrics = [...filteredMetrics].sort((a, b) => {
    const numA = parseInt(a.metric.replace('XC', ''), 10);
    const numB = parseInt(b.metric.replace('XC', ''), 10);
    return numA - numB;
  });

  // Format the gfs_forecast_at date string
  const formattedGfsForecastAt = gfsForecastAt
    ? new Date(gfsForecastAt).toLocaleString()
    : 'N/A';

  return (
    <div style={{ overflowY: 'auto', height: '100vh', padding: '20px' }}>
      <SiteDetails />
      <h1>Details for {siteId}</h1>
      
      {/* Updated Subtitle */}
      <h2>Based on NOAA GFS forecast at: {formattedGfsForecastAt}</h2>
      
      {/* Controls */}
      <Box display="flex" flexWrap="wrap" alignItems="center">
        {/* Date Selector */}
        <FormControl sx={{ m: 1, minWidth: 200 }}>
          <InputLabel>Select Date</InputLabel>
          <Select
            value={selectedDate}
            onChange={handleDateChange}
            label="Select Date"
          >
            {availableDates.map((date) => (
              <MenuItem key={date} value={date}>
                {date}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        
        {/* Metrics Selector for Line Chart */}
        <FormControl sx={{ m: 1, minWidth: 200 }}>
          <InputLabel>Metrics</InputLabel>
          <Select
            multiple
            value={selectedMetrics}
            onChange={handleMetricsChange}
            input={<OutlinedInput label="Metrics" />}
            renderValue={(selected) => selected.join(', ')}
          >
            {uniqueMetrics.map((metric) => (
              <MenuItem key={metric} value={metric}>
                <Checkbox checked={selectedMetrics.indexOf(metric) > -1} />
                <ListItemText primary={metric} />
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        {/* Button to Skip to Weather Forecast */}
        <Button variant="contained" color="primary" sx={{ m: 1 }} onClick={scrollToWeather}>
          Skip to Weather Forecast
        </Button>
      </Box>

      {/* Flyability Charts */}
      <Box display="flex" flexWrap="wrap" justifyContent="space-around" className="flyability-charts">
        {/* Bar Chart */}
        {sortedFilteredMetrics.length > 0 && (
          <Box className="plot-container">
            <Plot
              data={[
                {
                  type: 'bar',
                  x: sortedFilteredMetrics.map((m) => m.metric),
                  y: sortedFilteredMetrics.map((m) => m.value),
                  marker: {
                    color: '#1f77b4',
                  },
                  customdata: customHoverData,
                  hovertemplate: '%{customdata}<extra></extra>',
                  text: sortedFilteredMetrics.map((m) => `${m.value}%`),
                  textposition: 'auto',
                },
              ]}
              layout={{
                title: `Glideator Flyability Forecast for ${selectedDate} at Site ID ${siteId}`,
                xaxis: { title: 'XC Points' },
                yaxis: { title: 'Probability (%)', range: [0, 100], tickformat: 'd' },
                bargap: 0,
                hovermode: 'closest',
              }}
            />
          </Box>
        )}

        {/* Line Chart */}
        {selectedMetrics.length > 0 && (
          <Box className="plot-container">
            <Plot
              data={selectedMetrics.map((metric) => {
                const metricData = predictions
                  .filter((p) => p.metric === metric && p.date >= today)
                  .sort((a, b) => new Date(a.date) - new Date(b.date));
                return {
                  x: metricData.map((p) => p.date),
                  y: metricData.map((p) => p.value),
                  type: 'scatter',
                  mode: 'lines+markers',
                  name: metric,
                  hovertemplate: `${metric}<br>Date: %{x}<br>Value: %{y}%<extra></extra>`,
                };
              })}
              layout={{
                title: 'Glideator Flyability Forecast Over Time',
                xaxis: { title: 'Date', type: 'date' },
                yaxis: { title: 'Probability (%)', range: [0, 100], tickformat: 'd' },
                hovermode: 'x unified',
                showlegend: true,
              }}
            />
          </Box>
        )}
      </Box>

      {/* Weather Forecast Section */}
      <Box ref={weatherRef} className="weather-forecast">
        <ResponsiveForecast siteId={siteId} queryDate={queryDate} />
      </Box>
    </div>
  );
};

export default Details;
