import React from 'react';
import { Box, Skeleton } from '@mui/material';

/**
 * A placeholder component that mimics the appearance of DateBoxes while they're loading
 */
const DateBoxesPlaceholder = () => {
  return (
    <Box
      className="date-boxes-container"
      sx={{
        display: 'flex',
        gap: 'clamp(5px, 1vw, 10px)',
        padding: 'clamp(5px, 1.5vw, 10px)',
        backgroundColor: 'rgba(255, 255, 255, 0.9)',
        borderRadius: '8px',
        overflow: 'hidden',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
      }}
    >
      {/* Generate 3-5 placeholder boxes */}
      {Array.from({ length: 5 }).map((_, index) => (
        <Box
          key={index}
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            width: 'clamp(70px, min(15vw, 15vh), 120px)',
            borderRadius: '4px',
            padding: 'clamp(3px, 0.8vw, 5px)',
            backgroundColor: '#f9f9f9',
          }}
        >
          <Skeleton 
            variant="text" 
            width="70%" 
            height={20}
            sx={{ mb: 1 }}
          />
          <Skeleton 
            variant="rectangular"
            width="100%"
            height={80}
            sx={{ borderRadius: '4px' }}
          />
        </Box>
      ))}
    </Box>
  );
};

export default DateBoxesPlaceholder; 