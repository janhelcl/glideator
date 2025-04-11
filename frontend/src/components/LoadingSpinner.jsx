import React from 'react';
import { Box, CircularProgress } from '@mui/material';

const LoadingSpinner = () => {
  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: 1001,
        backgroundColor: 'rgba(255, 255, 255, 0.7)',
      }}
    >
      <CircularProgress
        size={80}
        thickness={4}
        sx={{
          position: 'relative',
          '& .MuiCircularProgress-circle': {
            strokeLinecap: 'round',
          },
        }}
      />
      <Box
        component="img"
        src="/logo512.png"
        alt="Logo"
        sx={{
          position: 'absolute',
          width: '50px',
          height: '50px',
          animation: 'pulse 2s infinite',
          '@keyframes pulse': {
            '0%': {
              transform: 'scale(1)',
              opacity: 1,
            },
            '50%': {
              transform: 'scale(1.1)',
              opacity: 0.8,
            },
            '100%': {
              transform: 'scale(1)',
              opacity: 1,
            },
          },
        }}
      />
    </Box>
  );
};

export default LoadingSpinner; 