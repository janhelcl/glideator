import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Box } from '@mui/material';

import {
  fetchFlightStats,
  fetchSimilarDays,
  fetchSiteForecast,
  fetchSiteResources,
  fetchSiteSpots,
} from '../api';

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

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

const formatNumber = (value, digits = 1) => (
  Number.isFinite(value) ? Number(value).toFixed(digits) : 'Not available'
);

const formatPercentage = (value) => (
  Number.isFinite(value) ? `${Math.round(Number(value) * 100)}%` : 'Not available'
);

const resourceLinks = (resources) => {
  const candidates = [
    ...(resources?.local_resources || []).map((resource) => ({
      url: resource.url,
      label: resource.name || resource.host || resource.url,
      type: 'Local resource',
    })),
    ...(resources?.webcam_urls || []).map((url) => ({ url, label: url, type: 'Webcam' })),
    ...(resources?.meteostation_urls || []).map((url) => ({ url, label: url, type: 'Meteostation' })),
  ];

  const seen = new Set();
  return candidates.filter(({ url }) => {
    if (!url || seen.has(url)) return false;
    seen.add(url);
    return true;
  });
};

const AccessibleSitePlanningContext = ({
  siteId,
  site,
  siteName,
  selectedDate,
  selectedMetric = 'XC0',
}) => {
  const numericSiteId = Number(siteId);

  // These disabled queries read SSR-prefetched cache data without restoring the
  // eager browser requests that the interactive tabs intentionally avoid.
  const flightStatsQuery = useQuery({
    queryKey: ['site', numericSiteId, 'flight-stats'],
    queryFn: () => fetchFlightStats(siteId),
    enabled: false,
  });
  const spotsQuery = useQuery({
    queryKey: ['site', numericSiteId, 'spots'],
    queryFn: () => fetchSiteSpots(siteId),
    enabled: false,
  });
  const resourcesQuery = useQuery({
    queryKey: ['site', numericSiteId, 'resources'],
    queryFn: () => fetchSiteResources(siteId),
    enabled: false,
  });
  const forecastQuery = useQuery({
    queryKey: ['site', numericSiteId, 'forecast', selectedDate],
    queryFn: () => fetchSiteForecast(siteId, selectedDate),
    enabled: false,
  });
  const similarDaysQuery = useQuery({
    queryKey: ['site', numericSiteId, 'similar-days', selectedDate],
    queryFn: () => fetchSimilarDays(siteId, selectedDate, 3),
    enabled: false,
  });

  const threshold = Number(selectedMetric.replace('XC', '')) || 0;
  const monthlyValues = flightStatsQuery.data?.[threshold]
    || flightStatsQuery.data?.[String(threshold)]
    || [];
  const spots = spotsQuery.data || [];
  const takeoffs = spots.filter((spot) => spot.type?.toLowerCase() === 'takeoff');
  const landings = spots.filter((spot) => spot.type?.toLowerCase() === 'landing');
  const links = resourceLinks(resourcesQuery.data);
  const forecast = forecastQuery.data;
  const similarDays = similarDaysQuery.data?.similar_days || [];
  const displayName = siteName || site?.name || `Site ${siteId}`;

  const hasContent = monthlyValues.length || spots.length || links.length || forecast || similarDays.length;
  if (!hasContent) return null;

  const xcontestLink = (pastDate) => (
    `https://www.xcontest.org/world/cs/vyhledavani-preletu/` +
    `?list[sort]=pts&filter[point]=${site.longitude}+${site.latitude}` +
    `&filter[radius]=5000&filter[date]=${pastDate}`
  );

  return (
    <Box
      component="section"
      sx={SCREEN_READER_ONLY}
      aria-label={`${displayName} planning context`}
    >
      <h2>{displayName} planning context</h2>
      <p>
        The following tables and links are semantic alternatives to the interactive season chart,
        site map, resource tabs, atmospheric profile and similar-days panels.
      </p>

      {monthlyValues.length > 0 && (
        <section aria-labelledby={`seasonality-${siteId}`}>
          <h3 id={`seasonality-${siteId}`}>{selectedMetric} monthly seasonality</h3>
          <table aria-label={`${displayName} monthly ${selectedMetric} seasonality`}>
            <caption>
              Average number of days per month with recorded flights exceeding the {selectedMetric} threshold
            </caption>
            <thead>
              <tr>
                <th scope="col">Month</th>
                <th scope="col">Average qualifying days</th>
              </tr>
            </thead>
            <tbody>
              {monthlyValues.map((value, index) => (
                <tr key={MONTHS[index] || index}>
                  <th scope="row">{MONTHS[index] || `Month ${index + 1}`}</th>
                  <td>{formatNumber(value)} days</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {spots.length > 0 && (
        <section aria-labelledby={`spots-${siteId}`}>
          <h3 id={`spots-${siteId}`}>{displayName} takeoff and landing spots</h3>
          {takeoffs.length > 0 && (
            <>
              <h4>Takeoffs</h4>
              <ul>
                {takeoffs.map((spot) => (
                  <li key={spot.spot_id}>
                    {spot.name}: {spot.latitude}, {spot.longitude}; altitude {spot.altitude} m
                    {spot.wind_direction ? `; suitable wind ${spot.wind_direction}` : ''}.
                  </li>
                ))}
              </ul>
            </>
          )}
          {landings.length > 0 && (
            <>
              <h4>Landings</h4>
              <ul>
                {landings.map((spot) => (
                  <li key={spot.spot_id}>
                    {spot.name}: {spot.latitude}, {spot.longitude}; altitude {spot.altitude} m.
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      )}

      {links.length > 0 && (
        <section aria-labelledby={`resources-${siteId}`}>
          <h3 id={`resources-${siteId}`}>Validated local resources</h3>
          <ul>
            {links.map((resource) => (
              <li key={resource.url}>
                {resource.type}: <a href={resource.url}>{resource.label}</a>
              </li>
            ))}
          </ul>
          {resourcesQuery.data?.run_extracted_at && (
            <p>Resource extraction updated: {resourcesQuery.data.run_extracted_at}.</p>
          )}
        </section>
      )}

      {forecast && selectedDate && (
        <section aria-labelledby={`weather-${siteId}-${selectedDate}`}>
          <h3 id={`weather-${siteId}-${selectedDate}`}>
            Selected-day weather drivers for {selectedDate}
          </h3>
          <p>
            Forecast computed {forecast.computed_at || 'at an unspecified time'} from GFS cycle{' '}
            {forecast.gfs_forecast_at || 'not provided'}.
          </p>
          <table aria-label={`${displayName} weather drivers for ${selectedDate}`}>
            <caption>Surface forecast values behind the atmospheric profile</caption>
            <thead>
              <tr>
                <th scope="col">Time</th>
                <th scope="col">Temperature</th>
                <th scope="col">Dew point</th>
                <th scope="col">10 m wind</th>
                <th scope="col">Gust</th>
                <th scope="col">Pressure</th>
              </tr>
            </thead>
            <tbody>
              {[9, 12, 15].map((hour) => {
                const values = forecast[`forecast_${hour}`] || {};
                return (
                  <tr key={hour}>
                    <th scope="row">{hour}:00</th>
                    <td>{formatNumber(values.temperature_2m_c)} °C</td>
                    <td>{formatNumber(values.dewpoint_2m_c)} °C</td>
                    <td>
                      {formatNumber(values.wind_speed_10m_ms)} m/s at{' '}
                      {formatNumber(values.wind_direction_10m_dgr, 0)}°
                    </td>
                    <td>{formatNumber(values.wind_gust_sfc_ms)} m/s</td>
                    <td>
                      {Number.isFinite(values.pressure_sfc_pa)
                        ? `${Math.round(values.pressure_sfc_pa / 100)} hPa`
                        : 'Not available'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      )}

      {similarDays.length > 0 && site && selectedDate && (
        <section aria-labelledby={`similar-${siteId}-${selectedDate}`}>
          <h3 id={`similar-${siteId}-${selectedDate}`}>Similar historical weather days</h3>
          <ul>
            {similarDays.map((day) => (
              <li key={day.past_date}>
                {day.past_date}, similarity {formatPercentage(day.similarity)}.{' '}
                <a href={xcontestLink(day.past_date)}>View flights near {displayName} on XContest</a>
              </li>
            ))}
          </ul>
        </section>
      )}

      <p>
        This information supports planning and historical comparison. It is not a safety guarantee;
        verify current conditions, airspace and local rules before flying.
      </p>
    </Box>
  );
};

export default AccessibleSitePlanningContext;
