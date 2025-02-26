import React, { useMemo } from 'react';
import { Box, Typography } from '@mui/material';
import MapView from './MapView';
import './DateBoxes.css';

const DateBoxes = ({
  dates,
  selectedDate,
  setSelectedDate,
  center,
  zoom,
  bounds,
  allSites,
  selectedMetric,
  metrics,
}) => {
  const metricIndexMap = useMemo(() => {
    return metrics.reduce((acc, metric, index) => {
      acc[metric] = index;
      return acc;
    }, {});
  }, [metrics]);

  return (
    <Box className="date-boxes-container">
      {dates.map((date) => {
        // Filter sites based on the specific date and selected metric
        const filteredSites = allSites.filter((site) => {
          const predictionForDate = site.predictions.find(pred => pred.date === date);
          if (!predictionForDate || !Array.isArray(predictionForDate.values)) {
            return false;
          }
          const metricIdx = metricIndexMap[selectedMetric];
          const value = predictionForDate.values[metricIdx];
          return value !== undefined && value !== null;
        });

        return (
          <Box
            key={date}
            className={`date-box ${selectedDate === date ? 'selected' : ''}`}
            onClick={() => setSelectedDate(date)}
          >
            <Typography variant="subtitle2" sx={{ marginBottom: '4px' }}>
              {date}
            </Typography>
            <MapView
              sites={filteredSites}
              selectedMetric={selectedMetric}
              selectedDate={date}
              center={center}
              zoom={zoom + 1}
              bounds={bounds}
              isSmallMap
              metrics={metrics}
            />
          </Box>
        );
      })}
    </Box>
  );
};

export default DateBoxes;