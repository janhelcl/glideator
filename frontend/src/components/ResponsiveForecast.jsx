import React, { useState, useEffect } from 'react';
import { Button, Box, Collapse } from '@mui/material';
import D3Forecast from './D3Forecast';
import { fetchSiteForecast } from '../api';

const ResponsiveForecast = ({ siteId, queryDate }) => {
  // State to toggle forecast visibility
  const [showForecast, setShowForecast] = useState(false);
  // Hold the fetched forecast data
  const [forecastData, setForecastData] = useState(null);
  const [error, setError] = useState(null);
  // Selected forecast hour (9, 12, or 15)
  const [selectedHour, setSelectedHour] = useState(9);

  // Fetch forecast data when siteId or queryDate changes
  useEffect(() => {
    const loadForecast = async () => {
      try {
        const data = await fetchSiteForecast(siteId, queryDate);
        setForecastData(data);
      } catch (err) {
        console.error("Error fetching forecast:", err);
        setError("Failed to load forecast data.");
      }
    };

    if (siteId && queryDate) {
      loadForecast();
    }
  }, [siteId, queryDate]);

  const renderForecast = () => {
    if (!forecastData) {
      return <Box>Loading forecast data...</Box>;
    }

    const forecast = forecastData[`forecast_${selectedHour}`];
    if (!forecast) {
      return <Box>No forecast data available for hour {selectedHour}.</Box>;
    }

    return (
      <Box sx={{ width: '100%', mt: 2 }}>
        <D3Forecast forecast={forecast} selectedHour={selectedHour} />
      </Box>
    );
  };

  return (
    <Box
      sx={{
        my: 2,
        p: 2,
        border: '1px solid #e0e0e0',
        borderRadius: 1,
        boxShadow: 1,
        bgcolor: 'background.paper',
        width: '100%',
        overflow: 'visible',
      }}
    >
      <Button
        variant="contained"
        onClick={() => setShowForecast(!showForecast)}
        fullWidth
        sx={{ mb: showForecast ? 2 : 0 }}
      >
        {showForecast ? "Hide GFS Forecast" : "Show GFS Forecast"}
      </Button>
      
      <Collapse in={showForecast}>
        <Box 
          sx={{ 
            mt: 2,
            width: '100%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
          }}
        >
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'center',
              gap: 1,
              mb: 2,
              width: '100%',
            }}
          >
            {[9, 12, 15].map((hour) => (
              <Button
                key={hour}
                variant={selectedHour === hour ? "contained" : "outlined"}
                onClick={() => setSelectedHour(hour)}
              >
                {hour}:00
              </Button>
            ))}
          </Box>
          <Box 
            sx={{ 
              width: '100%',
              minHeight: '550px',
              overflow: 'visible',
            }}
          >
            {error ? <Box>{error}</Box> : renderForecast()}
          </Box>
        </Box>
      </Collapse>
    </Box>
  );
};

export default ResponsiveForecast; 