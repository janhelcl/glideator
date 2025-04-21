import React, { useRef, useEffect, useState } from 'react';
import { Box, Typography } from '@mui/material';
import MapView from './MapView';
import './DateBoxes.css';

// Memoized small map component to prevent unnecessary re-renders
const SmallMapView = React.memo(({ date, selectedDate, center, zoom, bounds, filteredSites, selectedMetric, metrics }) => {
  return (
    <MapView
      sites={filteredSites}
      selectedMetric={selectedMetric}
      selectedDate={date}
      center={center}
      zoom={zoom + 1}
      bounds={bounds}
      isSmallMap
      lightweight={true}
      metrics={metrics}
    />
  );
});

const DateBoxes = ({
  dates,
  selectedDate,
  setSelectedDate,
  center,
  zoom,
  bounds,
  allSites,
  selectedMetric,
  metrics,
  filteredSitesByDate,
}) => {
  const containerRef = useRef(null);
  const [visibleDates, setVisibleDates] = useState([]);
  
  // Set up intersection observer to detect visible date boxes
  useEffect(() => {
    if (!containerRef.current) return;
    
    const options = {
      root: containerRef.current,
      rootMargin: '0px',
      threshold: 0.1 // 10% visibility is enough to trigger
    };
    
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        const date = entry.target.getAttribute('data-date');
        if (entry.isIntersecting) {
          // Add this date to visible dates if not already there
          setVisibleDates(prev => prev.includes(date) ? prev : [...prev, date]);
        } else {
          // Optional: Remove dates that are no longer visible
          // Uncomment this if you want to unload maps when scrolled away
          // setVisibleDates(prev => prev.filter(d => d !== date));
        }
      });
    }, options);
    
    // Observe all date boxes
    const dateBoxes = containerRef.current.querySelectorAll('.date-box');
    dateBoxes.forEach(box => observer.observe(box));
    
    return () => {
      dateBoxes.forEach(box => observer.unobserve(box));
      observer.disconnect();
    };
  }, [dates]); // Re-run when dates change

  return (
    <Box className="date-boxes-container" ref={containerRef}>
      {dates.map((date) => {
        const isVisible = visibleDates.includes(date) || date === selectedDate;
        
        return (
          <Box
            key={date}
            className={`date-box ${selectedDate === date ? 'selected' : ''}`}
            onClick={() => setSelectedDate(date)}
            data-date={date}
          >
            <Typography variant="subtitle2" sx={{ marginBottom: '4px' }}>
              {date}
            </Typography>
            
            {/* Only render the map if this date box is visible or selected */}
            {isVisible && filteredSitesByDate && filteredSitesByDate[date] && (
              <SmallMapView
                date={date}
                selectedDate={selectedDate}
                center={center}
                zoom={zoom}
                bounds={bounds}
                filteredSites={filteredSitesByDate[date]}
                selectedMetric={selectedMetric}
                metrics={metrics}
              />
            )}
          </Box>
        );
      })}
    </Box>
  );
};

export default DateBoxes;