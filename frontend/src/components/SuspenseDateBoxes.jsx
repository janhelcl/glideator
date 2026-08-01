import React from 'react';
import DateBoxes from './DateBoxes';

/**
 * Precomputes the date-specific site collections used by DateBoxes.
 * Data is supplied by the route query so the same component works for SSR and hydration.
 */
const SuspenseDateBoxes = ({
  allSites = [],
  dates,
  selectedDate,
  setSelectedDate,
  center,
  zoom,
  bounds,
  selectedMetric,
  metrics,
}) => {
  const filteredSitesByDate = React.useMemo(() => {
    if (!allSites.length || !dates.length) return {};

    const result = {};
    const metricIndexMap = metrics.reduce((acc, metric, index) => {
      acc[metric] = index;
      return acc;
    }, {});

    const metricIdx = metricIndexMap[selectedMetric];

    dates.forEach((date) => {
      result[date] = allSites.filter((site) => {
        const predictionForDate = site.predictions?.find((prediction) => prediction.date === date);
        const value = predictionForDate?.values?.[metricIdx];
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
