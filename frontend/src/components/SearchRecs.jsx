import React from 'react';
import { Box, Chip, Link, useTheme } from '@mui/material';

const SearchRecs = ({ siteName, country }) => {
  const theme = useTheme();

  if (!siteName) {
    return null; // Don't render if siteName is not available
  }

  const generateSearchUrl = (query) => {
    return `https://www.google.com/search?q=${encodeURIComponent(query)}`;
  };

  const searchQueries = [
    `paragliding ${siteName}${country ? ` (${country})` : ''}`,
    `${siteName} paragliding official information`,
    `${siteName} paragliding guide`,
  ];

  return (
    <Box 
      sx={{ 
        bgcolor: theme.palette.mode === 'dark' ? '#1f1f1f' : '#fafafa',
        borderRadius: '8px',
        p: '12px',
        boxShadow: theme.palette.mode === 'dark' ? '0 0 0 1px #ffffff26' : '0 0 0 1px #0000000f',
        width: '100%',
        boxSizing: 'border-box',
        mt: 2 
      }}
    >
      {/* Chips container - updated for responsiveness */}
      <Box 
        sx={{
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'center',
          gap: 1,
          overflow: 'visible',
          
          [theme.breakpoints.down('sm')]: {
            flexDirection: 'column',
            alignItems: 'center',
            flexWrap: 'nowrap',
          }
        }}
      >
        {searchQueries.map((query, index) => (
          <Link 
            href={generateSearchUrl(query)} 
            key={index}
            target="_blank" 
            rel="noopener noreferrer" 
            underline="none"
          >
            <Chip 
              label={query}
              clickable
              sx={{
                cursor: 'pointer',
                color: theme.palette.mode === 'dark' ? '#fff' : '#5e5e5e',
                borderColor: theme.palette.mode === 'dark' ? '#3c4043' : '#d2d2d2',
                bgcolor: theme.palette.mode === 'dark' ? '#2c2c2c' : '#ffffff',
                '&:hover': {
                  bgcolor: theme.palette.mode === 'dark' ? '#353536' : '#f2f2f2',
                },
                height: 'auto', 
                padding: '5px 16px',
                fontSize: '14px',
                borderRadius: '16px',
                [theme.breakpoints.down('sm')]: {
                  width: 'fit-content',
                  maxWidth: '100%'
                }
              }}
            />
          </Link>
        ))}
      </Box>
    </Box>
  );
};

export default SearchRecs; 