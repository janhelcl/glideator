import React from 'react';
import { Helmet } from 'react-helmet-async';

const PUBLIC_ORIGIN = process.env.REACT_APP_PUBLIC_ORIGIN || 'https://www.parra-glideator.com';

const SiteMetadata = ({ siteId, site, siteInfo }) => {
  if (!site) return null;

  const displayName = siteInfo?.site_name || site.name || `Site ${siteId}`;
  const canonicalUrl = `${PUBLIC_ORIGIN}/details/${siteId}`;
  const description = `Paragliding activity forecasts, seasonality and site information for ${displayName}.`;
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
      <title>{`${displayName} – Parra-Glideator`}</title>
      <meta name="description" content={description} />
      <link rel="canonical" href={canonicalUrl} />
      <meta property="og:title" content={`${displayName} – Parra-Glideator`} />
      <meta property="og:description" content={description} />
      <meta property="og:type" content="article" />
      <meta property="og:url" content={canonicalUrl} />
      <meta name="twitter:card" content="summary_large_image" />
      <script type="application/ld+json">{JSON.stringify(structuredData)}</script>
    </Helmet>
  );
};

export default SiteMetadata;
