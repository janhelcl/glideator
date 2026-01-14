import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Button,
  ButtonGroup,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { fetchSimilarDays, fetchPastDateForecast } from '../api';
import D3Forecast from './D3Forecast';
import LoadingSpinner from './LoadingSpinner';

const SimilarDaysPanel = ({ siteId, selectedDate, latitude, longitude }) => {
  const [similarDays, setSimilarDays] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Track which accordion is expanded
  const [expandedAccordion, setExpandedAccordion] = useState(null);
  
  // Track forecast data for each past date
  const [forecastData, setForecastData] = useState({});
  
  // Track loading state for each past date
  const [forecastLoading, setForecastLoading] = useState({});
  
  // Track selected hour for each past date (default to 12)
  const [selectedHours, setSelectedHours] = useState({});

  // Fetch similar days when component mounts or selectedDate changes
  useEffect(() => {
    const loadSimilarDays = async () => {
      if (!selectedDate || !siteId) return;
      
      try {
        setLoading(true);
        setError(null);
        const data = await fetchSimilarDays(siteId, selectedDate, 3);
        setSimilarDays(data.similar_days || []);
        
        // Initialize selected hours to 12 for all dates
        const initialHours = {};
        (data.similar_days || []).forEach(day => {
          initialHours[day.past_date] = 12;
        });
        setSelectedHours(initialHours);
      } catch (err) {
        console.error('Error fetching similar days:', err);
        setError('Failed to load similar days');
        setSimilarDays([]);
      } finally {
        setLoading(false);
      }
    };

    loadSimilarDays();
  }, [siteId, selectedDate]);

  // Fetch forecast data when an accordion is expanded
  const handleAccordionChange = async (pastDate) => {
    const isExpanding = expandedAccordion !== pastDate;
    setExpandedAccordion(isExpanding ? pastDate : null);
    
    // If expanding and we don't have forecast data yet, fetch it
    if (isExpanding && !forecastData[pastDate]) {
      try {
        setForecastLoading(prev => ({ ...prev, [pastDate]: true }));
        const data = await fetchPastDateForecast(siteId, selectedDate, pastDate);
        setForecastData(prev => ({ ...prev, [pastDate]: data }));
      } catch (err) {
        console.error(`Error fetching forecast for ${pastDate}:`, err);
      } finally {
        setForecastLoading(prev => ({ ...prev, [pastDate]: false }));
      }
    }
  };

  // Handle hour change for a specific past date
  const handleHourChange = (pastDate, hour) => {
    setSelectedHours(prev => ({ ...prev, [pastDate]: hour }));
  };

  // Format date for display
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    });
  };

  // Generate xcontest link
  const getXContestLink = (pastDate) => {
    return `https://www.xcontest.org/world/cs/vyhledavani-preletu/?list[sort]=pts&filter[point]=${longitude}+${latitude}&filter[radius]=5000&filter[date]=${pastDate}`;
  };

  // Render forecast content for a past date
  const renderForecastContent = (pastDate) => {
    if (forecastLoading[pastDate]) {
      return (
        <Box display="flex" justifyContent="center" p={3}>
          <LoadingSpinner />
        </Box>
      );
    }

    const forecast = forecastData[pastDate];
    if (!forecast) {
      return (
        <Typography color="error" align="center">
          Failed to load forecast data
        </Typography>
      );
    }

    const selectedHour = selectedHours[pastDate] || 12;
    const currentForecast = forecast[`forecast_${selectedHour}`];
    
    if (!currentForecast) {
      return (
        <Typography color="warning" align="center">
          No forecast data available for hour {selectedHour}
        </Typography>
      );
    }

    return (
      <Box sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        width: '100%',
      }}>
        <ButtonGroup 
          variant="contained" 
          sx={{ 
            minWidth: 'min-content',
            mb: 1
          }}
        >
          {[9, 12, 15].map((hour) => (
            <Button
              key={hour}
              onClick={() => handleHourChange(pastDate, hour)}
              variant={selectedHour === hour ? "contained" : "outlined"}
            >
              {hour}:00
            </Button>
          ))}
        </ButtonGroup>
        
        <Box sx={{ 
          width: '100%',
          aspectRatio: '1/1',
          maxHeight: 'calc(100vh - 300px)',
          maxWidth: '1000px',
          position: 'relative'
        }}>
          <D3Forecast 
            forecast={currentForecast} 
            selectedHour={selectedHour}
            date={forecast.past_date}
          />
        </Box>
      </Box>
    );
  };

  // Don't render if loading initially
  if (loading) {
    return null;
  }

  // Don't render if there are no similar days or error
  if (error || !similarDays || similarDays.length === 0) {
    return null;
  }

  // Get rank label
  const getRankLabel = (index) => {
    const labels = ['Best Match', '2nd Best', '3rd Best'];
    return labels[index] || `#${index + 1}`;
  };

  return (
    <Box sx={{ mt: 4 }}>
      <Typography variant="h6" gutterBottom>
        Similar Days in the Past
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Compare with days that had similar atmospheric conditions to see what flights were possible.
      </Typography>

      {similarDays.map((day, index) => (
        <Accordion
          key={day.past_date}
          expanded={expandedAccordion === day.past_date}
          onChange={() => handleAccordionChange(day.past_date)}
          sx={{ mb: 1 }}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            sx={{
              '& .MuiAccordionSummary-content': {
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 1,
                flexWrap: 'wrap',
              }
            }}
          >
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <Typography
                variant="caption"
                sx={{
                  bgcolor: index === 0 ? 'primary.main' : 'grey.500',
                  color: 'white',
                  px: 1,
                  py: 0.25,
                  borderRadius: 1,
                  fontWeight: 500,
                  whiteSpace: 'nowrap',
                }}
              >
                {getRankLabel(index)}
              </Typography>
              <Typography>{formatDate(day.past_date)}</Typography>
            </Box>
            <Button
              size="small"
              variant="outlined"
              href={getXContestLink(day.past_date)}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              startIcon={<OpenInNewIcon fontSize="small" />}
              sx={{ whiteSpace: 'nowrap' }}
            >
              View Flights
            </Button>
          </AccordionSummary>

          <AccordionDetails>
            {renderForecastContent(day.past_date)}
          </AccordionDetails>
        </Accordion>
      ))}
    </Box>
  );
};

export default SimilarDaysPanel;

