import React, { useState, useEffect } from 'react';
import { useParams, useLocation } from 'react-router-dom';
import { fetchSitePredictions } from '../api';
import Plot from 'react-plotly.js';
import { CircularProgress, Box, FormControl, InputLabel, Select, MenuItem, Checkbox, ListItemText, OutlinedInput } from '@mui/material';

const Details = () => {
  const { siteName } = useParams();
  const location = useLocation();
  const [predictions, setPredictions] = useState([]);
  const [selectedDate, setSelectedDate] = useState('');
  const [filteredMetrics, setFilteredMetrics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [availableDates, setAvailableDates] = useState([]);
  const [uniqueMetrics, setUniqueMetrics] = useState([]);
  const [selectedMetrics, setSelectedMetrics] = useState([]);

  // Get today's date in 'YYYY-MM-DD' format
  const today = new Date().toISOString().split('T')[0];

  // Parse query parameters for 'date' and 'metric'
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const date = params.get('date');
    const metric = params.get('metric');

    const loadPredictions = async () => {
      setLoading(true);
      const data = await fetchSitePredictions(siteName);
      
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

      // Extract unique metrics
      const metrics = [...new Set(filteredData.map((pred) => pred.metric))];
      setUniqueMetrics(metrics);
      
      // Set selectedMetrics based on the 'metric' query parameter
      if (metric && metrics.includes(metric)) {
        setSelectedMetrics([metric]);
      } else if (metrics.length > 0) {
        setSelectedMetrics([metrics[0]]); // Select the first metric by default
      } else {
        setSelectedMetrics([]);
      }

      setLoading(false);
    };

    loadPredictions();
  }, [siteName, location.search, today]);

  useEffect(() => {
    if (selectedDate) {
      const metricsForDate = predictions.filter(
        (pred) => pred.date === selectedDate
      );
      setFilteredMetrics(metricsForDate);
    } else {
      setFilteredMetrics([]);
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

  return (
    <div>
      <h1>Details for {siteName}</h1>
      
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

      {/* Bar Chart */}
      {filteredMetrics.length > 0 ? (
        <Plot
          data={[
            {
              type: 'bar',
              x: filteredMetrics.map((m) => m.metric),
              y: filteredMetrics.map((m) => m.value),
              marker: {
                color: '#1f77b4',
              },
              customdata: customHoverData,
              hovertemplate: '%{customdata}<extra></extra>',
              text: filteredMetrics.map((m) => `${m.value}%`),
              textposition: 'auto',
            },
          ]}
          layout={{
            title: `Glideator Flyability Forecast for ${selectedDate} at ${siteName}`,
            xaxis: { title: 'XC Points' },
            yaxis: { title: 'Probability (%)', range: [0, 100], tickformat: 'd' },
            bargap: 0,
            hovermode: 'closest',
          }}
        />
      ) : (
        <p>Please select a date to view the metrics.</p>
      )}

      {/* Line Chart */}
      {selectedMetrics.length > 0 && (
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
            showlegend: true, // Ensures the legend is always displayed
          }}
        />
      )}
    </div>
  );
};

export default Details;