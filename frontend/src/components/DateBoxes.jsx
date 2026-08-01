import React, { Suspense, useRef, useEffect, useState } from 'react';
import { Box, Typography } from '@mui/material';
import './DateBoxes.css';

const MapView = React.lazy(() => import('./MapView'));

const ClientOnly = ({ children }) => {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return mounted ? children : null;
};

const SmallMapView = React.memo(({ date, center, zoom, bounds, filteredSites, selectedMetric, metrics }) => (
  <MapView
    sites={filteredSites}
    selectedMetric={selectedMetric}
    selectedDate={date}
    center={center}
    zoom={zoom + 1}
    bounds={bounds}
    isSmallMap
    lightweight
    metrics={metrics}
  />
));

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
  void allSites;
  const containerRef = useRef(null);
  const [visibleDates, setVisibleDates] = useState([]);

  useEffect(() => {
    if (!containerRef.current) return undefined;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        const date = entry.target.getAttribute('data-date');
        if (entry.isIntersecting) {
          setVisibleDates((previous) => (
            previous.includes(date) ? previous : [...previous, date]
          ));
        }
      });
    }, {
      root: containerRef.current,
      rootMargin: '0px',
      threshold: 0.1,
    });

    const dateBoxes = containerRef.current.querySelectorAll('.date-box');
    dateBoxes.forEach((box) => observer.observe(box));

    return () => {
      dateBoxes.forEach((box) => observer.unobserve(box));
      observer.disconnect();
    };
  }, [dates]);

  const metricThreshold = selectedMetric.replace('XC', '');
  const metricArticle = /^[8]/.test(metricThreshold) ? 'an' : 'a';
  const metricLabel = selectedMetric === 'XC0'
    ? 'Chances of a flight'
    : `Chances of ${metricArticle} ${metricThreshold}+ point flight`;

  return (
    <Box className="date-strip-wrapper">
      <Typography className="date-strip-label" variant="caption">
        {metricLabel}
      </Typography>
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

              {isVisible && filteredSitesByDate?.[date] && (
                <ClientOnly>
                  <Suspense fallback={null}>
                    <SmallMapView
                      date={date}
                      center={center}
                      zoom={zoom}
                      bounds={bounds}
                      filteredSites={filteredSitesByDate[date]}
                      selectedMetric={selectedMetric}
                      metrics={metrics}
                    />
                  </Suspense>
                </ClientOnly>
              )}
            </Box>
          );
        })}
      </Box>
    </Box>
  );
};

export default DateBoxes;
