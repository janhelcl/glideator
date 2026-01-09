import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardActionArea,
  IconButton,
  LinearProgress,
  SwipeableDrawer,
  Stack,
  Typography,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import FlagIcon from '@mui/icons-material/Flag';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useNotifications } from '../context/NotificationContext';

// Mock data for testing UI with ?testMissed=true
const MOCK_MISSED_EVENTS = [
  {
    event_id: 'test-1',
    triggered_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2h ago
    payload: {
      site_id: 1,
      site_name: 'Monte Grappa',
      metric: 'XC0',
      value: 67,
      previous_value: 45,
      prediction_date: new Date().toISOString().split('T')[0],
      event_type: 'improved',
    },
  },
  {
    event_id: 'test-2',
    triggered_at: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(), // 5h ago
    payload: {
      site_id: 2,
      site_name: 'Col Rodella',
      metric: 'XC10',
      value: 32,
      previous_value: 55,
      prediction_date: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      event_type: 'deteriorated',
    },
  },
  {
    event_id: 'test-3',
    triggered_at: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(), // 8h ago
    payload: {
      site_id: 3,
      site_name: 'Bassano del Grappa',
      metric: 'XC30',
      value: 78,
      previous_value: null,
      prediction_date: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      event_type: 'initial',
    },
  },
  {
    event_id: 'test-4',
    triggered_at: new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString(), // 12h ago
    payload: {
      site_id: 4,
      site_name: 'Kössen',
      metric: 'XC0',
      value: 52,
      previous_value: 38,
      prediction_date: new Date().toISOString().split('T')[0],
      event_type: 'improved',
    },
  },
];

const formatTimeAgo = (isoString) => {
  if (!isoString) return '';
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

  if (diffMins < 60) {
    return `${diffMins}m ago`;
  }
  if (diffHours < 24) {
    return `${diffHours}h ago`;
  }
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
};

const formatPredictionDate = (dateString) => {
  if (!dateString) return '';
  const date = new Date(dateString + 'T00:00:00');
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);

  if (date.getTime() === today.getTime()) return 'Today';
  if (date.getTime() === tomorrow.getTime()) return 'Tomorrow';

  return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
};

const getEventIcon = (eventType) => {
  switch (eventType) {
    case 'improved':
      return <TrendingUpIcon sx={{ color: 'success.main' }} />;
    case 'deteriorated':
      return <TrendingDownIcon sx={{ color: 'warning.main' }} />;
    default:
      // Initial alert - threshold reached for the first time
      return <FlagIcon sx={{ color: 'info.main' }} />;
  }
};

const getProgressColor = (value) => {
  if (value >= 60) return 'success';
  if (value >= 40) return 'info';
  if (value >= 20) return 'warning';
  return 'error';
};

const MAX_VISIBLE_NOTIFICATIONS = 8;
const DRAWER_MAX_WIDTH = 480;

const MissedNotificationsBanner = () => {
  const { missedEvents, dismissMissedEvents } = useNotifications();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Test mode: ?testMissed=true shows mock data
  const testMode = searchParams.get('testMissed') === 'true';
  const [testDismissed, setTestDismissed] = useState(false);
  
  // Reset test dismissed state when testMode changes
  useEffect(() => {
    if (testMode) setTestDismissed(false);
  }, [testMode]);

  const effectiveEvents = testMode && !testDismissed ? MOCK_MISSED_EVENTS : missedEvents;
  const isOpen = effectiveEvents && effectiveEvents.length > 0;

  const handleDismiss = () => {
    if (testMode) {
      setTestDismissed(true);
      // Remove the test param from URL
      searchParams.delete('testMissed');
      setSearchParams(searchParams, { replace: true });
    } else {
      dismissMissedEvents();
    }
  };

  const notifications = (effectiveEvents || []).slice(0, MAX_VISIBLE_NOTIFICATIONS).map((event) => {
    const payload = event.payload || {};
    return {
      id: event.event_id,
      siteId: payload.site_id,
      siteName: payload.site_name || 'Unknown site',
      metric: payload.metric || 'XC0',
      value: payload.value != null ? Math.round(payload.value) : 0,
      previousValue: payload.previous_value != null ? Math.round(payload.previous_value) : null,
      date: payload.prediction_date,
      eventType: payload.event_type,
      triggeredAt: event.triggered_at,
    };
  });

  const handleNotificationClick = (notification) => {
    const params = new URLSearchParams();
    if (notification.date) params.set('date', notification.date);
    if (notification.metric) params.set('metric', notification.metric);

    handleDismiss();
    navigate(`/details/${notification.siteId}?${params.toString()}`);
  };

  const handleViewAll = () => {
    handleDismiss();
    navigate('/notifications');
  };

  return (
    <SwipeableDrawer
      anchor="bottom"
      open={isOpen}
      onClose={handleDismiss}
      onOpen={() => {}}
      disableSwipeToOpen
      PaperProps={{
        sx: {
          // Center and constrain width on desktop
          maxWidth: DRAWER_MAX_WIDTH,
          mx: 'auto',
          left: 0,
          right: 0,
          borderTopLeftRadius: 16,
          borderTopRightRadius: 16,
          maxHeight: '70vh',
          // Safe area for mobile devices with gesture bars
          pb: 'env(safe-area-inset-bottom)',
        },
      }}
    >
      {/* Drag handle */}
      <Box
        sx={{
          width: 40,
          height: 4,
          backgroundColor: 'grey.400',
          borderRadius: 2,
          mx: 'auto',
          mt: 1.5,
          mb: 1,
        }}
      />

      {/* Header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          px: 2,
          pb: 1,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <NotificationsActiveIcon color="primary" />
          <Typography variant="h6" fontWeight="medium">
            While you were away...
          </Typography>
          {testMode && (
            <Typography variant="caption" sx={{ bgcolor: 'warning.light', px: 1, py: 0.25, borderRadius: 1 }}>
              TEST MODE
            </Typography>
          )}
        </Box>
        <IconButton onClick={handleDismiss} size="small">
          <CloseIcon />
        </IconButton>
      </Box>

      <Typography variant="body2" color="text.secondary" sx={{ px: 2, pb: 1.5 }}>
        {notifications.length === 1
          ? '1 notification'
          : `${effectiveEvents.length} notification${effectiveEvents.length > 1 ? 's' : ''}`}
        {effectiveEvents.length > MAX_VISIBLE_NOTIFICATIONS && ` (showing ${MAX_VISIBLE_NOTIFICATIONS})`}
      </Typography>

      {/* Notification cards */}
      <Stack spacing={1.5} sx={{ px: 2, pb: 2, overflow: 'auto' }}>
        {notifications.map((item) => (
          <Card
            key={item.id}
            variant="outlined"
            sx={{
              borderRadius: 2,
              transition: 'transform 0.15s, box-shadow 0.15s',
              '&:hover': {
                transform: 'translateY(-2px)',
                boxShadow: 2,
              },
            }}
          >
            <CardActionArea
              onClick={() => handleNotificationClick(item)}
              sx={{ p: 1.5 }}
            >
              <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5 }}>
                {/* Icon */}
                <Box sx={{ pt: 0.25 }}>
                  {getEventIcon(item.eventType)}
                </Box>

                {/* Content */}
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  {/* Site name + time */}
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', mb: 0.25 }}>
                    <Typography variant="subtitle2" fontWeight="bold" noWrap>
                      {item.siteName}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ ml: 1, flexShrink: 0 }}>
                      {formatTimeAgo(item.triggeredAt)}
                    </Typography>
                  </Box>

                  {/* Metric + Date row */}
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75, mb: 0.75 }}>
                    <Typography variant="caption" color="text.secondary">
                      {item.metric}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">•</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {formatPredictionDate(item.date)}
                    </Typography>
                  </Box>

                  {/* Progress bar */}
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <LinearProgress
                      variant="determinate"
                      value={item.value}
                      color={getProgressColor(item.value)}
                      sx={{
                        flex: 1,
                        height: 6,
                        borderRadius: 3,
                        backgroundColor: 'grey.200',
                      }}
                    />
                    <Typography
                      variant="caption"
                      fontWeight="bold"
                      sx={{
                        minWidth: 32,
                        textAlign: 'right',
                        color: `${getProgressColor(item.value)}.main`,
                      }}
                    >
                      {item.value}%
                    </Typography>
                  </Box>

                  {/* Value change indicator */}
                  {item.previousValue != null && (
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                      {item.previousValue}% → {item.value}%
                    </Typography>
                  )}
                </Box>
              </Box>
            </CardActionArea>
          </Card>
        ))}
      </Stack>

      {/* View all button when there are more notifications */}
      {effectiveEvents.length > MAX_VISIBLE_NOTIFICATIONS && (
        <Box sx={{ px: 2, pb: 2 }}>
          <Card
            variant="outlined"
            sx={{
              borderRadius: 2,
              backgroundColor: 'action.hover',
            }}
          >
            <CardActionArea onClick={handleViewAll} sx={{ py: 1.5 }}>
              <Typography variant="body2" color="primary" align="center" fontWeight="medium">
                View all {effectiveEvents.length} notifications
              </Typography>
            </CardActionArea>
          </Card>
        </Box>
      )}
    </SwipeableDrawer>
  );
};

export default MissedNotificationsBanner;
