import React, { useState, useEffect, useCallback } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardActionArea,
  Chip,
  CircularProgress,
  LinearProgress,
  Stack,
  Typography,
} from '@mui/material';
import FlagIcon from '@mui/icons-material/Flag';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import HistoryIcon from '@mui/icons-material/History';
import { useNavigate } from 'react-router-dom';
import { fetchNotificationHistory } from '../api';

const PAGE_SIZE = 20;

// Deduplicate events by notification_id + prediction_date
// (same notification rule + same forecast = same logical notification)
const deduplicateEvents = (events) => {
  const seen = new Set();
  return events.filter((event) => {
    const payload = event.payload || {};
    const key = `${event.notification_id}-${payload.prediction_date}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
};

const formatTimeAgo = (isoString) => {
  if (!isoString) return '';
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
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

const getEventChip = (eventType) => {
  switch (eventType) {
    case 'improved':
      return <Chip label="Improved" size="small" color="success" variant="outlined" />;
    case 'deteriorated':
      return <Chip label="Deteriorated" size="small" color="warning" variant="outlined" />;
    default:
      return <Chip label="New" size="small" color="info" variant="outlined" />;
  }
};

const getProgressColor = (value) => {
  if (value >= 60) return 'success';
  if (value >= 40) return 'info';
  if (value >= 20) return 'warning';
  return 'error';
};

const NotificationHistory = () => {
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [hasMore, setHasMore] = useState(true);
  const [rawOffset, setRawOffset] = useState(0);

  const loadEvents = useCallback(async (offset = 0, append = false) => {
    try {
      if (append) {
        setIsLoadingMore(true);
      } else {
        setIsLoading(true);
      }
      setError(null);

      const newEvents = await fetchNotificationHistory(offset, PAGE_SIZE);

      if (append) {
        // Deduplicate when appending to existing events
        setEvents((prev) => deduplicateEvents([...prev, ...newEvents]));
      } else {
        setEvents(deduplicateEvents(newEvents));
        setRawOffset(0);
      }

      // Update raw offset based on number of events fetched
      setRawOffset((prev) => prev + newEvents.length);

      // Keep loading if we got a full page (there might be more unique events)
      setHasMore(newEvents.length === PAGE_SIZE);
    } catch (err) {
      setError(err.message || 'Failed to load notification history');
    } finally {
      setIsLoading(false);
      setIsLoadingMore(false);
    }
  }, []);

  useEffect(() => {
    loadEvents(0, false);
  }, [loadEvents]);

  const handleLoadMore = () => {
    loadEvents(rawOffset, true);
  };

  const handleEventClick = (event) => {
    const payload = event.payload || {};
    const params = new URLSearchParams();
    if (payload.prediction_date) params.set('date', payload.prediction_date);
    if (payload.metric) params.set('metric', payload.metric);
    navigate(`/details/${payload.site_id}?${params.toString()}`);
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  if (events.length === 0) {
    return (
      <Box sx={{ py: 6, textAlign: 'center' }}>
        <HistoryIcon sx={{ fontSize: 64, color: 'grey.400', mb: 2 }} />
        <Typography variant="h6" color="text.secondary" gutterBottom>
          No notification history
        </Typography>
        <Typography variant="body2" color="text.secondary">
          When you receive notifications, they will appear here.
        </Typography>
      </Box>
    );
  }

  return (
    <Stack spacing={2}>
      {events.map((event) => {
        const payload = event.payload || {};
        const value = payload.value != null ? Math.round(payload.value) : 0;
        const previousValue = payload.previous_value != null ? Math.round(payload.previous_value) : null;

        return (
          <Card key={event.event_id} variant="outlined">
            <CardActionArea onClick={() => handleEventClick(event)} sx={{ p: 2 }}>
              <Box sx={{ display: 'flex', gap: 2 }}>
                {/* Icon */}
                <Box
                  sx={{
                    width: 48,
                    height: 48,
                    borderRadius: '50%',
                    backgroundColor: 'action.hover',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  {getEventIcon(payload.event_type)}
                </Box>

                {/* Content */}
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  {/* Header row */}
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 0.5 }}>
                    <Typography variant="subtitle1" fontWeight="bold" noWrap>
                      {payload.site_name || 'Unknown site'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ ml: 1, flexShrink: 0 }}>
                      {formatTimeAgo(event.triggered_at)}
                    </Typography>
                  </Box>

                  {/* Info row */}
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, flexWrap: 'wrap' }}>
                    {getEventChip(payload.event_type)}
                    <Typography variant="body2" color="text.secondary">
                      {payload.metric} • {formatPredictionDate(payload.prediction_date)}
                    </Typography>
                  </Box>

                  {/* Progress bar */}
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <LinearProgress
                      variant="determinate"
                      value={value}
                      color={getProgressColor(value)}
                      sx={{
                        flex: 1,
                        height: 6,
                        borderRadius: 3,
                        backgroundColor: 'grey.200',
                      }}
                    />
                    <Typography
                      variant="body2"
                      fontWeight="bold"
                      sx={{ color: `${getProgressColor(value)}.main`, minWidth: 45 }}
                    >
                      {value}%
                    </Typography>
                    {previousValue != null && (
                      <Typography variant="caption" color="text.secondary">
                        (was {previousValue}%)
                      </Typography>
                    )}
                  </Box>
                </Box>
              </Box>
            </CardActionArea>
          </Card>
        );
      })}

      {/* Load more button */}
      {hasMore && (
        <Box sx={{ display: 'flex', justifyContent: 'center', pt: 2 }}>
          <Button
            variant="outlined"
            onClick={handleLoadMore}
            disabled={isLoadingMore}
            startIcon={isLoadingMore ? <CircularProgress size={16} /> : null}
          >
            {isLoadingMore ? 'Loading...' : 'Load more'}
          </Button>
        </Box>
      )}
    </Stack>
  );
};

export default NotificationHistory;
