import React, { useState, useCallback, useMemo, useEffect } from 'react';
import {
  Box,
  Card,
  Button,
  TextField,
  Typography,
  Stack,
  Slider,
  IconButton,
  Autocomplete,
  Chip,
  Tooltip,
} from '@mui/material';
import ViewModeToggle from './ViewModeToggle';
import { useGeolocation } from '../hooks/useGeolocation';
import { useAuth } from '../context/AuthContext';
import { DEFAULT_PLANNER_STATE, getDefaultDateRange } from '../types/ui-state';
import TimelineIcon from '@mui/icons-material/Timeline';
import SocialDistanceIcon from '@mui/icons-material/SocialDistance';
import FilterHdrIcon from '@mui/icons-material/FilterHdr';
import LocalOfferIcon from '@mui/icons-material/LocalOffer';
import HomeIcon from '@mui/icons-material/Home';
import MyLocationIcon from '@mui/icons-material/MyLocation';
import { fetchAllTags } from '../api';

const METRICS = ['XC0', 'XC10', 'XC20', 'XC30', 'XC40', 'XC50', 'XC60', 'XC70', 'XC80', 'XC90', 'XC100'];

/**
 * Metric-style Control Component
 * Replicates the style of StandaloneMetricControl with modal overlay
 */
const MetricStyleControl = ({ 
  icon: Icon, 
  title, 
  subtitle, 
  enabled, 
  children, 
  onToggle,
  showDisableButton = true
}) => {
  const [isOpen, setIsOpen] = useState(false);

  const handleClick = () => {
    setIsOpen(true);
    // Don't automatically enable - let user control the state via the Enable/Disable buttons
  };

  return (
    <>
      {/* Button container */}
      <Box sx={{ position: 'relative', width: 'fit-content' }}>
        <IconButton
          onClick={handleClick}
          sx={{
            backgroundColor: 'white',
            border: '1px solid #ddd',
            borderRadius: '4px',
            padding: '6px',
            boxShadow: '0 2px 6px rgba(0,0,0,0.3)',
            width: '32px',
            height: '32px',
            '&:hover': {
              backgroundColor: '#f5f5f5',
            },
          }}
        >
          <Icon fontSize="small" color="action" />
        </IconButton>
      </Box>
      
      {/* Overlay and centered slider */}
      {isOpen && (
        <Box
          onClick={() => setIsOpen(false)}
          sx={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 1200,
          }}
        >
          <Box
            onClick={(e) => e.stopPropagation()}
            sx={{
              backgroundColor: 'white',
              padding: '16px',
              borderRadius: '8px',
              boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
              height: 'clamp(180px, 30vh, 250px)',
              width: '80px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              position: 'relative',
              paddingTop: '16px',
            }}
          >
            <Typography 
              variant="subtitle1" 
              sx={{ 
                marginBottom: '12px',
                marginTop: '0px',
                fontWeight: 'bold',
                textAlign: 'center',
                width: '100%',
              }}
            >
              <span style={{ display: 'block', fontSize: '0.75rem' }}>{title}</span>
              <span style={{ display: 'block', fontSize: '0.65rem', marginTop: '2px' }}>{subtitle}</span>
            </Typography>
            
            <Box sx={{ height: '80%', width: '100%', padding: '0 12px', marginBottom: '12px' }}>
              {children}
            </Box>
            
            {enabled && showDisableButton && (
              <Button 
                size="small" 
                onClick={() => {
                  onToggle(false);
                  // Don't close the modal, just disable the content
                }}
                sx={{ 
                  fontSize: '0.6rem', 
                  padding: '2px 6px',
                  minWidth: 'auto'
                }}
              >
                Disable
              </Button>
            )}
            
            {!enabled && showDisableButton && (
              <Button 
                size="small" 
                onClick={() => {
                  onToggle(true);
                }}
                sx={{ 
                  fontSize: '0.6rem', 
                  padding: '2px 6px',
                  minWidth: 'auto'
                }}
              >
                Enable
              </Button>
            )}
            
            {/* Close button */}
            <Box
              onClick={() => setIsOpen(false)}
              sx={{
                position: 'absolute',
                top: -5,
                right: -5,
                width: 20,
                height: 20,
                borderRadius: '50%',
                backgroundColor: 'rgba(0, 0, 0, 0.5)',
                color: 'white',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                fontSize: '12px',
                '&:hover': {
                  backgroundColor: 'rgba(0, 0, 0, 0.7)',
                }
              }}
            >
              ×
            </Box>
          </Box>
        </Box>
      )}
    </>
  );
};

/**
 * Flight Quality Control - matches MetricControl exactly
 */
const FlightQualityMetricControl = ({ 
  selectedValues, 
  onSelectionChange, 
  enabled, 
  onToggle 
}) => {
  const propSliderValue = useMemo(() => selectedValues.length > 0 
    ? Math.max(...selectedValues.map(v => METRICS.indexOf(v)))
    : 0, [selectedValues]);
  
  const [localSliderValue, setLocalSliderValue] = useState(propSliderValue);

  useEffect(() => {
    setLocalSliderValue(propSliderValue);
  }, [propSliderValue]);

  const marks = useMemo(() => METRICS.map((metric, index) => ({
    value: index,
    label: metric.replace('XC', ''),
  })), []);

  const handleSliderChange = (event, value) => {
    setLocalSliderValue(value);
  };

  const handleSliderChangeCommitted = (event, value) => {
    const newSelection = METRICS.slice(0, value + 1);
    onSelectionChange(newSelection);
  };

  return (
    <MetricStyleControl
      icon={TimelineIcon}
      title="Flight Quality"
      subtitle="(XC Points)"
      enabled={enabled}
      onToggle={onToggle}
      showDisableButton={false}
    >
      <Slider
        orientation="vertical"
        value={localSliderValue}
        min={0}
        max={METRICS.length - 1}
        step={1}
        marks={marks}
        onChange={handleSliderChange}
        onChangeCommitted={handleSliderChangeCommitted}
        valueLabelDisplay="off"
        sx={{
          height: '100%',
          marginTop: '8px',
          '& .MuiSlider-markLabel': {
            transform: 'translateX(10px) translateY(50%)',
            margin: 0,
            whiteSpace: 'nowrap',
            fontSize: '0.7rem',
            color: '#555',
          },
          '& .MuiSlider-thumb': {
            width: 16,
            height: 16,
          },
          '& .MuiSlider-track': {
            width: 6,
          },
          '& .MuiSlider-rail': {
            width: 6,
          }
        }}
      />
    </MetricStyleControl>
  );
};

/**
 * Distance Control - metric style
 */
const DistanceMetricControl = ({
  distanceState,
  onDistanceChange,
  onToggle,
  onDetectLocation,
  isDetectingLocation,
  locationError,
  homeLocation,
  onLocationSourceChange
}) => {
  const [localDistance, setLocalDistance] = useState(distanceState.km);
  const locationSource = distanceState.locationSource || 'current';
  const hasHomeLocation = homeLocation && homeLocation.latitude && homeLocation.longitude;

  useEffect(() => {
    setLocalDistance(distanceState.km);
  }, [distanceState.km]);

  // Automatically try to get location when filter is enabled and no coords exist and source is 'current'
  useEffect(() => {
    if (distanceState.enabled && !distanceState.coords && !isDetectingLocation && locationSource === 'current') {
      onDetectLocation();
    }
  }, [distanceState.enabled, distanceState.coords, isDetectingLocation, onDetectLocation, locationSource]);

  const handleLocationSourceChange = (source) => {
    if (source === 'home' && hasHomeLocation) {
      onLocationSourceChange(source, homeLocation);
    } else if (source === 'current') {
      onLocationSourceChange(source, null);
      // Trigger geolocation detection
      onDetectLocation();
    }
  };

  const marks = useMemo(() => [
    { value: 10, label: '10' },
    { value: 100, label: '100' },
    { value: 200, label: '200' },
    { value: 300, label: '300' },
    { value: 400, label: '400' },
    { value: 500, label: '500' },
    { value: 600, label: '600' },
    { value: 700, label: '700' },
    { value: 800, label: '800' },
    { value: 900, label: '900' },
    { value: 1000, label: '1k' }
  ], []);

  const formatDistance = (distance) => {
    if (distance >= 1000) return `${(distance / 1000).toFixed(1)}k km`;
    return `${distance} km`;
  };

  const getSubtitle = () => {
    if (!distanceState.enabled) return '(km)';
    return locationSource === 'home' ? 'from home' : 'from location';
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
      <MetricStyleControl
        icon={SocialDistanceIcon}
        title="Distance"
        subtitle={getSubtitle()}
        enabled={distanceState.enabled}
        onToggle={onToggle}
        showDisableButton={true}
      >
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          {/* Location source toggle */}
          {distanceState.enabled && (
            <Box sx={{ display: 'flex', gap: 0.5, mb: 1, justifyContent: 'center' }}>
              <Tooltip title="Use current location">
                <IconButton
                  size="small"
                  onClick={() => handleLocationSourceChange('current')}
                  sx={{
                    backgroundColor: locationSource === 'current' ? 'primary.main' : 'transparent',
                    color: locationSource === 'current' ? 'white' : 'action.active',
                    border: '1px solid',
                    borderColor: locationSource === 'current' ? 'primary.main' : 'divider',
                    padding: '4px',
                    '&:hover': {
                      backgroundColor: locationSource === 'current' ? 'primary.dark' : 'action.hover',
                    }
                  }}
                >
                  <MyLocationIcon sx={{ fontSize: '0.9rem' }} />
                </IconButton>
              </Tooltip>
              <Tooltip title={hasHomeLocation ? 'Use home location' : 'Set home in Profile'}>
                <span>
                  <IconButton
                    size="small"
                    onClick={() => handleLocationSourceChange('home')}
                    disabled={!hasHomeLocation}
                    sx={{
                      backgroundColor: locationSource === 'home' ? 'primary.main' : 'transparent',
                      color: locationSource === 'home' ? 'white' : 'action.active',
                      border: '1px solid',
                      borderColor: locationSource === 'home' ? 'primary.main' : 'divider',
                      padding: '4px',
                      '&:hover': {
                        backgroundColor: locationSource === 'home' ? 'primary.dark' : 'action.hover',
                      },
                      '&.Mui-disabled': {
                        opacity: 0.5,
                      }
                    }}
                  >
                    <HomeIcon sx={{ fontSize: '0.9rem' }} />
                  </IconButton>
                </span>
              </Tooltip>
            </Box>
          )}

          {!distanceState.coords && distanceState.enabled && locationSource === 'current' && (
            <Typography variant="caption" sx={{
              fontSize: '0.6rem',
              textAlign: 'center',
              color: 'text.secondary',
              marginBottom: '8px'
            }}>
              {isDetectingLocation ? 'Getting location...' : 'Location access needed'}
            </Typography>
          )}

          {!distanceState.enabled && (
            <Typography variant="caption" sx={{
              fontSize: '0.6rem',
              textAlign: 'center',
              color: 'text.secondary',
              marginBottom: '8px'
            }}>
              Filter is disabled
            </Typography>
          )}

          <Slider
            orientation="vertical"
            value={localDistance}
            onChange={(e, val) => setLocalDistance(val)}
            onChangeCommitted={(e, val) => onDistanceChange(val)}
            min={10}
            max={1000}
            step={10}
            marks={marks}
            disabled={!distanceState.coords || !distanceState.enabled}
            valueLabelDisplay="off"
            sx={{
              height: distanceState.coords ? 'calc(100% - 20px)' : 'calc(100% - 40px)',
              marginTop: '8px',
              '& .MuiSlider-markLabel': {
                transform: 'translateX(10px) translateY(50%)',
                margin: 0,
                whiteSpace: 'nowrap',
                fontSize: '0.7rem',
                color: '#555',
              },
              '& .MuiSlider-thumb': {
                width: 16,
                height: 16,
              },
              '& .MuiSlider-track': {
                width: 6,
              },
              '& .MuiSlider-rail': {
                width: 6,
              }
            }}
          />

          <Typography variant="caption" sx={{ fontSize: '0.6rem', textAlign: 'center' }}>
            {formatDistance(localDistance)}
          </Typography>
        </Box>
      </MetricStyleControl>
    </Box>
  );
};

/**
 * Altitude Control - metric style
 */
const AltitudeMetricControl = ({ 
  altitudeState, 
  onAltitudeChange, 
  onToggle 
}) => {
  const [localAltitude, setLocalAltitude] = useState([altitudeState.min, altitudeState.max]);

  useEffect(() => {
    setLocalAltitude([altitudeState.min, altitudeState.max]);
  }, [altitudeState.min, altitudeState.max]);

  const marks = useMemo(() => [
    { value: 0, label: '0' },
    { value: 500, label: '0.5k' },
    { value: 1000, label: '1k' },
    { value: 1500, label: '1.5k' },
    { value: 2000, label: '2k' },
    { value: 2500, label: '2.5k' }
  ], []);

  const formatAltitude = (altitude) => {
    if (altitude >= 1000) return `${(altitude / 1000).toFixed(1)}k m`;
    return `${altitude} m`;
  };

  return (
    <MetricStyleControl
      icon={FilterHdrIcon}
      title="Altitude"
      subtitle="(m)"
      enabled={altitudeState.enabled}
      onToggle={onToggle}
      showDisableButton={false}
    >
      <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        <Slider
          orientation="vertical"
          value={localAltitude}
          onChange={(e, val) => setLocalAltitude(val)}
          onChangeCommitted={(e, val) => onAltitudeChange(val)}
          min={0}
          max={2500}
          step={100}
          marks={marks}
          valueLabelDisplay="off"
          sx={{
            height: 'calc(100% - 20px)',
            marginTop: '8px',
            '& .MuiSlider-markLabel': {
              transform: 'translateX(10px) translateY(50%)',
              margin: 0,
              whiteSpace: 'nowrap',
              fontSize: '0.7rem',
              color: '#555',
            },
            '& .MuiSlider-thumb': {
              width: 16,
              height: 16,
            },
            '& .MuiSlider-track': {
              width: 6,
            },
            '& .MuiSlider-rail': {
              width: 6,
            }
          }}
        />
        
        <Typography variant="caption" sx={{ fontSize: '0.6rem', textAlign: 'center', marginTop: '4px' }}>
          {formatAltitude(localAltitude[0])} - {formatAltitude(localAltitude[1])}
        </Typography>
      </Box>
    </MetricStyleControl>
  );
};

/**
 * Tags Control - searchable multi-select with chips
 */
const TagsMetricControl = ({ selectedTags, onSelectionChange }) => {
  const [allTags, setAllTags] = useState([]);
  const [loading, setLoading] = useState(false);

  const POPULAR_TAGS = useMemo(() => ['car', 'shuttle', 'lift', 'Alps', 'Pyrenees', 'Apennines'], []);

  const ensureTagsLoaded = useCallback(async () => {
    if (allTags.length > 0 || loading) return;
    setLoading(true);
    try {
      const tags = await fetchAllTags(2);
      // Order: specified popular tags first (in given order), then the rest alphabetically
      const popularSet = new Set(POPULAR_TAGS);
      const popularInData = POPULAR_TAGS.filter(t => tags.includes(t));
      const rest = tags.filter(t => !popularSet.has(t)).sort((a, b) => a.localeCompare(b));
      setAllTags([...popularInData, ...rest]);
    } catch (e) {
      // silent fail
    } finally {
      setLoading(false);
    }
  }, [allTags.length, loading, POPULAR_TAGS]);

  const filterOptions = useCallback((options, { inputValue }) => {
    if (!inputValue) return options;
    const q = inputValue.toLowerCase();
    return options.filter(opt => opt.toLowerCase().includes(q));
  }, []);

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 240 }}>
      <LocalOfferIcon fontSize="small" color="action" />
      <Autocomplete
        multiple
        options={allTags}
        value={selectedTags}
        onChange={(e, val) => onSelectionChange(val)}
        onOpen={ensureTagsLoaded}
        filterOptions={filterOptions}
        filterSelectedOptions
        loading={loading}
        renderTags={(value, getTagProps) =>
          value.map((option, index) => (
            <Chip variant="outlined" size="small" label={option} {...getTagProps({ index })} />
          ))
        }
        renderInput={(params) => (
          <TextField {...params} size="small" label="Tags" placeholder={loading ? 'Loading…' : 'Filter by tags'} onFocus={ensureTagsLoaded} />
        )}
        sx={{ minWidth: 220 }}
      />
    </Box>
  );
};

/**
 * Unified Trip Planner Controls Component
 * Consolidates all user-editable inputs for the Plan a Trip page
 */
const TripPlannerControls = ({
  state = DEFAULT_PLANNER_STATE,
  setState,
  onViewChange
}) => {
  const [dateRange, setDateRange] = useState(() => {
    const [defaultStart, defaultEnd] = getDefaultDateRange();
    return [
      state.dates[0] || defaultStart,
      state.dates[1] || defaultEnd
    ];
  });

  const { profile } = useAuth();

  // Create home location object from profile
  const homeLocation = useMemo(() => {
    if (profile?.home_lat && profile?.home_lon) {
      return { latitude: profile.home_lat, longitude: profile.home_lon };
    }
    return null;
  }, [profile?.home_lat, profile?.home_lon]);

  const {
    location: detectedLocation,
    isLoading: isDetectingLocation,
    error: locationError,
    detectLocation
  } = useGeolocation();

  const formatDateForInput = (date) => {
    if (!date) return '';
    return date.toISOString().split('T')[0];
  };

  const getMinDate = () => {
    return new Date().toISOString().split('T')[0];
  };

  const handleStartDateChange = (event) => {
    const dateStr = event.target.value;
    const newDate = dateStr ? new Date(dateStr) : null;
    const newRange = [newDate, dateRange[1]];
    setDateRange(newRange);
    setState({ ...state, dates: newRange });
  };

  const handleEndDateChange = (event) => {
    const dateStr = event.target.value;
    const newDate = dateStr ? new Date(dateStr) : null;
    const newRange = [dateRange[0], newDate];
    setDateRange(newRange);
    setState({ ...state, dates: newRange });
  };



  const handleDistanceToggle = (enabled) => {
    setState(prev => ({
      ...prev,
      distance: { ...prev.distance, enabled }
    }));
  };

  const handleDistanceChange = useCallback((value) => {
    setState(prev => ({
      ...prev,
      distance: { ...prev.distance, km: value }
    }));
  }, [setState]);

  const handleLocationDetect = () => {
    detectLocation();
  };

  // Handle location source change (home vs current)
  const handleLocationSourceChange = useCallback((source, coords) => {
    setState(prev => ({
      ...prev,
      distance: {
        ...prev.distance,
        locationSource: source,
        coords: coords,
        enabled: true
      }
    }));
  }, [setState]);

  // Update coords when geolocation is detected (only if source is 'current')
  React.useEffect(() => {
    if (detectedLocation && state.distance.locationSource === 'current') {
      setState(prev => ({
        ...prev,
        distance: { ...prev.distance, coords: detectedLocation, enabled: true }
      }));
    }
  }, [detectedLocation, setState, state.distance.locationSource]);

  const handleAltitudeToggle = (enabled) => {
    setState(prev => ({
      ...prev,
      altitude: { ...prev.altitude, enabled }
    }));
  };

  const handleAltitudeChange = useCallback((value) => {
    setState(prev => ({
      ...prev,
      altitude: {
        ...prev.altitude,
        min: value[0],
        max: value[1]
      }
    }));
  }, [setState]);

  const handleFlightQualityToggle = (enabled) => {
    setState(prev => ({
      ...prev,
      flightQuality: { ...prev.flightQuality, enabled }
    }));
  };

  const handleFlightQualityChange = (selectedValues) => {
    const newSelectedMetric = selectedValues.reduce((max, current) => {
      const maxNum = parseInt(max.replace('XC', ''), 10);
      const currentNum = parseInt(current.replace('XC', ''), 10);
      return currentNum > maxNum ? current : max;
    }, 'XC0');

    setState(prev => ({
      ...prev,
      flightQuality: { ...prev.flightQuality, selectedValues },
      selectedMetric: newSelectedMetric
    }));
  };

  const handleViewModeChange = (view) => {
    if (onViewChange) {
      onViewChange(view);
    } else {
      setState({ ...state, view });
    }
  };

  return (
    <Card
      sx={{
        p: { xs: 2, sm: 3 },
        borderRadius: 3,
        boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
        backgroundColor: 'white'
      }}
    >
      <Box sx={{
        display: 'flex',
        flexDirection: { xs: 'column', md: 'row' },
        alignItems: { xs: 'stretch', md: 'center' },
        gap: 2,
      }}>
        <Box sx={{ 
          display: 'flex', 
          flexWrap: 'wrap', 
          alignItems: 'center', 
          gap: 2, 
          flex: 1 
        }}>
          <TextField
            label="Start Date"
            type="date"
            value={formatDateForInput(dateRange[0])}
            onChange={handleStartDateChange}
            inputProps={{ min: getMinDate() }}
            size="small"
            sx={{ minWidth: 150, flex: 1 }}
            InputLabelProps={{ shrink: true }}
          />
          <TextField
            label="End Date"
            type="date"
            value={formatDateForInput(dateRange[1])}
            onChange={handleEndDateChange}
            inputProps={{ min: dateRange[0] ? formatDateForInput(dateRange[0]) : getMinDate() }}
            size="small"
            sx={{ minWidth: 150, flex: 1 }}
            InputLabelProps={{ shrink: true }}
          />
        </Box>

        <Box sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 2,
          flexWrap: 'wrap',
          justifyContent: { xs: 'space-between', md: 'flex-end' }
        }}>
          <Stack direction="row" spacing={1} alignItems="center">
            <FlightQualityMetricControl
                selectedValues={state.flightQuality.selectedValues}
                onSelectionChange={handleFlightQualityChange}
                enabled={state.flightQuality.enabled}
                onToggle={handleFlightQualityToggle}
              />
            <DistanceMetricControl
                distanceState={state.distance}
                onDistanceChange={handleDistanceChange}
                onToggle={handleDistanceToggle}
                onDetectLocation={handleLocationDetect}
                isDetectingLocation={isDetectingLocation}
                locationError={locationError}
                homeLocation={homeLocation}
                onLocationSourceChange={handleLocationSourceChange}
              />
            <AltitudeMetricControl
                altitudeState={state.altitude}
                onAltitudeChange={handleAltitudeChange}
                onToggle={handleAltitudeToggle}
              />
          </Stack>
          <Box sx={{ flexBasis: { xs: '100%', md: 'auto' }, flexGrow: { xs: 1, md: 0 }, mt: { xs: 1, md: 0 } }}>
            <TagsMetricControl
              selectedTags={state.tags || []}
              onSelectionChange={(tags) => setState(prev => ({ ...prev, tags }))}
            />
          </Box>
          
          <ViewModeToggle
            currentView={state.view}
            onViewChange={handleViewModeChange}
          />
        </Box>
      </Box>
    </Card>
  );
};

export default TripPlannerControls; 