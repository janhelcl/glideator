import React, { useEffect, useRef } from 'react';

import {
  buildDetailsShareUrl,
  getForecastProbability,
} from '../utils/shareUtils';

export const buildForecastShareUrl = ({ origin, siteId, selectedDate, selectedMetric }) => (
  buildDetailsShareUrl({
    origin,
    siteId,
    tab: 'forecast',
    selectedDate,
    selectedMetric,
  })
);

export { getForecastProbability };

// Kept temporarily so the existing Details layout can remove its old slot without
// leaving an empty row. Sharing now lives in the global application bar.
const ShareForecastButton = () => {
  const markerRef = useRef(null);

  useEffect(() => {
    const container = markerRef.current?.parentElement;
    if (!container) return undefined;

    const previousDisplay = container.style.display;
    const previousMinHeight = container.style.minHeight;
    container.style.display = 'none';
    container.style.minHeight = '0';

    return () => {
      container.style.display = previousDisplay;
      container.style.minHeight = previousMinHeight;
    };
  }, []);

  return <span ref={markerRef} hidden aria-hidden="true" />;
};

export default ShareForecastButton;
