import React from 'react';
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
import FlightTakeoffIcon from '@mui/icons-material/FlightTakeoff';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import { useNavigate } from 'react-router-dom';
import { useNotifications } from '../context/NotificationContext';

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
      return <FlightTakeoffIcon sx={{ color: 'info.main' }} />;
  }
};

const getProgressColor = (value) => {
  if (value >= 60) return 'success';
  if (value >= 40) return 'info';
  if (value >= 20) return 'warning';
  return 'error';
};

const MissedNotificationsBanner = () => {
  const { missedEvents, dismissMissedEvents } = useNotifications();
  const navigate = useNavigate();

  const isOpen = missedEvents && missedEvents.length > 0;

  const notifications = (missedEvents || []).slice(0, 8).map((event) => {
    const payload = event.payload || {};
    return {
      id: event.event_id,
      siteId: payload.site_id,
      siteName: payload.site_name || 'Unknown site',
      metric: payload.metric || 'XC0',
      value: payload.value != null ? Math.round(payload.value) : 0,
      date: payload.prediction_date,
      eventType: payload.event_type,
      triggeredAt: event.triggered_at,
    };
  });

  const handleNotificationClick = (notification) => {
    const params = new URLSearchParams();
    if (notification.date) params.set('date', notification.date);
    if (notification.metric) params.set('metric', notification.metric);

    dismissMissedEvents();
    navigate(`/details/${notification.siteId}?${params.toString()}`);
  };

  return (
    <SwipeableDrawer
      anchor="bottom"
      open={isOpen}
      onClose={dismissMissedEvents}
      onOpen={() => {}}
      disableSwipeToOpen
      PaperProps={{
        sx: {
          borderTopLeftRadius: 16,
          borderTopRightRadius: 16,
          maxHeight: '70vh',
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
        </Box>
        <IconButton onClick={dismissMissedEvents} size="small">
          <CloseIcon />
        </IconButton>
      </Box>

      <Typography variant="body2" color="text.secondary" sx={{ px: 2, pb: 2 }}>
        {notifications.length === 1
          ? '1 notification'
          : `${missedEvents.length} notifications`}
        {missedEvents.length > 8 && ` (showing 8)`}
      </Typography>

      {/* Notification cards */}
      <Stack spacing={1.5} sx={{ px: 2, pb: 3, overflow: 'auto' }}>
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
              sx={{ p: 2 }}
            >
              <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5 }}>
                {/* Icon */}
                <Box sx={{ pt: 0.5 }}>
                  {getEventIcon(item.eventType)}
                </Box>

                {/* Content */}
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', mb: 0.5 }}>
                    <Typography variant="subtitle1" fontWeight="medium" noWrap>
                      {item.siteName}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ ml: 1, flexShrink: 0 }}>
                      {formatTimeAgo(item.triggeredAt)}
                    </Typography>
                  </Box>

                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      {item.metric}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      •
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {formatPredictionDate(item.date)}
                    </Typography>
                  </Box>

                  {/* Progress bar */}
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <LinearProgress
                      variant="determinate"
                      value={item.value}
                      color={getProgressColor(item.value)}
                      sx={{
                        flex: 1,
                        height: 8,
                        borderRadius: 4,
                        backgroundColor: 'grey.200',
                      }}
                    />
                    <Typography
                      variant="body2"
                      fontWeight="bold"
                      sx={{
                        minWidth: 40,
                        textAlign: 'right',
                        color: `${getProgressColor(item.value)}.main`,
                      }}
                    >
                      {item.value}%
                    </Typography>
                  </Box>
                </Box>
              </Box>
            </CardActionArea>
          </Card>
        ))}
      </Stack>
    </SwipeableDrawer>
  );
};

export default MissedNotificationsBanner;
