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
        display: { xs: 'none', sm: 'flex' }, // Hidden on mobile
        gap: 0.5,
        alignItems: 'center'
      }}
    >
      <Tooltip title="List View">
        <IconButton
          onClick={() => handleViewChange('list')}
          disabled={disabled}
          aria-pressed={currentView === 'list'}
          aria-label="Switch to list view"
          sx={{
            width: 36,
            height: 36,
            backgroundColor: currentView === 'list' ? '#1677ff' : 'transparent',
            color: currentView === 'list' ? 'white' : 'text.primary',
            border: '1px solid',
            borderColor: currentView === 'list' ? '#1677ff' : 'divider',
            borderRadius: 1,
            '&:hover': disabled ? {} : {
              backgroundColor: currentView === 'list' ? '#1565c0' : 'action.hover',
              borderColor: currentView === 'list' ? '#1565c0' : 'primary.main'
            },
            '&:focus-visible': {
              outline: '2px solid #1677ff',
              outlineOffset: 1
            }
          }}
        >
          <ListIcon sx={{ fontSize: '18px' }} />
        </IconButton>
      </Tooltip>

      <Tooltip title="Map View">
        <IconButton
          onClick={() => handleViewChange('map')}
          disabled={disabled}
          aria-pressed={currentView === 'map'}
          aria-label="Switch to map view"
          sx={{
            width: 36,
            height: 36,
            backgroundColor: currentView === 'map' ? '#1677ff' : 'transparent',
            color: currentView === 'map' ? 'white' : 'text.primary',
            border: '1px solid',
            borderColor: currentView === 'map' ? '#1677ff' : 'divider',
            borderRadius: 1,
            '&:hover': disabled ? {} : {
              backgroundColor: currentView === 'map' ? '#1565c0' : 'action.hover',
              borderColor: currentView === 'map' ? '#1565c0' : 'primary.main'
            },
            '&:focus-visible': {
              outline: '2px solid #1677ff',
              outlineOffset: 1
            }
          }}
        >
          <MapIcon sx={{ fontSize: '18px' }} />
        </IconButton>
      </Tooltip>
    </Box>
  );
};

export default ViewModeToggle; 