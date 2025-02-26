import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import D3Forecast from '../components/D3Forecast';
import { fetchSiteForecast, fetchSites } from '../api';
import DateBoxes from '../components/DateBoxes';
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
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Get date and metric from URL or use defaults
  const initialDate = searchParams.get('date') || '';
  const initialMetric = searchParams.get('metric') || 'XC50';
  
  // State for site data and dates
  const [siteData, setSiteData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedDate, setSelectedDate] = useState(initialDate);
  const [selectedMetric] = useState(initialMetric);
  
  // Calculated values
  const allDates = useMemo(() => {
    if (!siteData || !siteData.length) return [];
    // Get all unique dates from the site's predictions
    const dates = siteData[0]?.predictions?.map(pred => pred.date) || [];
    return [...new Set(dates)].sort();
  }, [siteData]);
  
  // Effect to load site data
  useEffect(() => {
    const loadSiteData = async () => {
      try {
        setLoading(true);
        // Fetch site data without date filter to get all dates
        const data = await fetchSites(null, null);
        // Filter for just this site
        const filteredData = data.filter(site => site.site_id === parseInt(siteId));
        setSiteData(filteredData);
      } catch (err) {
        console.error('Error loading site data:', err);
        setError('Failed to load site data');
      } finally {
        setLoading(false);
      }
    };
    
    loadSiteData();
  }, [siteId]);
  
  // Set default date if none selected and data is loaded
  useEffect(() => {
    if (allDates.length && !selectedDate) {
      setSelectedDate(allDates[0]);
    }
  }, [allDates, selectedDate]);
  
  // Update URL when date or metric changes
  useEffect(() => {
    if (selectedDate) {
      setSearchParams(prev => {
        const newParams = new URLSearchParams(prev);
        newParams.set('date', selectedDate);
        newParams.set('metric', selectedMetric);
        return newParams;
      }, { replace: true });
    }
  }, [selectedDate, selectedMetric, setSearchParams]);
  
  // Handle date selection
  const handleDateChange = (date) => {
    setSelectedDate(date);
  };
  
  // Replace the static mapState with one derived from the siteData
  // This needs to be a useMemo to update when siteData changes

  const mapState = useMemo(() => {
    // Default values if site data isn't loaded yet
    const defaultState = {
      center: [48.5, -100],
      zoom: 8, // Increased zoom level for better site visibility
      bounds: null
    };
    
    // If we have site data, use the site's coordinates as center
    if (siteData && siteData.length > 0) {
      const site = siteData[0];
      return {
        center: [site.latitude, site.longitude],
        zoom: 10, // Higher zoom for site detail view
        bounds: null
      };
    }
    
    return defaultState;
  }, [siteData]);
  
  // Available metrics (same as in Home)
  const metrics = ['XC0', 'XC10', 'XC20', 'XC30', 'XC40', 'XC50', 'XC60', 'XC70', 'XC80', 'XC90', 'XC100'];
  
  const [forecast, setForecast] = useState(null);
  const [selectedHour, setSelectedHour] = useState(9);

  useEffect(() => {
    const loadForecast = async () => {
      try {
        setLoading(true);
        const data = await fetchSiteForecast(siteId, selectedDate);
        setForecast(data);
      } catch (err) {
        console.error('Error fetching forecast:', err);
      } finally {
        setLoading(false);
      }
    };

    if (selectedDate) {
      loadForecast();
    }
  }, [siteId, selectedDate]);

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
            mb: 1  // 8px fixed margin below buttons
          }}
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
          width: '100%',
          aspectRatio: '1/1',  // Makes it square
          maxHeight: 'calc(100vh - 300px)',  // Limits maximum height
          maxWidth: '1000px',  // Limits maximum width
          position: 'relative'
        }}>
          <D3Forecast 
            forecast={currentForecast} 
            selectedHour={selectedHour}
          />
        </Box>
      </Box>
    );
  };

  // First, let's add a useEffect to log the site data structure
  useEffect(() => {
    if (siteData && siteData.length > 0) {
      console.log('Site data structure:', siteData[0]);
      console.log('Predictions available:', siteData[0].predictions);
    }
  }, [siteData]);

  return (
    <Box sx={{ 
      maxWidth: '1200px',
      margin: '0 auto',
      p: 2,
      minHeight: '100%',  // Ensure it takes full height if content is short
    }}>
      {error ? (
        <Typography color="error" variant="h6" align="center" my={4}>
          {error}
        </Typography>
      ) : !siteData || !siteData.length ? (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
          <CircularProgress />
        </Box>
      ) : (
        <>
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

          {/* Add DateBoxes at bottom, just like on Home page */}
          {allDates.length > 0 && siteData && (
            <DateBoxes
              key={`datebox-${siteData[0]?.site_id}`}
              dates={allDates}
              selectedDate={selectedDate}
              setSelectedDate={handleDateChange}
              center={mapState.center}
              zoom={mapState.zoom}
              bounds={mapState.bounds}
              allSites={siteData}
              selectedMetric={selectedMetric}
              metrics={metrics}
            />
          )}
        </>
      )}
    </Box>
  );
};

export default Details;
