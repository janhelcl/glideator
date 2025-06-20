import React from 'react';
import { Fab } from '@mui/material';
import { Map as MapIcon, ExpandLess, ExpandMore } from '@mui/icons-material';

const MapToggle = ({ isMapVisible, onToggle, isMobile }) => {
  if (!isMobile) {
    return null; // Don't show toggle on desktop
  }

  return (
    <Fab
      color="primary"
      size="medium"
      onClick={onToggle}
      sx={{
        position: 'fixed',
        bottom: 80,
        right: 16,
        zIndex: 1000,
        boxShadow: 3,
        '&:hover': {
          boxShadow: 6,
        }
      }}
      aria-label={isMapVisible ? 'Hide map' : 'Show map'}
    >
      {isMapVisible ? <ExpandMore /> : <MapIcon />}
    </Fab>
  );
};

export default MapToggle; 