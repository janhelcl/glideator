import React from 'react';
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
  return (
    <Box className="date-boxes-container">
      {dates.map((date) => {
        // Filter sites based on the specific date
        const filteredSites = allSites.filter((site) =>
          site.predictions.some(
            (pred) => pred.metric === selectedMetric && pred.date === date
          )
        );

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