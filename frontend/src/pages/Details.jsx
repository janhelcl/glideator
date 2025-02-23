import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import D3Forecast from '../components/D3Forecast';
import { fetchSiteForecast } from '../api';
import { 
  Box, 
  Button, 
  ButtonGroup,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  CircularProgress
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

const Details = () => {
  const { siteId } = useParams();
  const [forecast, setForecast] = useState(null);
  const [selectedHour, setSelectedHour] = useState(9);
  const [loading, setLoading] = useState(true);
  const queryDate = new Date().toISOString().split('T')[0];

  useEffect(() => {
    const loadForecast = async () => {
      try {
        setLoading(true);
        const data = await fetchSiteForecast(siteId, queryDate);
        setForecast(data);
      } catch (err) {
        console.error('Error fetching forecast:', err);
      } finally {
        setLoading(false);
      }
    };

    loadForecast();
  }, [siteId, queryDate]);

  const renderForecastContent = () => {
    if (loading) {
      return (
        <Box display="flex" justifyContent="center" p={3}>
          <CircularProgress />
        </Box>
      );
    }

    if (!forecast) {
      return (
        <Typography color="error" align="center">
          Failed to load forecast data
        </Typography>
      );
    }

    const currentForecast = forecast[`forecast_${selectedHour}`];
    if (!currentForecast) {
      return (
        <Typography color="warning" align="center">
          No forecast data available for hour {selectedHour}
        </Typography>
      );
    }

    return (
      <>
        <ButtonGroup 
          variant="contained" 
          sx={{ alignSelf: 'center', mb: 2 }}
        >
          {[9, 12, 15].map((hour) => (
            <Button
              key={hour}
              onClick={() => setSelectedHour(hour)}
              variant={selectedHour === hour ? "contained" : "outlined"}
            >
              {hour}:00
            </Button>
          ))}
        </ButtonGroup>
        
        <Box sx={{ 
          height: '600px',
          position: 'relative'
        }}>
          <D3Forecast 
            forecast={currentForecast} 
            selectedHour={selectedHour}
          />
        </Box>
      </>
    );
  };

  return (
    <Box sx={{ 
      maxWidth: '1200px',
      margin: '0 auto',
      p: 2,
    }}>
      {/* Site Information Section */}
      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">Site Information</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Typography>
            Site details coming soon...
          </Typography>
        </AccordionDetails>
      </Accordion>

      {/* Weather Forecast Section */}
      <Accordion defaultExpanded>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">Weather Forecast</Typography>
        </AccordionSummary>
        <AccordionDetails>
          {renderForecastContent()}
        </AccordionDetails>
      </Accordion>

      {/* Flight Statistics Section */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">Flight Statistics</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Typography>
            Flight statistics coming soon...
          </Typography>
        </AccordionDetails>
      </Accordion>

      {/* Historical Data Section */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">Historical Data</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Typography>
            Historical data coming soon...
          </Typography>
        </AccordionDetails>
      </Accordion>
    </Box>
  );
};

export default Details;
