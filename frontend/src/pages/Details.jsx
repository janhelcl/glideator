import React, { Suspense, useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link as RouterLink, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import {
  Box,
  Button,
  ButtonGroup,
  Fade,
  IconButton,
  Link,
  Paper,
  Tab,
  Tabs,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
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
import FavoriteIcon from '@mui/icons-material/Favorite';
import FavoriteBorderIcon from '@mui/icons-material/FavoriteBorder';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import { Helmet } from 'react-helmet-async';
import {
  fetchFlightStats,
  fetchSiteForecast,
  fetchSiteInfo,
  fetchSitePredictions,
  fetchSiteResources,
} from '../api';
import GlideatorForecast from '../components/GlideatorForecast';
import LoadingSpinner from '../components/LoadingSpinner';
import ShareForecastButton from '../components/ShareForecastButton';
import { useAuth } from '../context/AuthContext';
import { useDefaultMetric } from '../hooks/useDefaultMetric';

const D3Forecast = React.lazy(() => import('../components/D3Forecast'));
const FlightStatsChart = React.lazy(() => import('../components/FlightStatsChart'));
const SearchRecs = React.lazy(() => import('../components/SearchRecs'));
const SimilarDaysPanel = React.lazy(() => import('../components/SimilarDaysPanel'));
const SiteMap = React.lazy(() => import('../components/SiteMap'));

const TAB_NAMES = ['forecast', 'season', 'map', 'resources'];
const METRICS = ['XC0', 'XC10', 'XC20', 'XC30', 'XC40', 'XC50', 'XC60', 'XC70', 'XC80', 'XC90', 'XC100'];

const PanelLoading = () => (
  <Box display="flex" justifyContent="center" p={3}>
    <LoadingSpinner />
  </Box>
);

const TabPanel = ({ children, value, index }) => (
  <div
    role="tabpanel"
    hidden={value !== index}
    id={`site-tabpanel-${index}`}
    aria-labelledby={`site-tab-${index}`}
  >
    {value === index && (
      <Box sx={{ p: 3 }}>
        <Suspense fallback={<PanelLoading />}>{children}</Suspense>
      </Box>
    )}
  </div>
);

const isNotFound = (error) => (
  error?.response?.status === 404 || error?.response?.data?.detail === 'Site not found'
);

const safeHostname = (url) => {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
};

const Details = () => {
  const { siteId } = useParams();
  const numericSiteId = Number(siteId);
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const theme = useTheme();
  const isSmallScreen = useMediaQuery(theme.breakpoints.down('sm'));
  const { preferredMetric } = useDefaultMetric();
  const { isAuthenticated, toggleFavoriteSite, isFavorite } = useAuth();

  const initialTabName = searchParams.get('tab') || 'forecast';
  const initialTabIndex = Math.max(0, TAB_NAMES.indexOf(initialTabName));
  const [activeTab, setActiveTab] = useState(initialTabIndex);
  const [selectedDate, setSelectedDate] = useState(searchParams.get('date') || '');
  const [selectedMetric, setSelectedMetric] = useState(searchParams.get('metric') || preferredMetric);
  const [selectedHour, setSelectedHour] = useState(12);
  const [showWeatherDetails, setShowWeatherDetails] = useState(false);

  const predictionsQuery = useQuery({
    queryKey: ['site', numericSiteId, 'predictions'],
    queryFn: ({ signal }) => fetchSitePredictions(siteId, { signal }),
    enabled: Number.isFinite(numericSiteId),
  });

  const siteInfoQuery = useQuery({
    queryKey: ['site', numericSiteId, 'info'],
    queryFn: ({ signal }) => fetchSiteInfo(siteId, { signal }),
    enabled: Number.isFinite(numericSiteId),
  });

  const siteData = predictionsQuery.data;
  const siteInfo = siteInfoQuery.data;
  const site = siteData?.[0];

  const allDates = useMemo(() => {
    const dates = site?.predictions?.map((prediction) => prediction.date) || [];
    return [...new Set(dates)].sort();
  }, [site]);

  useEffect(() => {
    if (!Number.isFinite(numericSiteId)) {
      navigate('/404', { replace: true });
      return;
    }

    const missingSite = predictionsQuery.isSuccess && (!siteData || siteData.length === 0);
    if (missingSite || isNotFound(predictionsQuery.error) || isNotFound(siteInfoQuery.error)) {
      navigate('/404', { replace: true });
    }
  }, [navigate, numericSiteId, predictionsQuery.error, predictionsQuery.isSuccess, siteData, siteInfoQuery.error]);

  useEffect(() => {
    if (!allDates.length) return;

    if (!selectedDate || !allDates.includes(selectedDate)) {
      const today = new Date().toISOString().split('T')[0];
      setSelectedDate(allDates.includes(today) ? today : allDates[0]);
    }
  }, [allDates, selectedDate]);

  useEffect(() => {
    setSearchParams((previous) => {
      const next = new URLSearchParams(previous);
      if (selectedDate) next.set('date', selectedDate);
      next.set('metric', selectedMetric);
      next.set('tab', TAB_NAMES[activeTab]);
      return next;
    }, { replace: true });
  }, [activeTab, selectedDate, selectedMetric, setSearchParams]);

  const forecastQuery = useQuery({
    queryKey: ['site', numericSiteId, 'forecast', selectedDate],
    queryFn: ({ signal }) => fetchSiteForecast(siteId, selectedDate, { signal }),
    enabled: activeTab === 0 && showWeatherDetails && Boolean(selectedDate),
  });

  const flightStatsQuery = useQuery({
    queryKey: ['site', numericSiteId, 'flight-stats'],
    queryFn: ({ signal }) => fetchFlightStats(siteId, { signal }),
    enabled: activeTab === 1,
  });

  const resourcesQuery = useQuery({
    queryKey: ['site', numericSiteId, 'resources'],
    queryFn: ({ signal }) => fetchSiteResources(siteId, { signal }),
    enabled: activeTab === 3,
  });

  const mapState = useMemo(() => ({
    center: site ? [site.latitude, site.longitude] : [48.5, -100],
    zoom: site ? 10 : 8,
    bounds: null,
  }), [site]);

  const handleMetricChange = (metric) => {
    setSelectedMetric(metric);
  };

  const renderForecastContent = () => {
    if (forecastQuery.isPending) return <PanelLoading />;

    if (forecastQuery.isError || !forecastQuery.data) {
      return (
        <Typography color="error" align="center">
          Failed to load forecast data.
        </Typography>
      );
    }

    const forecast = forecastQuery.data;
    const currentForecast = forecast[`forecast_${selectedHour}`];

    if (!currentForecast) {
      return (
        <Typography color="warning.main" align="center">
          No forecast data is available for {selectedHour}:00.
        </Typography>
      );
    }

    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%' }}>
        <ButtonGroup variant="contained" sx={{ minWidth: 'min-content', mb: 1 }}>
          {[9, 12, 15].map((hour) => (
            <Button
              key={hour}
              onClick={() => setSelectedHour(hour)}
              variant={selectedHour === hour ? 'contained' : 'outlined'}
            >
              {hour}:00
            </Button>
          ))}
        </ButtonGroup>

        <Box sx={{
          width: '100%',
          display: 'flex',
          justifyContent: 'center',
          position: 'relative',
        }}>
          <D3Forecast
            forecast={currentForecast}
            selectedHour={selectedHour}
            date={forecast.date}
            gfs_forecast_at={forecast.gfs_forecast_at}
            computed_at={forecast.computed_at}
          />
        </Box>

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
          {site?.altitude != null && (
            <Typography variant="body2" color="text.secondary">
              Actual alt.: <strong>{site.altitude} m</strong>
            </Typography>
          )}
        </Box>
      </Box>
    );
  };

  const renderResourcesContent = () => {
    if (resourcesQuery.isPending) return <PanelLoading />;

    if (resourcesQuery.isError) {
      return (
        <Typography color="error" align="center">
          Could not load resources. Try again later.
        </Typography>
      );
    }

    const {
      local_resources: localResources = [],
      webcam_urls: webcamUrls = [],
      meteostation_urls: meteoUrls = [],
    } = resourcesQuery.data || {};

    const sectionSx = {
      bgcolor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.015)',
      border: '1px solid',
      borderColor: theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)',
      borderRadius: 2,
      p: { xs: 2, sm: 2.5 },
    };

    const header = (icon, title) => (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
        {icon}
        <Typography variant="h6" sx={{ fontSize: '1.05rem', fontWeight: 600 }}>{title}</Typography>
      </Box>
    );

    const externalLink = (href, label, description = null) => (
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
          borderColor: 'divider',
          '&:hover': { borderColor: 'primary.main' },
        }}
      >
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="body2" sx={{ fontWeight: 600, color: 'primary.main' }}>{label}</Typography>
          {description && <Typography variant="caption" color="text.secondary">{description}</Typography>}
        </Box>
        <OpenInNewIcon sx={{ fontSize: '0.9rem', opacity: 0.5 }} />
      </Link>
    );

    const weatherLinks = site ? [
      [`https://windy.com/${site.latitude}/${site.longitude}?${site.latitude},${site.longitude},11`, 'Windy.com', 'General weather forecast'],
      [`https://meteo-parapente.com/#/${site.latitude},${site.longitude},7`, 'Meteo-Parapente', 'Paragliding-focused forecast'],
      [`http://www.xcmeteo.net/cs?p=${site.longitude}x${site.latitude}`, 'xcmeteo.net', 'GFS atmospheric profile'],
      [`https://www.windguru.cz/map/?lat=${site.latitude}&lon=${site.longitude}&zoom=11`, 'Windguru', 'Detailed wind models'],
      [`https://thermal.kk7.ch/#${site.latitude},${site.longitude},11`, 'Thermal map', 'Thermal hotspots'],
    ] : [];

    const flightLinks = site ? [
      [`https://www.xcontest.org/world/cs/vyhledavani-preletu/?list[sort]=time_start&filter[point]=${site.longitude}+${site.latitude}&filter[radius]=5000`, 'Recent flights', 'Latest tracks from this area'],
      [`https://www.xcontest.org/world/cs/vyhledavani-preletu/?list[sort]=pts&filter[point]=${site.longitude}+${site.latitude}&filter[radius]=5000`, 'Best flights', 'Top-scoring XC flights nearby'],
    ] : [];

    const urlSection = (title, icon, urls, emptyText) => (
      <Box sx={sectionSx}>
        {header(icon, title)}
        {urls.length ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {urls.map((url) => externalLink(url, safeHostname(url)))}
          </Box>
        ) : (
          <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>{emptyText}</Typography>
        )}
      </Box>
    );

    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
        <Box sx={sectionSx}>
          {header(<LanguageIcon color="primary" />, 'Local Resources')}
          {localResources.length ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {localResources.map((resource) => externalLink(
                resource.url,
                resource.name || resource.host || safeHostname(resource.url),
                safeHostname(resource.url),
              ))}
            </Box>
          ) : (
            <Typography variant="body2" color="text.secondary">No local club or site pages on file yet.</Typography>
          )}
        </Box>

        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2.5 }}>
          {urlSection('Webcams', <VideocamIcon color="primary" />, webcamUrls, 'None found yet')}
          {urlSection('Meteostations', <DeviceThermostatIcon color="primary" />, meteoUrls, 'None found yet')}
        </Box>

        <Box sx={sectionSx}>
          {header(<CloudIcon color="primary" />, 'Weather & Forecasts')}
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 1.25 }}>
            {weatherLinks.map(([href, label, description]) => externalLink(href, label, description))}
          </Box>
        </Box>

        <Box sx={sectionSx}>
          {header(<ParaglidingIcon color="primary" />, 'Flight Records')}
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 1.25 }}>
            {flightLinks.map(([href, label, description]) => externalLink(href, label, description))}
          </Box>
        </Box>

        {siteInfo?.site_name && (
          <Box sx={sectionSx}>
            {header(<SearchIcon color="primary" />, 'Do Your Own Research')}
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Quick searches to find more about this site.
            </Typography>
            <SearchRecs siteName={siteInfo.site_name} country={siteInfo.country} />
          </Box>
        )}
      </Box>
    );
  };

  if (predictionsQuery.isPending) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <LoadingSpinner />
      </Box>
    );
  }

  if (predictionsQuery.isError && !isNotFound(predictionsQuery.error)) {
    return (
      <Typography color="error" variant="h6" align="center" my={4}>
        Failed to load site data.
      </Typography>
    );
  }

  if (!site) return null;

  const displayName = siteInfo?.site_name || site.name || 'Site Details';
  const favoriteActive = isAuthenticated && isFavorite(numericSiteId);

  return (
    <Box sx={{ maxWidth: '1200px', margin: '0 auto', p: 2, minHeight: '100%' }}>
      <Helmet>
        <title>{`${displayName} – Parra-Glideator`}</title>
        <meta name="description" content={`Forecasts, seasonality and map for ${displayName}. Plan flights with Glideator metrics.`} />
        <link rel="canonical" href={window.location.origin + `/details/${siteId}`} />
        <meta property="og:title" content={`${displayName} – Parra-Glideator`} />
        <meta property="og:description" content={`Paragliding forecasts and info for ${displayName}.`} />
        <meta property="og:type" content="article" />
        <meta name="twitter:card" content="summary_large_image" />
      </Helmet>

      <Paper elevation={2}>
        <Box sx={{ p: isSmallScreen ? 1 : 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Tooltip title={isAuthenticated ? (favoriteActive ? 'Remove from favorites' : 'Add to favorites') : 'Log in to manage favorites'}>
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
              <Tooltip title={isAuthenticated ? 'Create notification' : 'Log in to create notifications'}>
                <span>
                  <IconButton
                    color="primary"
                    size="large"
                    disabled={!isAuthenticated}
                    onClick={() => navigate('/notifications', {
                      state: { notificationSetup: { siteId: numericSiteId, metric: selectedMetric } },
                    })}
                  >
                    <NotificationsActiveIcon />
                  </IconButton>
                </span>
              </Tooltip>
              <Typography variant="h4" component="h1" sx={{ mb: 0 }}>{displayName}</Typography>
            </Box>
            <img src={`${process.env.PUBLIC_URL}/logo192.png`} alt="Glideator" style={{ height: 48 }} />
          </Box>
        </Box>

        <Tabs
          value={activeTab}
          onChange={(event, newValue) => {
            void event;
            setActiveTab(newValue);
          }}
          variant={isSmallScreen ? 'scrollable' : 'fullWidth'}
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
              '& .MuiSvgIcon-root': { fontSize: '1.5rem', marginBottom: '4px' },
            },
          }}
        >
          <Tab label="Activity Forecast" icon={<TimelineIcon />} iconPosition="top" id="site-tab-0" aria-controls="site-tabpanel-0" />
          <Tab label="Season" icon={<CalendarMonthIcon />} iconPosition="top" id="site-tab-1" aria-controls="site-tabpanel-1" />
          <Tab label="Site Map" icon={<MapIcon />} iconPosition="top" id="site-tab-2" aria-controls="site-tabpanel-2" />
          <Tab label="Resources" icon={<LinkIcon />} iconPosition="top" id="site-tab-3" aria-controls="site-tabpanel-3" />
        </Tabs>

        <TabPanel value={activeTab} index={0}>
          <Box sx={{ display: 'flex', flexDirection: 'column', width: '100%', gap: 2 }}>
            {selectedDate && (
              <Box sx={{ display: 'flex', justifyContent: 'flex-end', minHeight: 32 }}>
                <ShareForecastButton
                  siteId={siteId}
                  siteName={displayName}
                  selectedDate={selectedDate}
                  selectedMetric={selectedMetric}
                  predictions={site.predictions}
                />
              </Box>
            )}

            <GlideatorForecast
              siteData={site}
              selectedDate={selectedDate}
              selectedMetric={selectedMetric}
              metrics={METRICS}
              onMetricChange={handleMetricChange}
              onDateChange={setSelectedDate}
              allDates={allDates}
              mapState={mapState}
              allSites={siteData}
            />

            <Typography
              variant="body2"
              color="text.secondary"
              component="div"
              sx={{ mt: 2, fontStyle: 'italic', textAlign: 'center', lineHeight: 1.55, maxWidth: 560, mx: 'auto' }}
            >
              <Box component="span" sx={{ display: 'block' }}>Decision support, not divine revelation.</Box>
              <Box component="span" sx={{ display: 'block' }}>Always check local conditions and use your judgment.</Box>
              <Box component="span" sx={{ display: 'block', mt: 0.5 }}>
                See{' '}
                <Link component={RouterLink} to="/about#scores" underline="hover" sx={{ fontWeight: 600, fontStyle: 'italic' }}>
                  How it works
                </Link>{' '}
                for more details.
              </Box>
            </Typography>

            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
              <Button
                variant="outlined"
                onClick={() => setShowWeatherDetails((visible) => !visible)}
                endIcon={<ExpandMoreIcon sx={{ transform: showWeatherDetails ? 'rotate(180deg)' : 'none' }} />}
              >
                {showWeatherDetails ? 'Hide' : "See What's Driving This"}
              </Button>
            </Box>

            <Fade in={showWeatherDetails} timeout={200} unmountOnExit>
              <Box data-testid="weather-details-panel" sx={{ mt: 2, pt: 1 }}>
                {renderForecastContent()}
              </Box>
            </Fade>

            {selectedDate && (
              <SimilarDaysPanel
                siteId={siteId}
                selectedDate={selectedDate}
                latitude={site.latitude}
                longitude={site.longitude}
                siteAltitude={site.altitude}
              />
            )}
          </Box>
        </TabPanel>

        <TabPanel value={activeTab} index={1}>
          {flightStatsQuery.isPending ? (
            <PanelLoading />
          ) : flightStatsQuery.data ? (
            <FlightStatsChart
              data={flightStatsQuery.data}
              metrics={METRICS}
              selectedMetric={selectedMetric}
              onMetricChange={handleMetricChange}
            />
          ) : (
            <Typography>Flight statistics are not available for this site.</Typography>
          )}
        </TabPanel>

        <TabPanel value={activeTab} index={2}>
          <SiteMap siteId={siteId} siteName={displayName} />
        </TabPanel>

        <TabPanel value={activeTab} index={3}>
          {renderResourcesContent()}
        </TabPanel>
      </Paper>
    </Box>
  );
};

export default Details;
