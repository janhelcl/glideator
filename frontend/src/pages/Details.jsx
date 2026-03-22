import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import D3Forecast from '../components/D3Forecast';
import {
  fetchSiteForecast,
  fetchFlightStats,
  fetchSiteInfo,
  fetchSitePredictions,
  fetchSiteResources,
} from '../api';
import { 
  Box, 
  Button, 
  ButtonGroup,
  Typography,
  Collapse,
  Tabs,
  Tab,
  Paper,
  useTheme,
  useMediaQuery,
  Link,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import TimelineIcon from '@mui/icons-material/Timeline';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import MapIcon from '@mui/icons-material/Map';
import LinkIcon from '@mui/icons-material/Link';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import VideocamIcon from '@mui/icons-material/Videocam';
import DeviceThermostatIcon from '@mui/icons-material/DeviceThermostat';
import CloudIcon from '@mui/icons-material/Cloud';
import ParaglidingIcon from '@mui/icons-material/Paragliding';
import SearchIcon from '@mui/icons-material/Search';
import LanguageIcon from '@mui/icons-material/Language';
import GlideatorForecast from '../components/GlideatorForecast';
import FlightStatsChart from '../components/FlightStatsChart';
import SiteMap from '../components/SiteMap';
import SearchRecs from '../components/SearchRecs';
import LoadingSpinner from '../components/LoadingSpinner';
import { Helmet } from 'react-helmet-async';
import FavoriteIcon from '@mui/icons-material/Favorite';
import FavoriteBorderIcon from '@mui/icons-material/FavoriteBorder';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import { useAuth } from '../context/AuthContext';
import Tooltip from '@mui/material/Tooltip';
import IconButton from '@mui/material/IconButton';
import SimilarDaysPanel from '../components/SimilarDaysPanel';
import { useDefaultMetric } from '../hooks/useDefaultMetric';

// Define tab names for URL mapping (default tab = forecast at index 2)
const tabNames = ['forecast', 'season', 'map', 'resources'];

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
const navigate = useNavigate();
const numericSiteId = Number(siteId);
const { preferredMetric } = useDefaultMetric();
  const { isAuthenticated, toggleFavoriteSite, isFavorite } = useAuth();

  // Get date and metric from URL or use defaults
  const initialDate = searchParams.get('date') || '';
  const initialMetric = searchParams.get('metric') || preferredMetric;
  const initialTabName = searchParams.get('tab') || 'forecast';

  // Find the index corresponding to the initial tab name
  const initialTabIndex = tabNames.indexOf(initialTabName) !== -1 ? tabNames.indexOf(initialTabName) : 0;
  
  // State for site data and dates
  const [siteData, setSiteData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedDate, setSelectedDate] = useState(initialDate);
  const [selectedMetric, setSelectedMetric] = useState(initialMetric);
  
  // New state for site info
  const [siteInfo, setSiteInfo] = useState(null);
  const [siteInfoLoading, setSiteInfoLoading] = useState(false);

  const [siteResources, setSiteResources] = useState(null);
  const [siteResourcesLoading, setSiteResourcesLoading] = useState(false);
  const [siteResourcesError, setSiteResourcesError] = useState(null);
  
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
  
  // Effect to load site data (now specifically predictions)
  useEffect(() => {
    const loadSiteData = async () => {
      try {
        setLoading(true);
        // Fetch predictions specifically for this siteId
        const data = await fetchSitePredictions(siteId);
        
        // Check if data is valid (should be an array with one item)
        if (!data || data.length === 0) {
          // Site not found, redirect to 404
          navigate('/404');
          return;
        }
        
        // Set the site data directly from the response
        setSiteData(data);
      } catch (err) {
        console.error('Error loading site data:', err);
        if (err.response?.data?.detail === "Site not found") {
          navigate('/404');
          return;
        }
        setError('Failed to load site data');
      } finally {
        setLoading(false);
      }
    };
    
    loadSiteData();
  }, [siteId, navigate]);
  
  // New effect to load site info
  useEffect(() => {
    const loadSiteInfo = async () => {
      try {
        setSiteInfoLoading(true);
        const info = await fetchSiteInfo(siteId);
        if (!info) {
          navigate('/404');
          return;
        }
        setSiteInfo(info);
      } catch (err) {
        console.error('Error loading site info:', err);
        if (err.response?.data?.detail === "Site not found") {
          navigate('/404');
          return;
        }
      } finally {
        setSiteInfoLoading(false);
      }
    };
    
    loadSiteInfo();
  }, [siteId, navigate]);

  useEffect(() => {
    const loadResources = async () => {
      try {
        setSiteResourcesLoading(true);
        setSiteResourcesError(null);
        const data = await fetchSiteResources(siteId);
        setSiteResources(data);
      } catch (err) {
        console.error('Error loading site resources:', err);
        setSiteResourcesError('Could not load resources. Try again later.');
        setSiteResources(null);
      } finally {
        setSiteResourcesLoading(false);
      }
    };

    loadResources();
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

        {/* Surface metadata */}
        <Box sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr 1fr', sm: 'repeat(4, auto)' },
          gap: { xs: 0.5, sm: 2 },
          justifyContent: 'center',
          justifyItems: { xs: 'center', sm: 'start' },
          mt: 1,
          px: 1,
        }}>
          {currentForecast.wind_gust_sfc_ms != null && (
            <Typography variant="body2" color="text.secondary">
              Gust: <strong>{currentForecast.wind_gust_sfc_ms.toFixed(1)} m/s</strong>
            </Typography>
          )}
          {currentForecast.pressure_sfc_pa != null && (
            <Typography variant="body2" color="text.secondary">
              Pressure: <strong>{(currentForecast.pressure_sfc_pa / 100).toFixed(0)} hPa</strong>
            </Typography>
          )}
          {currentForecast.geopotential_height_sfc_m != null && (
            <Typography variant="body2" color="text.secondary">
              Model alt.: <strong>{Math.round(currentForecast.geopotential_height_sfc_m)} m</strong>
            </Typography>
          )}
          {siteData && siteData[0]?.altitude != null && (
            <Typography variant="body2" color="text.secondary">
              Actual alt.: <strong>{siteData[0].altitude} m</strong>
            </Typography>
          )}
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
  const renderResourcesContent = () => {
    const { local_resources: localResources = [], webcam_urls: webcamUrls = [], meteostation_urls: meteoUrls = [] } = siteResources || {};

    const sectionBoxSx = {
      bgcolor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.015)',
      border: '1px solid',
      borderColor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)',
      borderRadius: 2,
      p: { xs: 2, sm: 2.5 },
    };

    const sectionHeaderSx = {
      display: 'flex',
      alignItems: 'center',
      gap: 1,
      mb: 1.5,
    };

    const resourceLink = (href, label, icon) => (
      <Link
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        underline="hover"
        sx={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 0.75,
          py: 0.5,
          wordBreak: 'break-all',
          fontSize: '0.9rem',
        }}
      >
        {icon || <OpenInNewIcon sx={{ fontSize: '1rem', opacity: 0.6, flexShrink: 0 }} />}
        {label || href}
      </Link>
    );

    const linkCard = ({ href, label, desc }) => (
      <Link
        key={href}
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        underline="none"
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
          p: 1.5,
          borderRadius: 1.5,
          border: '1px solid',
          borderColor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
          bgcolor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.02)' : '#fff',
          transition: 'all 0.15s ease',
          '&:hover': {
            borderColor: 'primary.main',
            bgcolor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.04)' : 'rgba(41,182,246,0.04)',
          },
        }}
      >
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="body2" sx={{ fontWeight: 600, color: 'primary.main', lineHeight: 1.3 }}>
            {label}
          </Typography>
          {desc && (
            <Typography variant="caption" color="text.secondary" sx={{ lineHeight: 1.3 }}>
              {desc}
            </Typography>
          )}
        </Box>
        <OpenInNewIcon sx={{ fontSize: '0.9rem', opacity: 0.4, flexShrink: 0, color: 'text.secondary' }} />
      </Link>
    );

    const weatherLinks = siteData && siteData[0] ? [
      {
        href: `https://windy.com/${siteData[0].latitude}/${siteData[0].longitude}?${siteData[0].latitude},${siteData[0].longitude},11`,
        label: 'Windy.com',
        desc: 'General weather forecast',
      },
      {
        href: `https://meteo-parapente.com/#/${siteData[0].latitude},${siteData[0].longitude},7`,
        label: 'Meteo-Parapente',
        desc: 'PG-focused forecast',
      },
      {
        href: `http://www.xcmeteo.net/cs?p=${siteData[0].longitude}x${siteData[0].latitude}`,
        label: 'xcmeteo.net',
        desc: 'Atmospheric profile from the GFS model',
      },
      {
        href: `https://www.windguru.cz/map/?lat=${siteData[0].latitude}&lon=${siteData[0].longitude}&zoom=11`,
        label: 'Windguru – forecast',
        desc: 'Detailed wind models',
      },
      {
        href: `https://www.windguru.cz/map/station?lat=${siteData[0].latitude}&lon=${siteData[0].longitude}&zoom=11`,
        label: 'Windguru – stations',
        desc: 'Nearby live meteostations',
      },
      {
        href: `https://thermal.kk7.ch/#${siteData[0].latitude},${siteData[0].longitude},11`,
        label: 'Thermal map',
        desc: 'Thermal hotspots (kk7.ch)',
      },
    ] : [];

    const flightLinks = siteData && siteData[0] ? [
      {
        href: `https://www.xcontest.org/world/cs/vyhledavani-preletu/?list[sort]=time_start&filter[point]=${siteData[0].longitude}+${siteData[0].latitude}&filter[radius]=5000`,
        label: 'Recent flights',
        desc: 'Latest tracks from this area',
      },
      {
        href: `https://www.xcontest.org/world/cs/vyhledavani-preletu/?list[sort]=pts&filter[point]=${siteData[0].longitude}+${siteData[0].latitude}&filter[radius]=5000`,
        label: 'Best flights',
        desc: 'Top-scoring XC flights nearby',
      },
    ] : [];

    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
        {/* Local Resources */}
        <Box sx={sectionBoxSx}>
          <Box sx={sectionHeaderSx}>
            <LanguageIcon color="primary" sx={{ fontSize: '1.3rem' }} />
            <Typography variant="h6" sx={{ fontSize: '1.05rem', fontWeight: 600 }}>
              Local Resources
            </Typography>
          </Box>
          {siteResourcesLoading ? (
            <Box display="flex" justifyContent="center" p={2}><LoadingSpinner /></Box>
          ) : siteResourcesError ? (
            <Typography variant="body2" color="text.secondary">{siteResourcesError}</Typography>
          ) : localResources.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No local club or site pages on file yet.
            </Typography>
          ) : (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.25 }}>
              {localResources.map((r) => (
                <Box key={r.candidate_id} sx={{ display: 'flex', flexDirection: 'column' }}>
                  {resourceLink(r.url, r.name || r.host || 'Resource')}
                  <Typography variant="caption" color="text.secondary" sx={{ pl: 2.75 }}>
                    {new URL(r.url).hostname}
                  </Typography>
                </Box>
              ))}
            </Box>
          )}
        </Box>

        {/* Webcams & Meteostations side by side on larger screens */}
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2.5 }}>
          {/* Webcams */}
          <Box sx={sectionBoxSx}>
            <Box sx={sectionHeaderSx}>
              <VideocamIcon color="primary" sx={{ fontSize: '1.3rem' }} />
              <Typography variant="h6" sx={{ fontSize: '1.05rem', fontWeight: 600 }}>
                Webcams
              </Typography>
            </Box>
            {siteResourcesLoading ? (
              <Box display="flex" justifyContent="center" p={2}><LoadingSpinner /></Box>
            ) : webcamUrls.length === 0 ? (
              <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                None found yet
              </Typography>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {webcamUrls.map((u) => (
                  <Box key={u}>
                    {resourceLink(u, new URL(u).hostname.replace(/^www\./, ''))}
                  </Box>
                ))}
              </Box>
            )}
          </Box>

          {/* Meteostations */}
          <Box sx={sectionBoxSx}>
            <Box sx={sectionHeaderSx}>
              <DeviceThermostatIcon color="primary" sx={{ fontSize: '1.3rem' }} />
              <Typography variant="h6" sx={{ fontSize: '1.05rem', fontWeight: 600 }}>
                Meteostations
              </Typography>
            </Box>
            {siteResourcesLoading ? (
              <Box display="flex" justifyContent="center" p={2}><LoadingSpinner /></Box>
            ) : meteoUrls.length === 0 ? (
              <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                None found yet
              </Typography>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {meteoUrls.map((u) => (
                  <Box key={u}>
                    {resourceLink(u, new URL(u).hostname.replace(/^www\./, ''))}
                  </Box>
                ))}
              </Box>
            )}
          </Box>
        </Box>

        {/* Weather & Forecast Links */}
        {weatherLinks.length > 0 && (
          <Box sx={sectionBoxSx}>
            <Box sx={sectionHeaderSx}>
              <CloudIcon color="primary" sx={{ fontSize: '1.3rem' }} />
              <Typography variant="h6" sx={{ fontSize: '1.05rem', fontWeight: 600 }}>
                Weather & Forecasts
              </Typography>
            </Box>
            <Box sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' },
              gap: 1.25,
            }}>
              {weatherLinks.map(linkCard)}
            </Box>

          </Box>
        )}

        {/* Flight Records */}
        {flightLinks.length > 0 && (
          <Box sx={sectionBoxSx}>
            <Box sx={sectionHeaderSx}>
              <ParaglidingIcon color="primary" sx={{ fontSize: '1.3rem' }} />
              <Typography variant="h6" sx={{ fontSize: '1.05rem', fontWeight: 600 }}>
                Flight Records
              </Typography>
            </Box>
            <Box sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' },
              gap: 1.25,
            }}>
              {flightLinks.map(linkCard)}
            </Box>
          </Box>
        )}

        {/* Do your own research */}
        {siteInfo && siteInfo.site_name && (
          <Box sx={sectionBoxSx}>
            <Box sx={sectionHeaderSx}>
              <SearchIcon color="primary" sx={{ fontSize: '1.3rem' }} />
              <Typography variant="h6" sx={{ fontSize: '1.05rem', fontWeight: 600 }}>
                Do Your Own Research
              </Typography>
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Quick Google searches to find more about this site.
            </Typography>
            <SearchRecs siteName={siteInfo.site_name} country={siteInfo.country} />
          </Box>
        )}
      </Box>
    );
  };

  const favoriteActive = isAuthenticated && isFavorite(numericSiteId);

  return (
    <Box sx={{ 
      maxWidth: '1200px',
      margin: '0 auto',
      p: 2,
      minHeight: '100%',  // Ensure it takes full height if content is short
    }}>
      {siteData && siteData.length > 0 && (
        <Helmet>
          <title>{`${siteInfo?.site_name || siteData[0]?.name} – Parra-Glideator`}</title>
          <meta name="description" content={`Forecasts, seasonality and map for ${siteInfo?.site_name || siteData[0]?.name}. Plan flights with Glideator metrics.`} />
          <link rel="canonical" href={window.location.origin + `/details/${siteId}`} />
          <meta property="og:title" content={`${siteInfo?.site_name || siteData[0]?.name} – Parra-Glideator`} />
          <meta property="og:description" content={`Paragliding forecasts and info for ${siteInfo?.site_name || siteData[0]?.name}.`} />
          <meta property="og:type" content="article" />
          <meta name="twitter:card" content="summary_large_image" />
          <script type="application/ld+json">{JSON.stringify({
            "@context": "https://schema.org",
            "@type": "SportsActivityLocation",
            "name": siteInfo?.site_name || siteData[0]?.name,
            "description": "Paragliding site with forecasts, seasonality, and site map.",
            "geo": {
              "@type": "GeoCoordinates",
              "latitude": siteData[0]?.latitude,
              "longitude": siteData[0]?.longitude
            },
            "hasMap": `https://maps.google.com/?q=${siteData[0]?.latitude},${siteData[0]?.longitude}`,
            "sameAs": [
              `https://windy.com/${siteData[0]?.latitude}/${siteData[0]?.longitude}?${siteData[0]?.latitude},${siteData[0]?.longitude},11`,
              `http://www.xcmeteo.net/cs?p=${siteData[0]?.longitude}x${siteData[0]?.latitude}`,
              `https://www.windguru.cz/map/?lat=${siteData[0]?.latitude}&lon=${siteData[0]?.longitude}&zoom=11`,
              `https://www.windguru.cz/map/station?lat=${siteData[0]?.latitude}&lon=${siteData[0]?.longitude}&zoom=11`,
              `https://thermal.kk7.ch/#${siteData[0]?.latitude},${siteData[0]?.longitude},11`,
              `https://www.xcontest.org/world/cs/vyhledavani-preletu/?list[sort]=pts&filter[point]=${siteData[0]?.longitude}+${siteData[0]?.latitude}&filter[radius]=5000`
            ]
          })}</script>
          <script type="application/ld+json">{JSON.stringify({
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [
              {
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": "https://parra-glideator.com/"
              },
              ...(siteInfo?.country ? [{
                "@type": "ListItem",
                "position": 2,
                "name": siteInfo.country,
                "item": `https://parra-glideator.com/country/${siteInfo.country.toLowerCase().replace(/\s+/g, '-')}`
              }] : []),
              {
                "@type": "ListItem",
                "position": siteInfo?.country ? 3 : 2,
                "name": siteInfo?.site_name || siteData[0]?.name
              }
            ]
          })}</script>
        </Helmet>
      )}
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
          <Box sx={{ p: isSmallScreen ? 1 : 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              {/* Title with favorite */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Tooltip
                  title={isAuthenticated ? (favoriteActive ? 'Remove from favorites' : 'Add to favorites') : 'Log in to manage favorites'}
                >
                  <span>
                    <IconButton
                      color={favoriteActive ? 'error' : 'default'}
                      onClick={() => toggleFavoriteSite(numericSiteId)}
                      size="large"
                      disabled={!isAuthenticated}
                    >
                      {favoriteActive ? <FavoriteIcon /> : <FavoriteBorderIcon />}
                    </IconButton>
                  </span>
                </Tooltip>
                <Tooltip
                  title={isAuthenticated ? 'Create notification' : 'Log in to create notifications'}
                >
                  <span>
                    <IconButton
                      color="primary"
                      size="large"
                      disabled={!isAuthenticated}
                      onClick={() =>
                        navigate('/notifications', {
                          state: {
                            notificationSetup: {
                              siteId: numericSiteId,
                              metric: selectedMetric,
                            },
                          },
                        })
                      }
                    >
                      <NotificationsActiveIcon />
                    </IconButton>
                  </span>
                </Tooltip>
                <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 0 }}>
                  {siteData[0]?.name || 'Site Details'}
                </Typography>
              </Box>
              <img src={`${process.env.PUBLIC_URL}/logo192.png`} alt="Glideator" style={{ height: 48 }} />
            </Box>
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
              label="Activity Forecast" 
              icon={<TimelineIcon />} 
              iconPosition="top"
              id="site-tab-0" 
              aria-controls="site-tabpanel-0" 
            />
            <Tab 
              label="Season" 
              icon={<CalendarMonthIcon />} 
              iconPosition="top"
              id="site-tab-1" 
              aria-controls="site-tabpanel-1" 
            />
            <Tab 
              label="Site Map" 
              icon={<MapIcon />} 
              iconPosition="top"
              id="site-tab-2" 
              aria-controls="site-tabpanel-2" 
            />
            <Tab 
              label="Resources" 
              icon={<LinkIcon />} 
              iconPosition="top"
              id="site-tab-3" 
              aria-controls="site-tabpanel-3" 
            />
          </Tabs>
          
          {/* Tab panels */}
          <TabPanel value={activeTab} index={0}>
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
              
              {/* Similar Days Panel */}
              {selectedDate && siteData && siteData[0] && (
                <SimilarDaysPanel
                  siteId={siteId}
                  selectedDate={selectedDate}
                  latitude={siteData[0].latitude}
                  longitude={siteData[0].longitude}
                  siteAltitude={siteData[0].altitude}
                />
              )}
            </Box>
          </TabPanel>
          
          <TabPanel value={activeTab} index={1}>
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
          
          <TabPanel value={activeTab} index={2}>
            <SiteMap siteId={siteId} siteName={siteData[0]?.name} />
          </TabPanel>
          
          <TabPanel value={activeTab} index={3}>
            {renderResourcesContent()}
          </TabPanel>
        </Paper>
      )}
    </Box>
  );
};

export default Details;
