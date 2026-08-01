import React, { useEffect, useRef } from 'react';
import { Box } from '@mui/material';
import { useParams, useSearchParams } from 'react-router-dom';

import { trackEvent } from '../analytics';
import AccessibleSiteForecast from '../components/AccessibleSiteForecast';
import QuickFeedback from '../components/QuickFeedback';
import Details from './Details';

const DetailsRoute = () => {
  const { siteId } = useParams();
  const [searchParams] = useSearchParams();
  const previousSelection = useRef(null);

  const date = searchParams.get('date') || null;
  const metric = searchParams.get('metric') || 'XC0';
  const tab = searchParams.get('tab') || 'forecast';

  useEffect(() => {
    trackEvent('site_detail_viewed', {
      site_id: Number(siteId),
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
          site_id: Number(siteId),
          previous_date: previous.date,
          date,
          metric,
        });
      }
      if (previous.metric !== metric) {
        trackEvent('site_metric_changed', {
          site_id: Number(siteId),
          previous_metric: previous.metric,
          metric,
          date,
        });
      }
      if (previous.tab !== tab) {
        trackEvent('site_tab_changed', {
          site_id: Number(siteId),
          previous_tab: previous.tab,
          tab,
        });
      }
    }

    previousSelection.current = current;
  }, [date, metric, siteId, tab]);

  return (
    <>
      <AccessibleSiteForecast siteId={siteId} selectedDate={date} />
      <Details />
      {tab === 'forecast' && date && (
        <Box sx={{ maxWidth: '1200px', mx: 'auto', px: 2, pb: 2 }}>
          <QuickFeedback
            key={`${siteId}-${date}-${metric}`}
            question="Was this forecast useful?"
            context={{
              surface: 'site_forecast',
              site_id: Number(siteId),
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
