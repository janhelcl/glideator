import React, { useState, useRef, useEffect } from 'react';
import { Box, IconButton } from '@mui/material';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import CloseIcon from '@mui/icons-material/Close';
import DateBoxes from './DateBoxes';

const DateBoxesControl = (props) => {
  const [isOpen, setIsOpen] = useState(false);
  const boxesRef = useRef(null);

  useEffect(() => {
    // Handle clicks outside the control
    const handleClickOutside = (event) => {
      if (isOpen && boxesRef.current && !boxesRef.current.contains(event.target)) {
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

  return (
    <>
      {/* Button container */}
      <Box
        sx={{
          position: 'relative',
          zIndex: 1000,
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
          <CalendarMonthIcon fontSize="small" />
        </IconButton>
      </Box>
      
      {/* Overlay and date boxes */}
      {isOpen && (
        <Box
          sx={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            display: 'flex',
            alignItems: 'flex-end',  // Position at bottom
            justifyContent: 'center',
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 1200,
          }}
        >
          <Box
            ref={boxesRef}
            sx={{
              position: 'relative',
              width: '100%',
              backgroundColor: 'white',
              padding: '16px',
              paddingTop: '30px',  // Extra space for close button
              borderTopLeftRadius: '8px',
              borderTopRightRadius: '8px',
              boxShadow: '0 -4px 12px rgba(0,0,0,0.2)',
            }}
          >
            {/* Close button */}
            <IconButton
              size="small"
              onClick={() => setIsOpen(false)}
              sx={{
                position: 'absolute',
                top: '8px',
                right: '8px',
                padding: '4px',
                '&:hover': {
                  backgroundColor: 'rgba(0, 0, 0, 0.08)',
                },
              }}
            >
              <CloseIcon fontSize="small" />
            </IconButton>
            
            {/* DateBoxes component (reused exactly as is) */}
            <DateBoxes {...props} />
          </Box>
        </Box>
      )}
    </>
  );
};

export default DateBoxesControl; 