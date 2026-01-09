import React from 'react';
import { Alert, AlertTitle, Button, Collapse, Stack, Typography } from '@mui/material';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import { useNotifications } from '../context/NotificationContext';

const formatEventDate = (isoString) => {
  if (!isoString) return '';
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now - date;
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

  if (diffHours < 1) {
    const diffMins = Math.floor(diffMs / (1000 * 60));
    return `${diffMins}m ago`;
  }
  if (diffHours < 24) {
    return `${diffHours}h ago`;
  }
  return date.toLocaleDateString();
};

const MissedNotificationsBanner = () => {
  const { missedEvents, dismissMissedEvents } = useNotifications();

  if (!missedEvents || missedEvents.length === 0) {
    return null;
  }

  // Group events by site for a cleaner summary
  const summary = missedEvents.slice(0, 5).map((event) => {
    const payload = event.payload || {};
    return {
      id: event.event_id,
      siteName: payload.site_name || 'Unknown site',
      metric: payload.metric || '',
      value: payload.value != null ? Math.round(payload.value) : null,
      date: payload.prediction_date,
      eventType: payload.event_type,
      triggeredAt: event.triggered_at,
    };
  });

  return (
    <Collapse in={missedEvents.length > 0}>
      <Alert
        severity="info"
        icon={<NotificationsActiveIcon />}
        sx={{ mb: 2 }}
        action={
          <Button color="inherit" size="small" onClick={dismissMissedEvents}>
            Dismiss
          </Button>
        }
      >
        <AlertTitle>
          {missedEvents.length === 1
            ? 'You have 1 missed notification'
            : `You have ${missedEvents.length} missed notifications`}
        </AlertTitle>
        <Stack spacing={0.5}>
          {summary.map((item) => (
            <Typography key={item.id} variant="body2">
              <strong>{item.siteName}</strong>
              {item.value != null && ` - ${item.metric} ${item.value}%`}
              {item.date && ` for ${item.date}`}
              <Typography component="span" variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                ({formatEventDate(item.triggeredAt)})
              </Typography>
            </Typography>
          ))}
          {missedEvents.length > 5 && (
            <Typography variant="body2" color="text.secondary">
              ...and {missedEvents.length - 5} more
            </Typography>
          )}
        </Stack>
      </Alert>
    </Collapse>
  );
};

export default MissedNotificationsBanner;
