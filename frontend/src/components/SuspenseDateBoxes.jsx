import React from 'react';
import DateBoxes from './DateBoxes';

/**
 * A component that reads from a Suspense resource and renders DateBoxes
 * This component will automatically suspend while data is loading
 */
const SuspenseDateBoxes = ({
  sitesResource,
  dates,
  selectedDate,
  setSelectedDate,
  center,
  zoom,
  bounds,
  selectedMetric,
  metrics,
}) => {
  // This read() call will suspend the component if data is still loading
  const allSites = sitesResource.read();
  
  // Precompute filtered sites by date - same logic as in Home.jsx
  const filteredSitesByDate = React.useMemo(() => {
    // Skip computation if we don't have sites or dates yet
    if (!allSites.length || !dates.length) return {};
    
    console.log('Precomputing filtered sites for all dates in SuspenseDateBoxes');
    
    // Create an object to store filtered sites for each date
    const result = {};
    const metricIndexMap = metrics.reduce((acc, metric, index) => {
      acc[metric] = index;
      return acc;
    }, {});
    
    const metricIdx = metricIndexMap[selectedMetric];
    
    // For each date, filter the sites once
    dates.forEach(date => {
      result[date] = allSites.filter(site => {
        // Skip sites without predictions
        if (!site.predictions || !Array.isArray(site.predictions)) {
          return false;
        }
        
        // Find prediction for this date
        const predictionForDate = site.predictions.find(pred => pred.date === date);
        if (!predictionForDate || !Array.isArray(predictionForDate.values)) {
          return false;
        }
        
        // Check if this metric has a value
        const value = predictionForDate.values[metricIdx];
        return value !== undefined && value !== null;
      });
    });
    
    return result;
  }, [allSites, dates, selectedMetric, metrics]);

  return (
    <DateBoxes
      dates={dates}
      selectedDate={selectedDate}
      setSelectedDate={setSelectedDate}
      center={center}
      zoom={zoom}
      bounds={bounds}
      allSites={allSites}
      selectedMetric={selectedMetric}
      metrics={metrics}
      filteredSitesByDate={filteredSitesByDate}
    />
  );
};

export default SuspenseDateBoxes; 