import React, { useMemo, useState } from 'react';
import { Alert, Button, Snackbar } from '@mui/material';
import ShareIcon from '@mui/icons-material/Share';

import { trackEvent } from '../analytics';

const METRICS = ['XC0', 'XC10', 'XC20', 'XC30', 'XC40', 'XC50', 'XC60', 'XC70', 'XC80', 'XC90', 'XC100'];
const CONFIGURED_PUBLIC_ORIGIN = process.env.REACT_APP_PUBLIC_ORIGIN || 'https://www.parra-glideator.com';

export const buildForecastShareUrl = ({ origin, siteId, selectedDate, selectedMetric }) => {
  const normalizedOrigin = String(origin || CONFIGURED_PUBLIC_ORIGIN).replace(/\/$/, '');
  const params = new URLSearchParams();

  if (selectedDate) params.set('date', selectedDate);
  if (METRICS.includes(selectedMetric)) params.set('metric', selectedMetric);

  const query = params.toString();
  return `${normalizedOrigin}/details/${encodeURIComponent(siteId)}${query ? `?${query}` : ''}`;
};

export const getForecastProbability = ({ predictions, selectedDate, selectedMetric }) => {
  const metricIndex = METRICS.indexOf(selectedMetric);
  if (metricIndex < 0 || !selectedDate || !Array.isArray(predictions)) return null;

  const prediction = predictions.find((item) => item?.date === selectedDate);
  const value = prediction?.values?.[metricIndex];
  return Number.isFinite(value) ? value : null;
};

const formatDate = (date) => {
  if (!date) return 'the selected date';

  const parsed = new Date(`${date}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return date;

  return new Intl.DateTimeFormat('en', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(parsed);
};

const copyText = async (text) => {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', '');
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.select();

  const copied = document.execCommand('copy');
  document.body.removeChild(textarea);
  if (!copied) throw new Error('Copy command failed');
};

const ShareForecastButton = ({
  siteId,
  siteName,
  selectedDate,
  selectedMetric,
  predictions,
}) => {
  const [message, setMessage] = useState(null);
  const [severity, setSeverity] = useState('success');

  const probability = useMemo(() => getForecastProbability({
    predictions,
    selectedDate,
    selectedMetric,
  }), [predictions, selectedDate, selectedMetric]);

  const handleShare = async () => {
    const origin = typeof window !== 'undefined' && window.location?.origin
      ? window.location.origin
      : CONFIGURED_PUBLIC_ORIGIN;
    const url = buildForecastShareUrl({
      origin,
      siteId,
      selectedDate,
      selectedMetric,
    });
    const percentage = probability == null ? null : Math.round(probability * 100);
    const title = `${siteName} forecast – Parra-Glideator`;
    const text = percentage == null
      ? `${siteName}: Glideator forecast for ${selectedMetric} on ${formatDate(selectedDate)}. Decision support, not a safety forecast.`
      : `${siteName}: ${percentage}% Glideator probability for ${selectedMetric} on ${formatDate(selectedDate)}. Decision support, not a safety forecast.`;

    if (navigator.share) {
      try {
        await navigator.share({ title, text, url });
        void trackEvent('forecast_shared', {
          site_id: Number(siteId),
          date: selectedDate,
          metric: selectedMetric,
          probability,
          method: 'native',
        });
        return;
      } catch (error) {
        if (error?.name === 'AbortError') return;
      }
    }

    try {
      await copyText(url);
      setSeverity('success');
      setMessage('Forecast link copied');
      void trackEvent('forecast_shared', {
        site_id: Number(siteId),
        date: selectedDate,
        metric: selectedMetric,
        probability,
        method: 'clipboard',
      });
    } catch {
      setSeverity('error');
      setMessage('Could not copy the forecast link');
    }
  };

  return (
    <>
      <Button
        variant="text"
        size="small"
        startIcon={<ShareIcon fontSize="small" />}
        onClick={handleShare}
        aria-label={`Share forecast for ${siteName}`}
        sx={{
          minWidth: 0,
          px: 1,
          py: 0.5,
          color: 'text.secondary',
          borderRadius: 1.5,
          textTransform: 'none',
          fontWeight: 500,
          '&:hover': {
            bgcolor: 'action.hover',
            color: 'text.primary',
          },
        }}
      >
        Share
      </Button>

      <Snackbar
        open={Boolean(message)}
        autoHideDuration={3500}
        onClose={() => setMessage(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity={severity} onClose={() => setMessage(null)} sx={{ width: '100%' }}>
          {message}
        </Alert>
      </Snackbar>
    </>
  );
};

export default ShareForecastButton;
