import React, { useState } from 'react';
import { Box, Slider, Typography } from '@mui/material';
import { IconButton } from '@mui/material';
import TimelineIcon from '@mui/icons-material/Timeline';
import PreventLeafletControl from './PreventLeafletControl';

const MetricControl = ({ metrics, sliderValue, onSliderChange, onSliderChangeCommitted }) => {
  const [isOpen, setIsOpen] = useState(false);

  const marks = metrics.map((metric, index) => ({
    value: index,
    label: metric,
  }));

  return (
    <PreventLeafletControl>
      <Box
        sx={{
          position: 'absolute',
          top: 'clamp(60px, 10vh, 75px)',
          right: 'clamp(10px, 2vw, 20px)',
          zIndex: 1000,
          '& *': {
            pointerEvents: 'auto !important'
          }
        }}
      >
        <IconButton
          onClick={() => setIsOpen(!isOpen)}
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
        
        {isOpen && (
          <Box
            className="metric-slider"
            sx={{
              position: 'absolute',
              top: '40px',
              right: 0,
              backgroundColor: 'rgba(255, 255, 255, 0.9)',
              padding: 'clamp(8px, 1.5vw, 12px)',
              borderRadius: '4px',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
              backdropFilter: 'blur(5px)',
              height: 'clamp(180px, 30vh, 250px)',
            }}
          >
            <Typography variant="subtitle1" gutterBottom>
              Select Metric
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
            />
          </Box>
        )}
      </Box>
    </PreventLeafletControl>
  );
};

export default MetricControl; 