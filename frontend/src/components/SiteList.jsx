import React from 'react';
import { Box, Typography, Paper, IconButton } from '@mui/material';
import { Launch as LaunchIcon } from '@mui/icons-material';
import Sparkline from './Sparkline';
import { getColorWithAlpha } from '../utils/colorUtils';

const SiteList = ({ sites, onSiteClick, selectedMetric = 'XC0' }) => {
  const handleSiteClick = (site) => {
    // Open site details in new tab with selected metric
    const url = `/details/${site.site_id}?metric=${selectedMetric}`;
    window.open(url, '_blank');
  };

  if (!sites || sites.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="h6" color="text.secondary">
          No sites found for the selected date range
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Try adjusting your date range or check back later
        </Typography>
      </Paper>
    );
  }

  return (
    <Box sx={{ width: '100%' }}>
      <Typography variant="h6" sx={{ mb: 2, fontWeight: 'bold' }}>
        Recommended Sites ({sites.length})
      </Typography>
      
      {sites.map((site, index) => (
        <Paper
          key={site.site_id}
          sx={{
            mb: 1,
            p: 2,
            cursor: 'pointer',
            backgroundColor: getColorWithAlpha(site.average_flyability, 0.15),
            border: '1px solid rgba(0,0,0,0.1)',
            transition: 'all 0.2s ease',
            '&:hover': {
              backgroundColor: getColorWithAlpha(site.average_flyability, 0.25),
              transform: 'translateY(-1px)',
              boxShadow: 2
            }
          }}
          onClick={() => handleSiteClick(site)}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              handleSiteClick(site);
            }
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flex: 1 }}>
              {/* Rank */}
              <Typography
                variant="h6"
                sx={{
                  minWidth: '24px',
                  fontWeight: 'bold',
                  color: 'primary.main'
                }}
              >
                {index + 1}
              </Typography>

              {/* Site Name and Average */}
              <Box sx={{ flex: 1 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                  {site.site_name}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Avg: {Math.round(site.average_flyability * 100)}%
                </Typography>
              </Box>

              {/* Sparkline */}
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Sparkline dailyProbabilities={site.daily_probabilities} />
              </Box>
            </Box>

            {/* Action Buttons */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <IconButton
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  handleSiteClick(site);
                }}
                sx={{ color: 'primary.main' }}
                aria-label={`View details for ${site.site_name}`}
              >
                <LaunchIcon />
              </IconButton>
            </Box>
          </Box>
        </Paper>
      ))}
    </Box>
  );
};

export default SiteList; 