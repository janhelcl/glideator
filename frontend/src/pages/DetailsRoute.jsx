import React, { useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Box, Typography } from '@mui/material';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';

import { trackEvent } from '../analytics';
import { fetchSiteInfo, fetchSitePredictions } from '../api';
import AccessibleSiteForecast from '../components/AccessibleSiteForecast';
import AccessibleSitePlanningContext from '../components/AccessibleSitePlanningContext';
import LoadingSpinner from '../components/LoadingSpinner';
import QuickFeedback from '../components/QuickFeedback';
import SiteMetadata from '../components/SiteMetadata';
import Details from './Details';

const isNotFound = (error) => (
  error?.response?.status === 404 || error?.response?.data?.detail === 'Site not found'
);

const DetailsRoute = () => {
  const { siteId } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const previousSelection = useRef(null);
  const numericSiteId = Number(siteId);

  const date = searchParams.get('date') || null;
  const metric = searchParams.get('metric') || 'XC0';
  const tab = searchParams.get('tab') || 'forecast';

  const predictionsQuery = useQuery({
    queryKey: ['site', numericSiteId, 'predictions'],
    queryFn: ({ signal }) => fetchSitePredictions(siteId, { signal }),
    enabled: Number.isFinite(numericSiteId),
  });

  // Site descriptions are optional. A valid forecast site must not become a 404
  // merely because no enriched sites_info row exists yet.
  const siteInfoQuery = useQuery({
    queryKey: ['site', numericSiteId, 'info'],
    queryFn: async ({ signal }) => {
      try {
        return await fetchSiteInfo(siteId, { signal });
      } catch (error) {
        if (error?.response?.status === 404) return null;
        throw error;
      }
    },
    enabled: Number.isFinite(numericSiteId),
  });

  useEffect(() => {
    if (!Number.isFinite(numericSiteId)) {
      navigate('/404', { replace: true });
      return;
    }

    const emptySuccessfulResponse = predictionsQuery.isSuccess
      && (!Array.isArray(predictionsQuery.data) || predictionsQuery.data.length === 0);

    if (emptySuccessfulResponse || isNotFound(predictionsQuery.error)) {
      navigate('/404', { replace: true });
    }
  }, [navigate, numericSiteId, predictionsQuery.data, predictionsQuery.error, predictionsQuery.isSuccess]);

  useEffect(() => {
    trackEvent('site_detail_viewed', {
      site_id: numericSiteId,
      date,
      metric,
      tab,
    });
    // The first view is tracked separately from subsequent selection changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteId]);

  useEffect(() => {
    const current = { date, metric, tab };
    const previous = previousSelection.current;

    if (previous) {
      if (previous.date !== date) {
        trackEvent('site_date_changed', {
          site_id: numericSiteId,
          previous_date: previous.date,
          date,
          metric,
        });
      }
      if (previous.metric !== metric) {
        trackEvent('site_metric_changed', {
          site_id: numericSiteId,
          previous_metric: previous.metric,
          metric,
          date,
        });
      }
      if (previous.tab !== tab) {
        trackEvent('site_tab_changed', {
          site_id: numericSiteId,
          previous_tab: previous.tab,
          tab,
        });
      }
    }

    previousSelection.current = current;
  }, [date, metric, numericSiteId, tab]);

  if (!Number.isFinite(numericSiteId) || isNotFound(predictionsQuery.error)) {
    return null;
  }

  if (predictionsQuery.isPending) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <LoadingSpinner />
      </Box>
    );
  }

  if (predictionsQuery.isError) {
    return (
      <Typography color="error" align="center" sx={{ py: 6 }}>
        Failed to load site data. Please try again.
      </Typography>
    );
  }

  if (!Array.isArray(predictionsQuery.data) || predictionsQuery.data.length === 0) {
    return null;
  }

  const site = predictionsQuery.data[0];
  const displayName = siteInfoQuery.data?.site_name || site.name;

  return (
    <>
      <AccessibleSiteForecast siteId={siteId} selectedDate={date} />
      <AccessibleSitePlanningContext
        siteId={siteId}
        site={site}
        siteName={displayName}
        selectedDate={date}
        selectedMetric={metric}
      />
      <Details />
      <SiteMetadata siteId={siteId} site={site} siteInfo={siteInfoQuery.data} />
      {tab === 'forecast' && date && (
        <Box sx={{ maxWidth: '1200px', mx: 'auto', px: 2, pb: 2 }}>
          <QuickFeedback
            key={`${siteId}-${date}-${metric}`}
            question="Was this forecast useful?"
            context={{
              surface: 'site_forecast',
              site_id: numericSiteId,
              forecast_date: date,
              metric,
            }}
          />
        </Box>
      )}
    </>
  );
};

export default DetailsRoute;
