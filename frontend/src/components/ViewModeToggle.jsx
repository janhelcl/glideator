import React from 'react';
import {
  Box,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  List as ListIcon,
  Map as MapIcon
} from '@mui/icons-material';

/**
 * View Mode Toggle component
 * Provides mutually exclusive List/Map view selection
 * Hidden on mobile screens < 640px
 */
const ViewModeToggle = ({
  currentView = 'list',
  onViewChange,
  disabled = false
}) => {
  const handleViewChange = (newView) => {
    if (disabled || newView === currentView) return;
    onViewChange(newView);
  };

  return (
    <Box 
      sx={{ 
        display: 'flex',
        alignItems: 'center',
        backgroundColor: '#f5f5f5',
        borderRadius: '8px',
        padding: '2px',
        border: '1px solid #e0e0e0'
      }}
    >
      <Tooltip title="List View">
        <IconButton
          onClick={() => handleViewChange('list')}
          disabled={disabled}
          aria-pressed={currentView === 'list'}
          aria-label="Switch to list view"
          sx={{
            width: 32,
            height: 32,
            backgroundColor: currentView === 'list' ? 'white' : 'transparent',
            color: currentView === 'list' ? '#1677ff' : 'text.secondary',
            border: 'none',
            borderRadius: '6px',
            minWidth: 'auto',
            boxShadow: currentView === 'list' ? '0 1px 3px rgba(0,0,0,0.12)' : 'none',
            '&:hover': disabled ? {} : {
              backgroundColor: currentView === 'list' ? 'white' : 'rgba(255,255,255,0.7)',
              color: currentView === 'list' ? '#1677ff' : 'text.primary',
            },
            transition: 'all 0.2s ease-in-out'
          }}
        >
          <ListIcon sx={{ fontSize: '16px' }} />
        </IconButton>
      </Tooltip>

      <Tooltip title="Map View">
        <IconButton
          onClick={() => handleViewChange('map')}
          disabled={disabled}
          aria-pressed={currentView === 'map'}
          aria-label="Switch to map view"
          sx={{
            width: 32,
            height: 32,
            backgroundColor: currentView === 'map' ? 'white' : 'transparent',
            color: currentView === 'map' ? '#1677ff' : 'text.secondary',
            border: 'none',
            borderRadius: '6px',
            minWidth: 'auto',
            boxShadow: currentView === 'map' ? '0 1px 3px rgba(0,0,0,0.12)' : 'none',
            '&:hover': disabled ? {} : {
              backgroundColor: currentView === 'map' ? 'white' : 'rgba(255,255,255,0.7)',
              color: currentView === 'map' ? '#1677ff' : 'text.primary',
            },
            transition: 'all 0.2s ease-in-out'
          }}
        >
          <MapIcon sx={{ fontSize: '16px' }} />
        </IconButton>
      </Tooltip>
    </Box>
  );
};

export default ViewModeToggle; 