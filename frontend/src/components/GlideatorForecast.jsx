import React, { useEffect, useRef } from 'react';
import { Box, useMediaQuery, useTheme } from '@mui/material';
import StandaloneMetricControl from './StandaloneMetricControl';
import OptimizedDateBoxesControl from './OptimizedDateBoxesControl';
import { renderFlightForecastChart, renderFlightQualityChart } from './forecastCharts';

const GlideatorForecast = ({
  siteData,
  selectedDate,
  selectedMetric,
  metrics,
  onMetricChange,
  onDateChange,
  allDates,
  mapState,
  allSites
}) => {
  const barChartRef = useRef(null);
  const lineChartRef = useRef(null);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  useEffect(() => {
    const barChart = barChartRef.current;
    const lineChart = lineChartRef.current;
    const options = {
      predictions: siteData?.predictions ?? [],
      metrics,
      selectedDate,
      selectedMetric,
      isMobile,
    };

    const redraw = () => {
      renderFlightQualityChart(barChart, options);
      renderFlightForecastChart(lineChart, options);
    };

    redraw();
    const observer = new ResizeObserver(redraw);
    observer.observe(barChart.parentElement);
    observer.observe(lineChart.parentElement);
    return () => observer.disconnect();
  }, [siteData, selectedDate, selectedMetric, metrics, isMobile]);

  return (
    <Box sx={{ width: '100%' }}>
      <Box sx={{ 
        display: 'flex', 
        flexDirection: isMobile ? 'column' : 'row',
        gap: 3,
        width: '100%'
      }}>
        {/* Bar Chart with Date Control */}
        <Box 
          sx={{ 
            flex: 1, 
            height: isMobile ? '280px' : '400px',
            position: 'relative',
            minWidth: 0,
            overflow: 'visible',
            marginTop: '30px'
          }}
        >
          {/* Date control positioned above the chart */}
          <Box sx={{ 
            position: 'absolute', 
            top: '-30px',
            right: '10px'
          }}>
            {allDates && allDates.length > 0 && (
              <OptimizedDateBoxesControl
                dates={allDates}
                selectedDate={selectedDate}
                setSelectedDate={onDateChange}
                center={mapState?.center}
                zoom={mapState?.zoom}
                bounds={mapState?.bounds}
                allSites={allSites || [siteData]}
                selectedMetric={selectedMetric}
                metrics={metrics}
              />
            )}
          </Box>
          
          <svg 
            ref={barChartRef}
            style={{ 
              width: '100%', 
              height: '100%',
              overflow: 'visible',
              display: 'block'
            }}
          />
        </Box>

        {/* Line Chart with Metric Control */}
        <Box 
          sx={{ 
            flex: 1,
            height: isMobile ? '280px' : '400px',
            position: 'relative',
            minWidth: 0,
            overflow: 'visible',
            marginTop: '30px'
          }}
        >
          {/* Metric control positioned above the chart */}
          <Box sx={{ 
            position: 'absolute',
            top: '-30px',
            right: '10px'
          }}>
            <StandaloneMetricControl
              metrics={metrics}
              selectedMetric={selectedMetric}
              onMetricChange={onMetricChange}
            />
          </Box>
          
          <svg 
            ref={lineChartRef}
            style={{ 
              width: '100%',
              height: '100%',
              overflow: 'visible',
              display: 'block'
            }}
          />
        </Box>
      </Box>
    </Box>
  );
};

export default GlideatorForecast;
