import React from 'react';
import { Helmet } from 'react-helmet-async';

const CONFIGURED_PUBLIC_ORIGIN = process.env.REACT_APP_PUBLIC_ORIGIN || 'https://www.parra-glideator.com';
const METRICS = ['XC0', 'XC10', 'XC20', 'XC30', 'XC40', 'XC50', 'XC60', 'XC70', 'XC80', 'XC90', 'XC100'];

const formatDate = (date) => {
  if (!date) return null;

  const parsed = new Date(`${date}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return date;

  return new Intl.DateTimeFormat('en', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(parsed);
};

const getProbability = (site, selectedDate, selectedMetric) => {
  const metricIndex = METRICS.indexOf(selectedMetric);
  if (metricIndex < 0 || !selectedDate) return null;

  const prediction = site?.predictions?.find((item) => item?.date === selectedDate);
  const value = prediction?.values?.[metricIndex];
  return Number.isFinite(value) ? value : null;
};

const SiteMetadata = ({
  siteId,
  site,
  siteInfo,
  selectedDate = null,
  selectedMetric = 'XC0',
}) => {
  if (!site) return null;

  const publicOrigin = typeof window !== 'undefined' && window.location?.origin
    ? window.location.origin
    : CONFIGURED_PUBLIC_ORIGIN;
  const displayName = siteInfo?.site_name || site.name || `Site ${siteId}`;
  const canonicalUrl = `${publicOrigin}/details/${siteId}`;
  const validMetric = METRICS.includes(selectedMetric) ? selectedMetric : 'XC0';
  const probability = getProbability(site, selectedDate, validMetric);
  const formattedDate = formatDate(selectedDate);
  const percentage = probability == null ? null : Math.round(probability * 100);
  const title = selectedDate
    ? `${displayName}: ${percentage == null ? validMetric : `${percentage}% for ${validMetric}`} on ${formattedDate} – Parra-Glideator`
    : `${displayName} – Parra-Glideator`;
  const description = selectedDate
    ? percentage == null
      ? `Glideator activity forecast for ${validMetric} at ${displayName} on ${formattedDate}. Decision support, not a safety forecast.`
      : `Glideator estimates a ${percentage}% probability for ${validMetric} activity at ${displayName} on ${formattedDate}. Decision support, not a safety forecast.`
    : `Paragliding activity forecasts, seasonality and site information for ${displayName}.`;
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
