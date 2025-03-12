import React, { useState, useRef, useEffect } from 'react';
import { Box, Slider, Typography } from '@mui/material';
import { IconButton } from '@mui/material';
import TimelineIcon from '@mui/icons-material/Timeline';
import { useMap } from 'react-leaflet';

const MetricControl = ({ metrics, sliderValue, onSliderChange, onSliderChangeCommitted }) => {
  const [isOpen, setIsOpen] = useState(false);
  const controlRef = useRef(null);
  const map = useMap();

  const marks = metrics.map((metric, index) => ({
    value: index,
    // Convert "XC50" to "50", etc.
    label: metric.replace('XC', ''),
  }));

  useEffect(() => {
    if (!map) return;

    // Disable map drag when slider is open
    if (isOpen) {
      map.dragging.disable();
      map.scrollWheelZoom.disable();
    } else {
      map.dragging.enable();
      map.scrollWheelZoom.enable();
    }

    return () => {
      map.dragging.enable();
      map.scrollWheelZoom.enable();
    };
  }, [isOpen, map]);

  useEffect(() => {
    // Handle clicks outside the control
    const handleClickOutside = (event) => {
      if (controlRef.current && !controlRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    // Use mousedown for desktop and touchend for mobile
    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('touchend', handleClickOutside);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchend', handleClickOutside);
    };
  }, []);

  // Detect if device supports hover
  const isHoverableDevice = window.matchMedia('(hover: hover)').matches;

  const handleSliderInteraction = (e) => {
    e.stopPropagation();
    map.dragging.disable();
    map.scrollWheelZoom.disable();
  };

  const handleSliderEnd = (e) => {
    e.stopPropagation();
    if (!isOpen) {
      map.dragging.enable();
      map.scrollWheelZoom.enable();
    }
    
    // Ensure changes are committed when touch ends on mobile
    if (e.type === 'touchend') {
      onSliderChangeCommitted(e, sliderValue);
    }
  };

  return (
    <>
      {isOpen && (
        <Box
          sx={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 999,
            cursor: 'default',
          }}
          onMouseDown={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setIsOpen(false);
          }}
          onTouchStart={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setIsOpen(false);
          }}
        />
      )}
      <Box
        ref={controlRef}
        className="metric-control"
        sx={{
          pointerEvents: 'auto',
          '& *': {
            pointerEvents: 'auto !important'
          }
        }}
        onMouseEnter={(e) => {
          e.stopPropagation();
          isHoverableDevice && setIsOpen(true);
        }}
        onMouseLeave={(e) => {
          e.stopPropagation();
          isHoverableDevice && setIsOpen(false);
        }}
      >
        {!isOpen && (
          <IconButton
            onMouseDown={(e) => e.stopPropagation()}
            onTouchStart={(e) => e.stopPropagation()}
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              if (!isHoverableDevice) {
                setIsOpen(true);
              }
            }}
            sx={{
              backgroundColor: 'white',
              borderRadius: '4px',
              padding: '6px',
              boxShadow: '0 2px 6px rgba(0,0,0,0.3)',
              '&:hover': {
                backgroundColor: '#f5f5f5',
              },
            }}
          >
            <TimelineIcon />
          </IconButton>
        )}
        
        {isOpen && (
          <Box
            className="metric-slider"
            onMouseDown={(e) => e.stopPropagation()}
            onTouchStart={(e) => e.stopPropagation()}
            sx={{
              backgroundColor: 'white',
              padding: '12px',
              borderRadius: '4px',
              boxShadow: '0 2px 6px rgba(0,0,0,0.3)',
              height: 'clamp(180px, 30vh, 250px)',
              width: '80px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              position: 'relative',
              paddingTop: '24px',
              pointerEvents: 'auto',
            }}
          >
            <Typography 
              variant="subtitle2" 
              sx={{ 
                marginBottom: '8px',
                fontSize: '0.75rem',
                textAlign: 'center',
                width: '100%',
              }}
            >
              minimum XC points
            </Typography>
            <Slider
              orientation="vertical"
              value={sliderValue}
              min={0}
              max={metrics.length - 1}
              step={1}
              marks={marks}
              onMouseDown={handleSliderInteraction}
              onTouchStart={handleSliderInteraction}
              onMouseUp={handleSliderEnd}
              onTouchEnd={handleSliderEnd}
              onChange={(e, value) => {
                e.stopPropagation();
                onSliderChange(e, value);
              }}
              onChangeCommitted={(e, value) => {
                e.stopPropagation();
                onSliderChangeCommitted(e, value);
              }}
              valueLabelDisplay="off"
              aria-labelledby="metric-slider"
              sx={{
                height: '80%',
                padding: '0 12px',
                '& .MuiSlider-markLabel': {
                  transform: 'translateX(10px)',
                  whiteSpace: 'nowrap',
                  fontSize: '0.7rem',
                  color: '#555',
                }
              }}
            />
          </Box>
        )}
      </Box>
    </>
  );
};

export default MetricControl; 