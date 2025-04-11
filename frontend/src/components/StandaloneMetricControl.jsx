import React, { useState, useRef, useEffect } from 'react';
import { Box, Slider, Typography, IconButton } from '@mui/material';
import TimelineIcon from '@mui/icons-material/Timeline';

const StandaloneMetricControl = ({ metrics, selectedMetric, onMetricChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const controlRef = useRef(null);
  const sliderRef = useRef(null);
  
  // Find the index of the selected metric
  const sliderValue = metrics.indexOf(selectedMetric);

  const marks = metrics.map((metric, index) => ({
    value: index,
    // Convert "XC50" to "50", etc.
    label: metric.replace('XC', ''),
  }));

  useEffect(() => {
    // Handle clicks outside the control when the slider is open
    const handleClickOutside = (event) => {
      if (isOpen && sliderRef.current && !sliderRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('touchend', handleClickOutside);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('touchend', handleClickOutside);
    };
  }, [isOpen]);

  const handleSliderChange = (e, value) => {
    e.stopPropagation();
    onMetricChange(metrics[value]);
  };

  return (
    <>
      {/* Button container */}
      <Box
        ref={controlRef}
        sx={{
          position: 'relative',
          width: 'fit-content'
        }}
      >
        <IconButton
          onClick={() => setIsOpen(true)}
          sx={{
            backgroundColor: 'white',
            borderRadius: '4px',
            padding: '6px',
            boxShadow: '0 2px 6px rgba(0,0,0,0.3)',
            '&:hover': {
              backgroundColor: '#f5f5f5',
            },
            width: '32px',
            height: '32px',
          }}
        >
          <TimelineIcon fontSize="small" />
        </IconButton>
      </Box>
      
      {/* Overlay and centered slider */}
      {isOpen && (
        <Box
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
            ref={sliderRef}
            className="metric-slider"
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
              <span style={{ display: 'block', fontSize: '0.75rem' }}>Minimum Flight Quality</span>
              <span style={{ display: 'block', fontSize: '0.65rem', marginTop: '2px' }}>(XC Points)</span>
            </Typography>
            
            <Box sx={{ height: '80%', width: '100%', padding: '0 12px', marginBottom: '12px' }}>
              <Slider
                orientation="vertical"
                value={sliderValue}
                min={0}
                max={metrics.length - 1}
                step={1}
                marks={marks}
                onChange={handleSliderChange}
                onChangeCommitted={handleSliderChange}
                valueLabelDisplay="off"
                aria-labelledby="metric-slider"
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
            </Box>
          </Box>
        </Box>
      )}
    </>
  );
};

export default StandaloneMetricControl; 