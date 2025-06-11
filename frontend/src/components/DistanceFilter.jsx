import React, { useState } from 'react';
import {
  Box,
  Typography,
  Slider,
  Button,
  Switch,
  FormControlLabel,
  Alert,
  Tooltip
} from '@mui/material';
import {
  LocationOn as LocationIcon,
  MyLocation as MyLocationIcon,
  Info as InfoIcon
} from '@mui/icons-material';

const DistanceFilter = ({ 
  userLocation, 
  onLocationChange, 
  maxDistance, 
  onMaxDistanceChange, 
  enabled, 
  onEnabledChange 
}) => {
  const [locationError, setLocationError] = useState(null);
  const [isGettingLocation, setIsGettingLocation] = useState(false);

  const handleGetLocation = () => {
    if (!navigator.geolocation) {
      setLocationError('Geolocation is not supported by this browser');
      return;
    }

    setIsGettingLocation(true);
    setLocationError(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const location = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy
        };
        onLocationChange(location);
        setIsGettingLocation(false);
      },
      (error) => {
        let errorMessage = 'Unable to retrieve your location';
        switch (error.code) {
          case error.PERMISSION_DENIED:
            errorMessage = 'Location access denied. Please enable location permissions.';
            break;
          case error.POSITION_UNAVAILABLE:
            errorMessage = 'Location information is unavailable.';
            break;
          case error.TIMEOUT:
            errorMessage = 'Location request timed out.';
            break;
          default:
            errorMessage = 'An unknown error occurred while retrieving location.';
            break;
        }
        setLocationError(errorMessage);
        setIsGettingLocation(false);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 300000 // 5 minutes
      }
    );
  };

  const formatDistance = (distance) => {
    if (distance >= 1000) {
      return `${(distance / 1000).toFixed(1)}k km`;
    }
    return `${distance} km`;
  };

  const distanceMarks = [
    { value: 50, label: '50km' },
    { value: 100, label: '100km' },
    { value: 200, label: '200km' },
    { value: 500, label: '500km' },
    { value: 1000, label: '1000km' },
  ];

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: '280px' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <FormControlLabel
          control={
            <Switch
              checked={enabled}
              onChange={(e) => onEnabledChange(e.target.checked)}
              size="small"
            />
          }
          label={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Typography variant="body2" sx={{ fontSize: '0.875rem' }}>
                Distance Filter
              </Typography>
              <Tooltip title="Filter sites by maximum distance from your location">
                <InfoIcon sx={{ fontSize: '16px', color: 'text.secondary' }} />
              </Tooltip>
            </Box>
          }
        />
      </Box>

      {enabled && (
        <>
          {/* Location Section */}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
              Your Location
            </Typography>
            
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Button
                variant="outlined"
                size="small"
                startIcon={isGettingLocation ? null : <MyLocationIcon />}
                onClick={handleGetLocation}
                disabled={isGettingLocation}
                sx={{ minWidth: 'auto', px: 1 }}
              >
                {isGettingLocation ? 'Getting...' : 'Detect'}
              </Button>
              
              {userLocation && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  <LocationIcon sx={{ fontSize: '16px', color: 'success.main' }} />
                  <Typography variant="caption" color="success.main" sx={{ fontSize: '0.75rem' }}>
                    {userLocation.latitude.toFixed(3)}, {userLocation.longitude.toFixed(3)}
                  </Typography>
                </Box>
              )}
            </Box>

            {locationError && (
              <Alert severity="warning" sx={{ py: 0.5, fontSize: '0.75rem' }}>
                {locationError}
              </Alert>
            )}
          </Box>

          {/* Distance Slider Section */}
          {userLocation && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Typography variant="caption" color="text.secondary" sx={{ fontSize: '0.75rem' }}>
                  Maximum Distance
                </Typography>
                <Typography variant="caption" sx={{ fontSize: '0.75rem', fontWeight: 'bold' }}>
                  {formatDistance(maxDistance)}
                </Typography>
              </Box>
              
              <Slider
                value={maxDistance}
                onChange={(e, value) => onMaxDistanceChange(value)}
                min={25}
                max={1000}
                step={25}
                marks={distanceMarks}
                valueLabelDisplay="auto"
                valueLabelFormat={formatDistance}
                sx={{
                  '& .MuiSlider-markLabel': {
                    fontSize: '0.65rem',
                    color: 'text.secondary'
                  }
                }}
              />
            </Box>
          )}
        </>
      )}
    </Box>
  );
};

export default DistanceFilter; 