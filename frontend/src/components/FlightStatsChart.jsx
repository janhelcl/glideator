import React, { useEffect, useRef } from 'react';
import { Box, Typography } from '@mui/material';
import StandaloneMetricControl from './StandaloneMetricControl';
import { renderSeasonalityChart } from './seasonalityChart';

const FlightStatsChart = ({ data, metrics, selectedMetric, onMetricChange }) => {
  const svgRef = useRef(null);

  useEffect(() => {
    const svg = svgRef.current;
    if (!svg || !data) return;
    const values = Array.from({ length: 12 }, (_, index) => data[selectedMetric.slice(2)]?.[index] ?? 0);
    const redraw = () => renderSeasonalityChart(svg, values, selectedMetric);
    redraw();
    const observer = new ResizeObserver(redraw);
    observer.observe(svg.parentElement);
    return () => observer.disconnect();
  }, [data, selectedMetric]);

  if (!data) {
    return (
      <Box sx={{ textAlign: 'center', py: 2 }}>
        <Typography variant="body1">No flight statistics available</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ 
      position: 'relative', 
      width: '100%',
      display: 'flex',
      justifyContent: 'center' // Center the chart in the container
    }}>
      {/* Metric control positioned in the top-right corner */}
      <Box sx={{ 
        position: 'absolute', 
        top: '2px', // Move closer to the top
        right: '2px', // Move closer to the right
        zIndex: 10 
      }}>
        <StandaloneMetricControl
          metrics={metrics}
          selectedMetric={selectedMetric}
          onMetricChange={onMetricChange}
        />
      </Box>
      
      <Box 
        sx={{ 
          width: '100%', 
          maxWidth: '750px', // Reduced from 900px to 750px
          height: '350px',
          maxHeight: 'calc(100vh - 400px)',
          position: 'relative'
        }}
      >
        <svg 
          ref={svgRef}
          style={{
            width: '100%',
            height: '100%'
          }}
        />
      </Box>
    </Box>
  );
};

export default FlightStatsChart;
