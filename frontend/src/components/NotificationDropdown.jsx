import React, { useState, useMemo } from 'react';
import {
  Badge,
  Box,
  Button,
  Card,
  CardActionArea,
  Divider,
  IconButton,
  LinearProgress,
  Popover,
  Tab,
  Tabs,
  Tooltip,
  Typography,
} from '@mui/material';
import FlagIcon from '@mui/icons-material/Flag';
import NotificationsIcon from '@mui/icons-material/Notifications';
import SettingsIcon from '@mui/icons-material/Settings';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import { Link as RouterLink, useNavigate, useSearchParams } from 'react-router-dom';
import { useNotifications } from '../context/NotificationContext';

// Mock data for testing UI with ?testMissed=true
const MOCK_MISSED_EVENTS = [
  {
    event_id: 'test-1',
    triggered_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
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
    triggered_at: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(),
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
    triggered_at: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(),
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
    triggered_at: new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString(),
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

  if (diffMins < 60) return `${diffMins}m`;
  if (diffHours < 24) return `${diffHours}h`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d`;
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
      return <TrendingUpIcon fontSize="small" sx={{ color: 'success.main' }} />;
    case 'deteriorated':
      return <TrendingDownIcon fontSize="small" sx={{ color: 'warning.main' }} />;
    default:
      return <FlagIcon fontSize="small" sx={{ color: 'info.main' }} />;
  }
};

const getProgressColor = (value) => {
  if (value >= 60) return 'success';
  if (value >= 40) return 'info';
  if (value >= 20) return 'warning';
  return 'error';
};

const MAX_VISIBLE_NOTIFICATIONS = 5;

const NotificationDropdown = ({ iconColor = 'inherit' }) => {
  const {
    missedEvents,
    unreadEvents,
    unreadCount,
    markEventAsRead,
    markAllEventsAsRead,
  } = useNotifications();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [anchorEl, setAnchorEl] = useState(null);
  const [activeTab, setActiveTab] = useState('unread');

  // Test mode state for tracking read status locally
  const [testReadIds, setTestReadIds] = useState(new Set());

  // Test mode: ?testMissed=true shows mock data
  const testMode = searchParams.get('testMissed') === 'true';
  const allEvents = testMode ? MOCK_MISSED_EVENTS : (missedEvents || []);
  const unreadEventIds = useMemo(() => {
    if (testMode) {
      return new Set(allEvents.filter(e => !testReadIds.has(e.event_id)).map(e => e.event_id));
    }
    return new Set((unreadEvents || []).map(e => e.event_id));
  }, [testMode, allEvents, testReadIds, unreadEvents]);

  // Filter events based on active tab
  const effectiveEvents = activeTab === 'unread'
    ? allEvents.filter(e => unreadEventIds.has(e.event_id))
    : allEvents;

  // In test mode, filter by local read state; otherwise use context's unreadCount
  const notificationCount = testMode
    ? allEvents.filter(e => !testReadIds.has(e.event_id)).length
    : unreadCount;

  const open = Boolean(anchorEl);
  const id = open ? 'notification-popover' : undefined;

  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const notifications = effectiveEvents.slice(0, MAX_VISIBLE_NOTIFICATIONS).map((event) => {
    const payload = event.payload || {};
    const isRead = !unreadEventIds.has(event.event_id);
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
      isRead,
    };
  });

  const handleNotificationClick = (notification) => {
    // Mark as read
    if (testMode) {
      setTestReadIds(prev => new Set([...prev, notification.id]));
    } else {
      markEventAsRead(notification.id);
    }

    const params = new URLSearchParams();
    if (notification.date) params.set('date', notification.date);
    if (notification.metric) params.set('metric', notification.metric);

    handleClose();
    navigate(`/details/${notification.siteId}?${params.toString()}`);
  };

  const handleViewAll = () => {
    handleClose();
    navigate('/notifications');
  };

  const handleMarkAllRead = () => {
    if (testMode) {
      setTestReadIds(new Set(effectiveEvents.map(e => e.event_id)));
    } else {
      markAllEventsAsRead();
    }
    handleClose();
  };

  return (
    <>
      <Tooltip title="Notifications">
        <IconButton
          aria-describedby={id}
          onClick={handleClick}
          color={iconColor}
          size="large"
        >
          <Badge badgeContent={notificationCount} color="error" max={99}>
            <NotificationsIcon />
          </Badge>
        </IconButton>
      </Tooltip>

      <Popover
        id={id}
        open={open}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'right',
        }}
        transformOrigin={{
          vertical: 'top',
          horizontal: 'right',
        }}
        PaperProps={{
          sx: {
            width: 360,
            maxWidth: '100vw',
            maxHeight: 480,
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
          },
        }}
      >
        {/* Header */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            px: 2,
            py: 1.5,
            borderBottom: 1,
            borderColor: 'divider',
          }}
        >
          <Typography variant="h6" fontWeight="bold">
            Notifications
          </Typography>
          {testMode && (
            <Typography variant="caption" sx={{ bgcolor: 'warning.light', px: 1, py: 0.25, borderRadius: 1 }}>
              TEST
            </Typography>
          )}
          {notificationCount > 0 && (
            <Button size="small" onClick={handleMarkAllRead}>
              Mark all read
            </Button>
          )}
          <Tooltip title="Notification settings">
            <IconButton
              component={RouterLink}
              to="/notifications?tab=settings"
              size="small"
              onClick={handleClose}
            >
              <SettingsIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>

        {/* Tabs */}
        <Tabs
          value={activeTab}
          onChange={(e, newValue) => setActiveTab(newValue)}
          variant="fullWidth"
          sx={{
            minHeight: 36,
            borderBottom: 1,
            borderColor: 'divider',
            '& .MuiTab-root': {
              minHeight: 36,
              py: 0.5,
              textTransform: 'none',
              fontSize: '0.875rem',
            },
          }}
        >
          <Tab
            value="unread"
            label={notificationCount > 0 ? `Unread (${notificationCount})` : 'Unread'}
          />
          <Tab
            value="all"
            label={allEvents.length > 0 ? `All (${allEvents.length})` : 'All'}
          />
        </Tabs>

        {/* Notification list */}
        <Box sx={{ flex: 1, overflow: 'auto' }}>
          {notifications.length === 0 ? (
            <Box sx={{ py: 6, textAlign: 'center' }}>
              <NotificationsIcon sx={{ fontSize: 48, color: 'grey.400', mb: 1 }} />
              <Typography variant="body2" color="text.secondary">
                {activeTab === 'unread' ? 'No unread notifications' : 'No notifications yet'}
              </Typography>
            </Box>
          ) : (
            notifications.map((item, index) => (
              <Box key={item.id}>
                {index > 0 && <Divider />}
                <Card
                  elevation={0}
                  sx={{
                    borderRadius: 0,
                    // Unread notifications have a subtle blue background
                    backgroundColor: item.isRead ? 'transparent' : 'action.hover',
                    '&:hover': {
                      backgroundColor: item.isRead ? 'action.hover' : 'action.selected',
                    },
                  }}
                >
                  <CardActionArea
                    onClick={() => handleNotificationClick(item)}
                    sx={{ px: 2, py: 1.5 }}
                  >
                    <Box sx={{ display: 'flex', gap: 1.5 }}>
                      {/* Icon with unread indicator */}
                      <Box sx={{ position: 'relative' }}>
                        <Box
                          sx={{
                            width: 40,
                            height: 40,
                            borderRadius: '50%',
                            backgroundColor: item.isRead ? 'grey.200' : 'primary.light',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            flexShrink: 0,
                          }}
                        >
                          {getEventIcon(item.eventType)}
                        </Box>
                        {/* Blue dot for unread */}
                        {!item.isRead && (
                          <Box
                            sx={{
                              position: 'absolute',
                              top: 0,
                              right: 0,
                              width: 10,
                              height: 10,
                              borderRadius: '50%',
                              backgroundColor: 'primary.main',
                              border: '2px solid',
                              borderColor: 'background.paper',
                            }}
                          />
                        )}
                      </Box>

                      {/* Content */}
                      <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', mb: 0.25 }}>
                          <Typography 
                            variant="body2" 
                            fontWeight={item.isRead ? 'normal' : 'bold'} 
                            noWrap
                          >
                            {item.siteName}
                          </Typography>
                          <Typography variant="caption" color="text.secondary" sx={{ ml: 1, flexShrink: 0 }}>
                            {formatTimeAgo(item.triggeredAt)}
                          </Typography>
                        </Box>

                        <Typography variant="body2" color="text.secondary" sx={{ mb: 0.5 }}>
                          {item.metric} • {formatPredictionDate(item.date)}
                        </Typography>

                        {/* Progress bar */}
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <LinearProgress
                            variant="determinate"
                            value={item.value}
                            color={getProgressColor(item.value)}
                            sx={{
                              flex: 1,
                              height: 4,
                              borderRadius: 2,
                              backgroundColor: 'grey.200',
                            }}
                          />
                          <Typography
                            variant="caption"
                            fontWeight="bold"
                            sx={{ color: `${getProgressColor(item.value)}.main` }}
                          >
                            {item.value}%
                          </Typography>
                        </Box>
                      </Box>
                    </Box>
                  </CardActionArea>
                </Card>
              </Box>
            ))
          )}
        </Box>

        {/* Footer */}
        {(notifications.length > 0 || allEvents.length > 0) && (
          <Box sx={{ borderTop: 1, borderColor: 'divider' }}>
            <Button
              fullWidth
              onClick={handleViewAll}
              sx={{ py: 1.5, borderRadius: 0 }}
            >
              {effectiveEvents.length > MAX_VISIBLE_NOTIFICATIONS
                ? `View all ${effectiveEvents.length} notifications`
                : 'View full history'}
            </Button>
          </Box>
        )}
      </Popover>
    </>
  );
};

export default NotificationDropdown;

