import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Box } from '@mui/material';
import { fetchSiteInfo, fetchSitePredictions } from '../api';

const METRICS = ['XC0', 'XC10', 'XC20', 'XC30', 'XC40', 'XC50', 'XC60', 'XC70', 'XC80', 'XC90', 'XC100'];

const SCREEN_READER_ONLY = {
  position: 'absolute',
  width: '1px',
  height: '1px',
  padding: 0,
  margin: '-1px',
  overflow: 'hidden',
  clip: 'rect(0, 0, 0, 0)',
  whiteSpace: 'nowrap',
  border: 0,
};

const formatTimestamp = (value) => value || 'Not provided';

const AccessibleSiteForecast = ({ siteId, selectedDate = null }) => {
  const numericSiteId = Number(siteId);

  const predictionsQuery = useQuery({
    queryKey: ['site', numericSiteId, 'predictions'],
    queryFn: ({ signal }) => fetchSitePredictions(siteId, { signal }),
    enabled: Number.isFinite(numericSiteId),
  });

  const siteInfoQuery = useQuery({
    queryKey: ['site', numericSiteId, 'info'],
    queryFn: ({ signal }) => fetchSiteInfo(siteId, { signal }),
    enabled: Number.isFinite(numericSiteId),
  });

  const site = predictionsQuery.data?.[0];
  if (!site) return null;

  const displayName = siteInfoQuery.data?.site_name || site.name || `Site ${siteId}`;
  const country = siteInfoQuery.data?.country || 'Not provided';

  return (
    <Box component="section" sx={SCREEN_READER_ONLY} aria-label={`${displayName} forecast data`}>
      <h2>{displayName} seven-day paragliding activity forecast</h2>
      <p>
        Country: {country}. Coordinates: {site.latitude}, {site.longitude}. Altitude: {site.altitude} metres.
      </p>
      {site.tags?.length > 0 && <p>Site tags: {site.tags.join(', ')}.</p>}
      <p>
        XC0 is the probability of any recorded flying activity. XC10 through XC100 are probabilities of
        exceeding progressively higher XC-point thresholds. Higher values indicate more promising historical
        flight patterns, not guaranteed safe flying conditions. Always verify current weather and local rules.
      </p>
      <table aria-label={`${displayName} seven-day forecast probabilities`}>
        <caption>
          Parra-Glideator forecast probabilities{selectedDate ? `; selected date ${selectedDate}` : ''}
        </caption>
        <thead>
          <tr>
            <th scope="col">Date</th>
            {METRICS.map((metric) => <th scope="col" key={metric}>{metric}</th>)}
            <th scope="col">Forecast computed</th>
            <th scope="col">GFS forecast cycle</th>
          </tr>
        </thead>
        <tbody>
          {(site.predictions || []).map((prediction) => (
            <tr key={prediction.date}>
              <th scope="row">{prediction.date}</th>
              {METRICS.map((metric, index) => {
                const value = prediction.values?.[index];
                return (
                  <td key={metric}>
                    {value == null ? 'Not available' : `${Math.round(value * 100)}%`}
                  </td>
                );
              })}
              <td>{formatTimestamp(prediction.computed_at)}</td>
              <td>{formatTimestamp(prediction.gfs_forecast_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Box>
  );
};

export default AccessibleSiteForecast;
