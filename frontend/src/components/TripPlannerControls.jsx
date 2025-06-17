import React, { useState, useCallback, useMemo, useEffect } from 'react';
import {
  Box,
  Card,
  Button,
  TextField,
  Typography,
  Stack,
  Divider,
  Slider,
  IconButton,
} from '@mui/material';
import ViewModeToggle from './ViewModeToggle';
import { useGeolocation } from '../hooks/useGeolocation';
import { DEFAULT_PLANNER_STATE, getDefaultDateRange } from '../types/ui-state';
import TimelineIcon from '@mui/icons-material/Timeline';
import SocialDistanceIcon from '@mui/icons-material/SocialDistance';
import FilterHdrIcon from '@mui/icons-material/FilterHdr';
import MyLocationIcon from '@mui/icons-material/MyLocation';

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
  onToggle 
}) => {
  const [isOpen, setIsOpen] = useState(false);

  const handleClick = () => {
    setIsOpen(true);
    if (!enabled) {
      onToggle(true);
    }
  };

  return (
    <>
      {/* Button container */}
      <Box sx={{ position: 'relative', width: 'fit-content' }}>
        <IconButton
          onClick={handleClick}
          sx={{
            backgroundColor: enabled ? 'rgba(22, 119, 255, 0.1)' : 'white',
            border: `1px solid ${enabled ? '#1677ff' : '#ddd'}`,
            borderRadius: '4px',
            padding: '6px',
            boxShadow: '0 2px 6px rgba(0,0,0,0.3)',
            width: '32px',
            height: '32px',
            '&:hover': {
              backgroundColor: enabled ? 'rgba(22, 119, 255, 0.2)' : '#f5f5f5',
            },
          }}
        >
          <Icon fontSize="small" color={enabled ? 'primary' : 'action'} />
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
            
            {enabled && (
              <Button 
                size="small" 
                onClick={() => {
                  onToggle(false);
                  setIsOpen(false);
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
      title="Minimum Flight Quality"
      subtitle="(XC Points)"
      enabled={enabled}
      onToggle={onToggle}
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
  locationError 
}) => {
  const [localDistance, setLocalDistance] = useState(distanceState.km);

  useEffect(() => {
    setLocalDistance(distanceState.km);
  }, [distanceState.km]);

  const marks = useMemo(() => [
    { value: 10, label: '10' },
    { value: 100, label: '100' },
    { value: 500, label: '500' },
    { value: 1000, label: '1k' }
  ], []);

  const formatDistance = (distance) => {
    if (distance >= 1000) return `${(distance / 1000).toFixed(1)}k km`;
    return `${distance} km`;
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
      <MetricStyleControl
        icon={SocialDistanceIcon}
        title="Distance from"
        subtitle="Location (km)"
        enabled={distanceState.enabled}
        onToggle={onToggle}
      >
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 1 }}>
          <IconButton
            size="small"
            onClick={onDetectLocation}
            disabled={isDetectingLocation}
            sx={{ 
              fontSize: '0.6rem',
              padding: '2px',
              minHeight: '20px',
              backgroundColor: distanceState.coords ? 'rgba(22, 119, 255, 0.1)' : 'transparent'
            }}
          >
            <MyLocationIcon fontSize="small" />
          </IconButton>
          
          <Slider
            orientation="vertical"
            value={localDistance}
            onChange={(e, val) => setLocalDistance(val)}
            onChangeCommitted={(e, val) => onDistanceChange(val)}
            min={10}
            max={1000}
            step={10}
            marks={marks}
            disabled={!distanceState.coords}
            valueLabelDisplay="off"
            sx={{
              height: '70%',
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
    { value: 1000, label: '1k' },
    { value: 2000, label: '2k' },
    { value: 3000, label: '3k' },
    { value: 4000, label: '4k' }
  ], []);

  const formatAltitude = (altitude) => {
    if (altitude >= 1000) return `${(altitude / 1000).toFixed(1)}k m`;
    return `${altitude} m`;
  };

  return (
    <MetricStyleControl
      icon={FilterHdrIcon}
      title="Site Altitude"
      subtitle="Range (m)"
      enabled={altitudeState.enabled}
      onToggle={onToggle}
    >
      <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 1 }}>
        <Slider
          orientation="vertical"
          value={localAltitude}
          onChange={(e, val) => setLocalAltitude(val)}
          onChangeCommitted={(e, val) => onAltitudeChange(val)}
          min={0}
          max={4000}
          step={100}
          marks={marks}
          valueLabelDisplay="off"
          sx={{
            height: '70%',
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
          {formatAltitude(localAltitude[0])} - {formatAltitude(localAltitude[1])}
        </Typography>
      </Box>
    </MetricStyleControl>
  );
};

/**
 * Unified Trip Planner Controls Component
 * Consolidates all user-editable inputs for the Plan a Trip page
 */
const TripPlannerControls = ({
  state = DEFAULT_PLANNER_STATE,
  setState,
  onSubmit,
  loading = false
}) => {
  const [dateRange, setDateRange] = useState(() => {
    const [defaultStart, defaultEnd] = getDefaultDateRange();
    return [
      state.dates[0] || defaultStart,
      state.dates[1] || defaultEnd
    ];
  });

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

  const handleSubmit = () => {
    if (dateRange[0] && dateRange[1] && onSubmit) {
      onSubmit(dateRange);
    }
  };

  const isSubmitEnabled = useMemo(() => {
    return dateRange[0] && dateRange[1] && !loading;
  }, [dateRange, loading]);

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

  React.useEffect(() => {
    if (detectedLocation) {
      setState(prev => ({
        ...prev,
        distance: { ...prev.distance, coords: detectedLocation, enabled: true }
      }));
    }
  }, [detectedLocation, setState]);

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
    setState({ ...state, view });
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
            />
          <AltitudeMetricControl
              altitudeState={state.altitude}
              onAltitudeChange={handleAltitudeChange}
              onToggle={handleAltitudeToggle}
            />
        </Stack>
        
        <Divider orientation="vertical" flexItem sx={{ display: { xs: 'none', md: 'block' } }}/>
        
        <Stack direction="row" spacing={1} alignItems="center">
          <Button
            variant="contained"
            onClick={handleSubmit}
            disabled={!isSubmitEnabled}
            sx={{ px: 3, height: 40 }}
          >
            {loading ? 'Planning...' : 'GO'}
          </Button>
          <ViewModeToggle
            currentView={state.view}
            onViewChange={handleViewModeChange}
            disabled={loading}
          />
        </Stack>
      </Box>
    </Card>
  );
};

export default TripPlannerControls; 