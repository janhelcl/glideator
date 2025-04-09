import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import D3Forecast from '../components/D3Forecast';
import { fetchSiteForecast, fetchSites, fetchFlightStats, fetchSiteInfo } from '../api';
import { 
  Box, 
  Button, 
  ButtonGroup,
  Typography,
  CircularProgress,
  Collapse,
  Tabs,
  Tab,
  Paper,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import InfoIcon from '@mui/icons-material/Info';
import TimelineIcon from '@mui/icons-material/Timeline';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import MapIcon from '@mui/icons-material/Map';
import GlideatorForecast from '../components/GlideatorForecast';
import FlightStatsChart from '../components/FlightStatsChart';
import SiteMap from '../components/SiteMap';
import SearchRecs from '../components/SearchRecs';
import LoadingSpinner from '../components/LoadingSpinner';

// Define tab names for URL mapping
const tabNames = ['details', 'forecast', 'season', 'map'];

// TabPanel component to display tab content
function TabPanel(props) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`site-tabpanel-${index}`}
      aria-labelledby={`site-tab-${index}`}
      {...other}
    >
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

const Details = () => {
  const { siteId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Get date and metric from URL or use defaults
  const initialDate = searchParams.get('date') || '';
  const initialMetric = searchParams.get('metric') || 'XC50';
  const initialTabName = searchParams.get('tab') || tabNames[1]; // Default to 'forecast'

  // Find the index corresponding to the initial tab name
  const initialTabIndex = tabNames.indexOf(initialTabName) !== -1 ? tabNames.indexOf(initialTabName) : 1;
  
  // State for site data and dates
  const [siteData, setSiteData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedDate, setSelectedDate] = useState(initialDate);
  const [selectedMetric, setSelectedMetric] = useState(initialMetric);
  
  // New state for site info
  const [siteInfo, setSiteInfo] = useState(null);
  const [siteInfoLoading, setSiteInfoLoading] = useState(false);
  
  // State for active tab, initialized from URL or default
  const [activeTab, setActiveTab] = useState(initialTabIndex);
  
  // Add theme and media query logic
  const theme = useTheme();
  const isSmallScreen = useMediaQuery(theme.breakpoints.down('sm'));
  
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
  
  // New effect to load site info
  useEffect(() => {
    const loadSiteInfo = async () => {
      try {
        setSiteInfoLoading(true);
        const info = await fetchSiteInfo(siteId);
        setSiteInfo(info);
      } catch (err) {
        console.error('Error loading site info:', err);
      } finally {
        setSiteInfoLoading(false);
      }
    };
    
    loadSiteInfo();
  }, [siteId]);
  
  // Set default date if none selected and data is loaded
  useEffect(() => {
    if (allDates.length) {
      if (!selectedDate) {
        // No date selected, use the first available date
        setSelectedDate(allDates[0]);
      } else {
        // Check if the selected date is valid (exists in available dates)
        const dateExists = allDates.includes(selectedDate);
        
        if (!dateExists) {
          // If date doesn't exist (likely because it's in the past), use today's date or earliest available
          const today = new Date().toISOString().split('T')[0];
          // Find today's date in available dates or get the earliest available
          const todayIndex = allDates.indexOf(today);
          const newDate = todayIndex >= 0 ? today : allDates[0];
          
          // Update selected date
          setSelectedDate(newDate);
        }
      }
    }
  }, [allDates, selectedDate]);
  
  // Update URL when date, metric, or tab changes
  useEffect(() => {
    if (selectedDate) {
      setSearchParams(prev => {
        const newParams = new URLSearchParams(prev);
        newParams.set('date', selectedDate);
        newParams.set('metric', selectedMetric);
        // Map the activeTab index back to its name for the URL
        newParams.set('tab', tabNames[activeTab]); 
        return newParams;
      }, { replace: true });
    }
  }, [selectedDate, selectedMetric, activeTab, setSearchParams]);
  
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
          <LoadingSpinner />
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

  // Handle tab change
  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  // Render site info content
  const renderSiteInfoContent = () => {
    if (siteInfoLoading) {
      return (
        <Box display="flex" justifyContent="center" p={3}>
          <LoadingSpinner />
        </Box>
      );
    }
    
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <Typography variant="h5" gutterBottom>
          {siteInfo?.site_name || siteData[0]?.name}
          {siteInfo?.country && ` (${siteInfo.country})`}
        </Typography>
        
        {siteInfo?.html ? (
          <Box 
            sx={{ 
              '& h2': {
                mt: 3,
                mb: 2,
                color: 'black',
                fontWeight: 'bold'
              },
              '& p': {
                mb: 2
              },
              '& ul': {
                pl: 2,
                mb: 2
              },
              '& li': {
                mb: 1
              },
              '& a': {
                color: 'primary.main',
                textDecoration: 'none',
                '&:hover': {
                  textDecoration: 'underline'
                }
              },
              '& strong': {
                color: 'text.primary',
                fontWeight: 'bold'
              }
            }}
            dangerouslySetInnerHTML={{ __html: siteInfo.html }}
          />
        ) : (
          <Typography>
            Detailed information not available for this site yet.
          </Typography>
        )}

        {/* Conditionally render the SearchRecs component */}
        {siteInfo && siteInfo.site_name && (
          <SearchRecs 
            siteName={siteInfo.site_name} 
            country={siteInfo.country} 
          />
        )}
      </Box>
    );
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
          <LoadingSpinner />
        </Box>
      ) : (
        <Paper elevation={2}>
          {/* Site title displayed above tabs */}
          <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
            <Typography variant="h5">
              {siteInfo?.site_name || siteData[0]?.name}
            </Typography>
          </Box>
          
          {/* Tabs navigation */}
          <Tabs 
            value={activeTab} 
            onChange={handleTabChange} 
            variant={isSmallScreen ? "scrollable" : "fullWidth"}
            allowScrollButtonsMobile
            sx={{ 
              borderBottom: 1, 
              borderColor: 'divider',
              '& .MuiTab-root': {
                minHeight: 'auto',
                padding: '8px 0',
                gap: '4px',
                flexDirection: 'column',
                alignItems: 'center',
                textTransform: 'none',
                fontSize: '0.75rem',
                '& .MuiSvgIcon-root': {
                  fontSize: '1.5rem',
                  marginBottom: '4px'
                }
              }
            }}
          >
            <Tab 
              label="Details" 
              icon={<InfoIcon />} 
              iconPosition="top"
              id="site-tab-0" 
              aria-controls="site-tabpanel-0" 
            />
            <Tab 
              label="Activity Forecast" 
              icon={<TimelineIcon />} 
              iconPosition="top"
              id="site-tab-1" 
              aria-controls="site-tabpanel-1" 
            />
            <Tab 
              label="Season" 
              icon={<CalendarMonthIcon />} 
              iconPosition="top"
              id="site-tab-2" 
              aria-controls="site-tabpanel-2" 
            />
            <Tab 
              label="Site Map" 
              icon={<MapIcon />} 
              iconPosition="top"
              id="site-tab-3" 
              aria-controls="site-tabpanel-3" 
            />
          </Tabs>
          
          {/* Tab panels */}
          <TabPanel value={activeTab} index={0}>
            {renderSiteInfoContent()}
          </TabPanel>
          
          <TabPanel value={activeTab} index={1}>
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
          </TabPanel>
          
          <TabPanel value={activeTab} index={2}>
            {flightStatsLoading ? (
              <Box display="flex" justifyContent="center" p={3}>
                <LoadingSpinner />
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
          </TabPanel>
          
          <TabPanel value={activeTab} index={3}>
            <SiteMap siteId={siteId} siteName={siteData[0]?.name} />
          </TabPanel>
        </Paper>
      )}
    </Box>
  );
};

export default Details;
