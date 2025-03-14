import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import D3Forecast from '../components/D3Forecast';
import { fetchSiteForecast, fetchSites, fetchFlightStats } from '../api';
import { 
  Box, 
  Button, 
  ButtonGroup,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  CircularProgress,
  Collapse
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import GlideatorForecast from '../components/GlideatorForecast';
import FlightStatsChart from '../components/FlightStatsChart';
import StandaloneMetricControl from '../components/StandaloneMetricControl';
import SiteMap from '../components/SiteMap';

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
  const [selectedMetric, setSelectedMetric] = useState(initialMetric);
  
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
  const [selectedHour, setSelectedHour] = useState(12);
  const [showWeatherDetails, setShowWeatherDetails] = useState(false);
  const [flightStats, setFlightStats] = useState(null);
  const [flightStatsLoading, setFlightStatsLoading] = useState(false);

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

  // Add a new useEffect for loading flight statistics
  useEffect(() => {
    const loadFlightStats = async () => {
      try {
        setFlightStatsLoading(true);
        const data = await fetchFlightStats(siteId);
        setFlightStats(data);
      } catch (err) {
        console.error('Error loading flight statistics:', err);
      } finally {
        setFlightStatsLoading(false);
      }
    };
    
    loadFlightStats();
  }, [siteId]);

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
            date={forecast.date}
            gfs_forecast_at={forecast.gfs_forecast_at}
            computed_at={forecast.computed_at}
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

  // Handle metric change
  const handleMetricChange = (newMetric) => {
    setSelectedMetric(newMetric);
    // Update URL
    setSearchParams(prev => {
      const newParams = new URLSearchParams(prev);
      newParams.set('metric', newMetric);
      return newParams;
    }, { replace: true });
  };

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
              <Typography variant="body1" gutterBottom>
                <strong>Name:</strong> {siteData[0]?.name}
              </Typography>
              <Typography>
                Site details coming soon...
              </Typography>
            </AccordionDetails>
          </Accordion>

          {/* Glideator Forecast Section */}
          <Accordion defaultExpanded>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="h6">Site Activity Forecast</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Box sx={{ display: 'flex', flexDirection: 'column', width: '100%', gap: 2 }}>
                <GlideatorForecast 
                  siteData={siteData[0]}
                  selectedDate={selectedDate}
                  selectedMetric={selectedMetric}
                  metrics={metrics}
                  onMetricChange={handleMetricChange}
                  onDateChange={handleDateChange}
                  allDates={allDates}
                  mapState={mapState}
                  allSites={siteData}
                />
                
                {/* Button to show weather details */}
                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
                  <Button 
                    variant="outlined" 
                    onClick={() => setShowWeatherDetails(!showWeatherDetails)}
                    endIcon={showWeatherDetails ? 
                      <ExpandMoreIcon style={{ transform: 'rotate(180deg)' }} /> : 
                      <ExpandMoreIcon />
                    }
                  >
                    {showWeatherDetails ? 'Hide' : "See What's Driving This"}
                  </Button>
                </Box>
                
                {/* Conditionally render the weather forecast content with smooth animation */}
                <Collapse in={showWeatherDetails} timeout="auto">
                  <Box 
                    sx={{ 
                      mt: 2,
                      pt: 1  // Just a little padding at the top
                    }}
                  >
                    {renderForecastContent()}
                  </Box>
                </Collapse>
              </Box>
            </AccordionDetails>
          </Accordion>
          {/* Flight Statistics Section */}
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="h6">Flight Statistics</Typography>
            </AccordionSummary>
            <AccordionDetails>
              {flightStatsLoading ? (
                <Box display="flex" justifyContent="center" p={3}>
                  <CircularProgress />
                </Box>
              ) : flightStats ? (
                <FlightStatsChart 
                  data={flightStats} 
                  metrics={metrics}
                  selectedMetric={selectedMetric}
                  onMetricChange={handleMetricChange}
                />
              ) : (
                <Typography>
                  Flight statistics not available for this site.
                </Typography>
              )}
            </AccordionDetails>
          </Accordion>
          {/* Site Map Section - Now as an Accordion */}
          <Accordion defaultExpanded>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="h6">Site Map</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <SiteMap siteId={siteId} siteName={siteData?.name} />
            </AccordionDetails>
          </Accordion>
        </>
      )}
    </Box>
  );
};

export default Details;
