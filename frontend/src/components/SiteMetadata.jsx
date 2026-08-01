import React from 'react';
import { Helmet } from 'react-helmet-async';

import {
  formatShareDate,
  getChanceLabel,
  getFlightPhrase,
  getForecastProbability,
  getPluralFlightPhrase,
  normalizeMetric,
} from '../utils/shareUtils';

const CONFIGURED_PUBLIC_ORIGIN = process.env.REACT_APP_PUBLIC_ORIGIN || 'https://www.parra-glideator.com';

const SiteMetadata = ({
  siteId,
  site,
  siteInfo,
  selectedDate = null,
  selectedMetric = 'XC0',
  selectedTab = 'forecast',
}) => {
  if (!site) return null;

  const publicOrigin = typeof window !== 'undefined' && window.location?.origin
    ? window.location.origin
    : CONFIGURED_PUBLIC_ORIGIN;
  const displayName = siteInfo?.site_name || site.name || `Site ${siteId}`;
  const canonicalUrl = `${publicOrigin}/details/${siteId}`;
  const metric = normalizeMetric(selectedMetric);
  const tab = ['forecast', 'season', 'map', 'resources'].includes(selectedTab)
    ? selectedTab
    : 'forecast';
  const probability = getForecastProbability({
    predictions: site.predictions,
    selectedDate,
    selectedMetric: metric,
  });
  const percentage = probability == null ? null : Math.round(probability * 100);
  const formattedDate = selectedDate ? formatShareDate(selectedDate, { includeYear: true }) : null;

  let title = `${displayName} – Parra-Glideator`;
  let description = `Paragliding activity forecasts, seasonality and site information for ${displayName}.`;

  if (tab === 'forecast' && selectedDate) {
    title = percentage == null
      ? `${displayName}: ${getChanceLabel(metric)} – Parra-Glideator`
      : `${displayName}: ${percentage}% chance of ${getFlightPhrase(metric)} – Parra-Glideator`;
    description = percentage == null
      ? `${getChanceLabel(metric)} at ${displayName} on ${formattedDate}.`
      : `Glideator estimates a ${percentage}% chance of ${getFlightPhrase(metric)} at ${displayName} on ${formattedDate}.`;
  } else if (tab === 'season') {
    title = `${displayName} flying season – Parra-Glideator`;
    description = metric === 'XC0'
      ? `See ${displayName}’s typical flying season, based on historical activity.`
      : `See when ${displayName} is typically active for ${getPluralFlightPhrase(metric)}, based on historical activity.`;
  } else if (tab === 'map') {
    title = `${displayName} site map – Parra-Glideator`;
    description = `See takeoffs and landings for ${displayName}.`;
  } else if (tab === 'resources') {
    title = `${displayName} flying resources – Parra-Glideator`;
    description = `Local clubs, weather links, webcams and other flying resources for ${displayName}.`;
  }

  const imageUrl = `${publicOrigin}/logo512.png`;
  const country = siteInfo?.country || site.tags?.find((tag) => typeof tag === 'string') || undefined;
  const structuredData = {
    '@context': 'https://schema.org',
    '@type': 'Place',
    '@id': `${canonicalUrl}#place`,
    name: displayName,
    url: canonicalUrl,
    description,
    geo: {
      '@type': 'GeoCoordinates',
      latitude: site.latitude,
      longitude: site.longitude,
      elevation: site.altitude,
    },
    ...(country ? {
      address: {
        '@type': 'PostalAddress',
        addressCountry: country,
      },
    } : {}),
    additionalProperty: [
      {
        '@type': 'PropertyValue',
        name: 'Parra-Glideator site ID',
        value: Number(siteId),
      },
      {
        '@type': 'PropertyValue',
        name: 'Elevation',
        value: site.altitude,
        unitCode: 'MTR',
      },
    ],
  };

  return (
    <Helmet>
      <title>{title}</title>
      <meta name="description" content={description} />
      <link rel="canonical" href={canonicalUrl} />
      <meta property="og:title" content={title} />
      <meta property="og:description" content={description} />
      <meta property="og:type" content="article" />
      <meta property="og:url" content={canonicalUrl} />
      <meta property="og:image" content={imageUrl} />
      <meta property="og:image:alt" content="Parra-Glideator paragliding forecast" />
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={title} />
      <meta name="twitter:description" content={description} />
      <meta name="twitter:image" content={imageUrl} />
      <script type="application/ld+json">{JSON.stringify(structuredData)}</script>
    </Helmet>
  );
};

export default SiteMetadata;
