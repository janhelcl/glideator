import React, { useState, useRef, useEffect } from 'react';
import { Box, Slider, Typography } from '@mui/material';
import { IconButton } from '@mui/material';
import TimelineIcon from '@mui/icons-material/Timeline';
import PreventLeafletControl from './PreventLeafletControl';

const MetricControl = ({ metrics, sliderValue, onSliderChange, onSliderChangeCommitted }) => {
  const [isOpen, setIsOpen] = useState(false);
  const controlRef = useRef(null);

  const marks = metrics.map((metric, index) => ({
    value: index,
    // Convert "XC50" to "50", etc.
    label: metric.replace('XC', ''),
  }));

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

  return (
    <PreventLeafletControl>
      <Box
        ref={controlRef}
        sx={{
          position: 'absolute',
          top: 'clamp(60px, 10vh, 75px)',
          right: 'clamp(10px, 2vw, 20px)',
          zIndex: 1000,
          '& *': {
            pointerEvents: 'auto !important'
          }
        }}
        onMouseEnter={() => isHoverableDevice && setIsOpen(true)}
        onMouseLeave={() => isHoverableDevice && setIsOpen(false)}
      >
        {!isOpen && (
          <IconButton
            onClick={(e) => {
              if (!isHoverableDevice) {
                e.stopPropagation();
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
              paddingTop: '24px'
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
              onChange={onSliderChange}
              onChangeCommitted={onSliderChangeCommitted}
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
    </PreventLeafletControl>
  );
};

export default MetricControl; 