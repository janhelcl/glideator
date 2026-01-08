import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Collapse,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  Grid,
  IconButton,
  InputLabel,
  List,
  ListItem,
  ListItemSecondaryAction,
  ListItemText,
  ListSubheader,
  MenuItem,
  Paper,
  Select,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import CloseIcon from '@mui/icons-material/Close';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import HistoryIcon from '@mui/icons-material/History';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import NotificationsOffIcon from '@mui/icons-material/NotificationsOff';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import TrendingDownIcon from '@mui/icons-material/TrendingDown';
import NewReleasesIcon from '@mui/icons-material/NewReleases';
import { useLocation, useNavigate } from 'react-router-dom';

import { useNotifications } from '../context/NotificationContext';
import { useAuth } from '../context/AuthContext';
import { fetchSitesList } from '../api';
import { AVAILABLE_METRICS } from '../types/ui-state';
import StandaloneMetricControl from './StandaloneMetricControl';

const COMPARISON_OPTIONS = [
  { value: 'gte', label: '>= (at least)' },
  { value: 'gt', label: '> (greater than)' },
  { value: 'lte', label: '<= (at most)' },
  { value: 'lt', label: '< (less than)' },
  { value: 'eq', label: '= (exact match)' },
];

const DEFAULT_RULE_FORM = {
  site_id: '',
  metric: 'XC0',
  comparison: 'gte',
  threshold: 50,
  lead_time_hours: 0,
  improvement_threshold: 15,
  active: true,
};

const formatTimestamp = (isoString) => {
  if (!isoString) return '--';
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  return date.toLocaleString();
};

const truncate = (value, maxLength = 36) => {
  if (!value) return '';
  if (value.length <= maxLength) return value;
  return `${value.slice(0, maxLength)}...`;
};

const getEventTypeDisplay = (eventType) => {
  switch (eventType) {
    case 'deteriorated':
      return {
        label: 'Conditions dropped',
        color: 'warning',
        icon: <TrendingDownIcon fontSize="small" />,
      };
    case 'improved':
      return {
        label: 'Conditions improved',
        color: 'success',
        icon: <TrendingUpIcon fontSize="small" />,
      };
    case 'initial':
    default:
      return {
        label: 'Initial alert',
        color: 'info',
        icon: <NewReleasesIcon fontSize="small" />,
      };
  }
};

const NotificationManager = ({ defaultMetric = 'XC0', identityLabel: identityProp }) => {
  const { user, profile, favorites } = useAuth();
  const identityLabel = identityProp || profile?.display_name || user?.email || 'Current device';

  const {
    pushSupported,
    permission,
    subscriptions,
    notifications,
    eventsByNotification,
    registerCurrentDevice,
    deactivateSubscription,
    createRule,
    updateRule,
    deleteRule,
    loadNotificationEvents,
    isLoading,
    error,
    clearError,
  } = useNotifications();

  const location = useLocation();
  const navigate = useNavigate();

  const [status, setStatus] = useState({ type: null, message: null });
  const [sites, setSites] = useState([]);
  const { favoriteSites, otherSites } = useMemo(() => {
    const favoriteSet = new Set(favorites.map(String));
    const allSites = (sites || [])
      .map((site) => ({
        value: String(site.site_id ?? site[0]),
        label: site.name ?? site[1],
      }))
      .sort((a, b) => a.label.localeCompare(b.label));

    return {
      favoriteSites: allSites.filter((s) => favoriteSet.has(s.value)),
      otherSites: allSites.filter((s) => !favoriteSet.has(s.value)),
    };
  }, [sites, favorites]);

  const [ruleDialogOpen, setRuleDialogOpen] = useState(false);
  const [ruleSubmitting, setRuleSubmitting] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [ruleForm, setRuleForm] = useState(DEFAULT_RULE_FORM);
  const [siteSearch, setSiteSearch] = useState('');
  const [expandedRuleId, setExpandedRuleId] = useState(null);
  const [eventsLoadingId, setEventsLoadingId] = useState(null);
  const [subscriptionSubmitting, setSubscriptionSubmitting] = useState(false);

  useEffect(() => {
    const loadSites = async () => {
      try {
        const data = await fetchSitesList();
        setSites(data || []);
      } catch (err) {
        console.error('Failed to load site list', err);
      }
    };
    loadSites();
  }, []);

  const handleOpenRuleDialog = useCallback((rule = null, preset = {}) => {
    clearError();
    if (rule) {
      setEditingRule(rule);
      setRuleForm({
        site_id: String(rule.site_id),
        metric: rule.metric,
        comparison: rule.comparison,
        threshold: rule.threshold ?? 0,
        lead_time_hours: rule.lead_time_hours ?? 0,
        improvement_threshold: rule.improvement_threshold ?? 15,
        active: rule.active,
      });
    } else {
      setEditingRule(null);
      setRuleForm({
        site_id: preset.siteId ? String(preset.siteId) : '',
        metric: preset.metric || defaultMetric,
        comparison: preset.comparison || DEFAULT_RULE_FORM.comparison,
        threshold:
          preset.threshold !== undefined ? preset.threshold : DEFAULT_RULE_FORM.threshold,
        lead_time_hours:
          preset.lead_time_hours !== undefined
            ? preset.lead_time_hours
            : DEFAULT_RULE_FORM.lead_time_hours,
        improvement_threshold: DEFAULT_RULE_FORM.improvement_threshold,
        active: true,
      });
    }
    setRuleDialogOpen(true);
  }, [clearError, defaultMetric]);

  useEffect(() => {
    const setup = location.state?.notificationSetup;
    if (setup) {
      handleOpenRuleDialog(null, setup);
      const { notificationSetup, ...restState } = location.state || {};
      navigate(location.pathname, { replace: true, state: Object.keys(restState).length ? restState : null });
    }
  }, [location.pathname, location.state, navigate, handleOpenRuleDialog]);

  const handleCloseRuleDialog = useCallback(() => {
    setRuleDialogOpen(false);
    setEditingRule(null);
    setRuleForm(DEFAULT_RULE_FORM);
    setSiteSearch('');
  }, []);

  const filteredFavoriteSites = useMemo(() => {
    if (!siteSearch.trim()) return favoriteSites;
    const search = siteSearch.toLowerCase();
    return favoriteSites.filter((s) => s.label.toLowerCase().includes(search));
  }, [favoriteSites, siteSearch]);

  const filteredOtherSites = useMemo(() => {
    if (!siteSearch.trim()) return otherSites;
    const search = siteSearch.toLowerCase();
    return otherSites.filter((s) => s.label.toLowerCase().includes(search));
  }, [otherSites, siteSearch]);

  const renderPermissionAlert = () => {
    if (!pushSupported) {
      return (
        <Alert severity="warning" sx={{ mb: 2 }}>
          Push notifications are not supported in this browser.
        </Alert>
      );
    }
    if (permission === 'denied') {
      return (
        <Alert severity="error" sx={{ mb: 2 }}>
          Notifications are blocked in your browser settings. Please allow them to receive alerts.
        </Alert>
      );
    }
    if (permission === 'granted') {
      return (
        <Alert severity="success" sx={{ mb: 2 }}>
          Notifications are enabled. Manage your devices and alert rules below.
        </Alert>
      );
    }
    return (
      <Alert severity="info" sx={{ mb: 2 }}>
        Enable push notifications to receive flight alerts for your favourite sites.
      </Alert>
    );
  };

  const handleRuleFieldChange = (event) => {
    const { name, value, type, checked } = event.target;
    setRuleForm((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleRuleSubmit = async (event) => {
    event.preventDefault();
    setRuleSubmitting(true);
    clearError();
    try {
      const payload = {
        site_id: Number(ruleForm.site_id),
        metric: ruleForm.metric,
        comparison: ruleForm.comparison,
        threshold: Number(ruleForm.threshold),
        lead_time_hours: Number(ruleForm.lead_time_hours),
        improvement_threshold: Number(ruleForm.improvement_threshold),
        active: Boolean(ruleForm.active),
      };

      if (Number.isNaN(payload.site_id) || payload.site_id === 0) {
        throw new Error('Please choose a site.');
      }
      if (Number.isNaN(payload.threshold)) {
        throw new Error('Threshold must be a number.');
      }

      if (editingRule) {
        await updateRule(editingRule.notification_id, payload);
      } else {
        await createRule(payload);
      }
      handleCloseRuleDialog();
      setStatus({ type: 'success', message: 'Notification saved.' });
    } catch (err) {
      const detail =
        err?.response?.data?.detail || err?.message || 'Failed to save notification.';
      setStatus({ type: 'error', message: detail });
    } finally {
      setRuleSubmitting(false);
    }
  };

  const handleRegisterDevice = async () => {
    setSubscriptionSubmitting(true);
    clearError();
    try {
      await registerCurrentDevice({
        label: identityLabel,
      });
      setStatus({ type: 'success', message: 'Device registered for notifications.' });
    } catch (err) {
      const detail =
        err?.response?.data?.detail || err?.message || 'Failed to register device.';
      setStatus({ type: 'error', message: detail });
    } finally {
      setSubscriptionSubmitting(false);
    }
  };

  const handleDeactivateSubscription = async (subscriptionId) => {
    setSubscriptionSubmitting(true);
    clearError();
    try {
      await deactivateSubscription(subscriptionId);
      setStatus({ type: 'success', message: 'Device disabled.' });
    } catch (err) {
      const detail =
        err?.response?.data?.detail || err?.message || 'Failed to disable device.';
      setStatus({ type: 'error', message: detail });
    } finally {
      setSubscriptionSubmitting(false);
    }
  };

  const handleToggleRuleActive = async (rule) => {
    try {
      await updateRule(rule.notification_id, { active: !rule.active });
    } catch (err) {
      const detail =
        err?.response?.data?.detail || err?.message || 'Failed to update notification.';
      setStatus({ type: 'error', message: detail });
    }
  };

  const handleDeleteRule = async (rule) => {
    try {
      await deleteRule(rule.notification_id);
      setStatus({ type: 'success', message: 'Notification deleted.' });
    } catch (err) {
      const detail =
        err?.response?.data?.detail || err?.message || 'Failed to delete notification.';
      setStatus({ type: 'error', message: detail });
    }
  };

  const handleToggleEvents = async (ruleId) => {
    const isExpanding = expandedRuleId !== ruleId;
    setExpandedRuleId(isExpanding ? ruleId : null);
    if (isExpanding && !eventsByNotification[ruleId]) {
      setEventsLoadingId(ruleId);
      try {
        await loadNotificationEvents(ruleId);
      } catch (err) {
        const detail =
          err?.response?.data?.detail || err?.message || 'Failed to load events.';
        setStatus({ type: 'error', message: detail });
      } finally {
        setEventsLoadingId(null);
      }
    }
  };

  const getSiteName = (siteId) => {
    const option =
      favoriteSites.find((opt) => Number(opt.value) === Number(siteId)) ||
      otherSites.find((opt) => Number(opt.value) === Number(siteId));
    return option ? option.label : `Site ${siteId}`;
  };

  return (
    <Box>
      {status.type && (
        <Alert
          severity={status.type}
          sx={{ mb: 2 }}
          onClose={() => setStatus({ type: null, message: null })}
        >
          {status.message}
        </Alert>
      )}

      {renderPermissionAlert()}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={clearError}>
          {error?.response?.data?.detail || error.message || 'Notification request failed.'}
        </Alert>
      )}

      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }}>
        <Button
          variant="contained"
          startIcon={<NotificationsActiveIcon />}
          onClick={handleRegisterDevice}
          disabled={subscriptionSubmitting || permission === 'denied' || !pushSupported}
        >
          {permission === 'granted' ? 'Register this device' : 'Enable notifications'}
        </Button>
        {permission === 'denied' && (
          <Button
            variant="outlined"
            color="secondary"
            startIcon={<NotificationsOffIcon />}
            onClick={() =>
              setStatus({
                type: 'info',
                message: 'Notifications are blocked. Update browser permissions and try again.',
              })
            }
          >
            Notifications blocked
          </Button>
        )}
      </Stack>

      <Paper variant="outlined" sx={{ mb: 4 }}>
        <Box sx={{ p: 2 }}>
          <Typography variant="subtitle1" sx={{ fontWeight: 'bold', mb: 1 }}>
            Registered devices
          </Typography>
          {subscriptions.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              No devices registered yet.
            </Typography>
          ) : (
            <List dense disablePadding>
              {subscriptions.map((subscription) => (
                <ListItem key={subscription.subscription_id} sx={{ py: 1 }}>
                  <ListItemText
                    primary={
                      subscription.client_info?.label ||
                      subscription.client_info?.name ||
                      truncate(subscription.endpoint, 48)
                    }
                    secondary={`Last active: ${formatTimestamp(subscription.last_used_at)}`}
                  />
                  <ListItemSecondaryAction>
                    <Button
                      size="small"
                      color="error"
                      startIcon={<NotificationsOffIcon />}
                      disabled={subscriptionSubmitting}
                      onClick={() => handleDeactivateSubscription(subscription.subscription_id)}
                    >
                      Disable
                    </Button>
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>
          )}
        </Box>
      </Paper>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <NotificationsActiveIcon color="primary" />
        <Typography variant="h6">Notification Rules</Typography>
      </Box>

      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }}>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpenRuleDialog()}
          disabled={!pushSupported || permission === 'denied' || isLoading}
        >
          Add notification
        </Button>
      </Stack>

      {isLoading && notifications.length === 0 ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress size={28} />
        </Box>
      ) : null}

      {notifications.length === 0 && !isLoading ? (
        <Alert severity="info" sx={{ mb: 2 }}>
          Create a notification rule to get alerts when a site matches your conditions.
        </Alert>
      ) : null}

      <Stack spacing={2}>
        {notifications.map((rule) => {
          const events = eventsByNotification[rule.notification_id] || [];
          const isExpanded = expandedRuleId === rule.notification_id;
          return (
            <Paper key={rule.notification_id} variant="outlined" sx={{ p: 2 }}>
              <Grid container spacing={2} alignItems="center">
                <Grid item xs={12} md={4}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                    {getSiteName(rule.site_id)}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Last triggered: {formatTimestamp(rule.last_triggered_at)}
                  </Typography>
                </Grid>
                <Grid item xs={12} md={4}>
                  <Stack direction="row" spacing={1} flexWrap="wrap">
                    <Chip label={`Metric ${rule.metric}`} size="small" />
                    <Chip label={`Condition ${rule.comparison} ${rule.threshold}`} size="small" />
                    <Chip label={`Lead ${rule.lead_time_hours}h`} size="small" />
                  </Stack>
                </Grid>
                <Grid item xs={12} md={4}>
                  <Stack direction="row" spacing={1} justifyContent="flex-end" alignItems="center">
                    <Stack direction="row" spacing={1} alignItems="center">
                      <Typography variant="body2">Active</Typography>
                      <Switch
                        checked={rule.active}
                        onChange={() => handleToggleRuleActive(rule)}
                        inputProps={{ 'aria-label': 'Toggle notification' }}
                      />
                    </Stack>
                    <Button
                      size="small"
                      startIcon={<HistoryIcon />}
                      onClick={() => handleToggleEvents(rule.notification_id)}
                    >
                      Events
                    </Button>
                    <IconButton size="small" onClick={() => handleOpenRuleDialog(rule)}>
                      <EditIcon fontSize="small" />
                    </IconButton>
                    <IconButton size="small" color="error" onClick={() => handleDeleteRule(rule)}>
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Stack>
                </Grid>
              </Grid>

              <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                <Divider sx={{ my: 2 }} />
                {eventsLoadingId === rule.notification_id ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
                    <CircularProgress size={24} />
                  </Box>
                ) : events.length === 0 ? (
                  <Typography variant="body2" color="text.secondary">
                    No recent events recorded.
                  </Typography>
                ) : (
                  <Stack spacing={1}>
                    {events.map((event) => {
                      const eventTypeInfo = getEventTypeDisplay(event.payload?.event_type);
                      return (
                        <Paper key={event.event_id} variant="outlined" sx={{ p: 1.5 }}>
                          <Stack
                            direction={{ xs: 'column', sm: 'row' }}
                            spacing={1}
                            justifyContent="space-between"
                            alignItems={{ sm: 'center' }}
                          >
                            <Stack direction="row" spacing={1} alignItems="center">
                              <Typography variant="subtitle2">
                                {formatTimestamp(event.triggered_at)}
                              </Typography>
                              <Chip
                                icon={eventTypeInfo.icon}
                                label={eventTypeInfo.label}
                                size="small"
                                color={eventTypeInfo.color}
                                variant="outlined"
                              />
                            </Stack>
                            <Typography variant="body2" color="text.secondary">
                              Status: {event.delivery_status}
                            </Typography>
                          </Stack>
                          <Typography variant="body2" sx={{ mt: 1 }}>
                            {event.payload?.previous_value != null ? (
                              <>
                                Value: {event.payload.previous_value}% → {event.payload?.value ?? 'n/a'}%
                                {' '}(threshold {rule.threshold}%)
                              </>
                            ) : (
                              <>
                                Value: {event.payload?.value ?? 'n/a'}% (threshold {rule.threshold}%)
                              </>
                            )}
                          </Typography>
                          {event.payload?.prediction_date && (
                            <Typography variant="caption" color="text.secondary">
                              Forecast date {event.payload.prediction_date}
                            </Typography>
                          )}
                        </Paper>
                      );
                    })}
                  </Stack>
                )}
              </Collapse>
            </Paper>
          );
        })}
      </Stack>

      <Dialog open={ruleDialogOpen} onClose={handleCloseRuleDialog} fullWidth maxWidth="sm">
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          {editingRule ? 'Edit notification' : 'Create notification'}
          <IconButton onClick={handleCloseRuleDialog}>
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers>
          <Box component="form" id="notification-rule-form" onSubmit={handleRuleSubmit} sx={{ mt: 1 }}>
            <Stack spacing={2}>
              <FormControl fullWidth required>
                <InputLabel id="notification-site-label">Site</InputLabel>
                <Select
                  labelId="notification-site-label"
                  label="Site"
                  name="site_id"
                  value={ruleForm.site_id}
                  onChange={handleRuleFieldChange}
                  onClose={() => setSiteSearch('')}
                  MenuProps={{ autoFocus: false }}
                >
                  <ListSubheader sx={{ bgcolor: 'background.paper' }}>
                    <TextField
                      size="small"
                      autoFocus
                      placeholder="Search sites..."
                      fullWidth
                      value={siteSearch}
                      onChange={(e) => setSiteSearch(e.target.value)}
                      onKeyDown={(e) => e.stopPropagation()}
                    />
                  </ListSubheader>
                  {filteredFavoriteSites.length > 0 && [
                    <ListSubheader key="favorites-header">Favorites</ListSubheader>,
                    ...filteredFavoriteSites.map((option) => (
                      <MenuItem key={option.value} value={option.value}>
                        {option.label}
                      </MenuItem>
                    )),
                  ]}
                  {filteredOtherSites.length > 0 && (
                    <ListSubheader key="all-sites-header">All Sites</ListSubheader>
                  )}
                  {filteredOtherSites.map((option) => (
                    <MenuItem key={option.value} value={option.value}>
                      {option.label}
                    </MenuItem>
                  ))}
                  {filteredFavoriteSites.length === 0 && filteredOtherSites.length === 0 && (
                    <MenuItem disabled>No sites found</MenuItem>
                  )}
                </Select>
              </FormControl>

              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  px: 2,
                  py: 1.5,
                }}
              >
                <Typography variant="body1">
                  Metric: <strong>{ruleForm.metric}</strong>
                </Typography>
                <StandaloneMetricControl
                  metrics={AVAILABLE_METRICS}
                  selectedMetric={ruleForm.metric}
                  onMetricChange={(metric) =>
                    setRuleForm((prev) => ({ ...prev, metric }))
                  }
                />
              </Box>

              <Grid container spacing={2}>
                <Grid item xs={12} sm={6}>
                  <FormControl fullWidth>
                    <InputLabel id="notification-comparison-label">Comparison</InputLabel>
                    <Select
                      labelId="notification-comparison-label"
                      label="Comparison"
                      name="comparison"
                      value={ruleForm.comparison}
                      onChange={handleRuleFieldChange}
                    >
                      {COMPARISON_OPTIONS.map((option) => (
                        <MenuItem key={option.value} value={option.value}>
                          {option.label}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
                <Grid item xs={12} sm={6}>
                  <TextField
                    fullWidth
                    label="Threshold"
                    name="threshold"
                    type="number"
                    value={ruleForm.threshold}
                    onChange={handleRuleFieldChange}
                    inputProps={{ step: 'any', min: 0 }}
                  />
                </Grid>
              </Grid>

              <TextField
                fullWidth
                label="Lead time (hours)"
                name="lead_time_hours"
                type="number"
                value={ruleForm.lead_time_hours}
                onChange={handleRuleFieldChange}
                inputProps={{ min: 0, max: 168 }}
                helperText="Notify this many hours before the forecast window (0 for immediate)."
              />

              <TextField
                fullWidth
                label="Improvement threshold (%)"
                name="improvement_threshold"
                type="number"
                value={ruleForm.improvement_threshold}
                onChange={handleRuleFieldChange}
                inputProps={{ min: 0, max: 100, step: 5 }}
                helperText="Re-notify when conditions improve by this many percentage points (e.g., 35% to 50%)."
              />

              <Stack direction="row" spacing={1} alignItems="center">
                <Switch
                  name="active"
                  checked={ruleForm.active}
                  onChange={handleRuleFieldChange}
                />
                <Typography>Rule is active</Typography>
              </Stack>
            </Stack>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseRuleDialog}>Cancel</Button>
          <Button
            type="submit"
            form="notification-rule-form"
            variant="contained"
            disabled={ruleSubmitting}
          >
            {ruleSubmitting ? 'Saving...' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default NotificationManager;
