import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  LinearProgress,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import {
  fetchAdminAnalytics,
  fetchAdminFeedback,
  fetchAdminUsers,
} from '../../adminApi';

const formatDateTime = (value) => {
  if (!value) return '—';
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
};

const InsightCard = ({ label, value, detail }) => (
  <Card variant="outlined" sx={{ height: '100%' }}>
    <CardContent>
      <Typography variant="overline" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="h4" sx={{ mt: 0.5, fontWeight: 700 }}>
        {value}
      </Typography>
      {detail && (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          {detail}
        </Typography>
      )}
    </CardContent>
  </Card>
);

const SectionTitle = ({ children, detail }) => (
  <Box sx={{ mb: 1.5 }}>
    <Typography variant="h6" sx={{ fontWeight: 700 }}>{children}</Typography>
    {detail && <Typography variant="body2" color="text.secondary">{detail}</Typography>}
  </Box>
);

const ActivityBars = ({ daily }) => {
  const maxVisitors = useMemo(
    () => Math.max(1, ...(daily || []).map((point) => point.visitors)),
    [daily],
  );

  if (!daily?.length) {
    return <Typography color="text.secondary">No activity in this period.</Typography>;
  }

  return (
    <Stack spacing={1}>
      {daily.map((point) => (
        <Stack key={point.day} direction="row" spacing={1.5} alignItems="center">
          <Typography variant="caption" sx={{ width: 78, flexShrink: 0 }}>
            {point.day.slice(5)}
          </Typography>
          <Box sx={{ flexGrow: 1, height: 10, backgroundColor: 'action.hover', borderRadius: 1 }}>
            <Box
              sx={{
                width: `${Math.max(3, 100 * point.visitors / maxVisitors)}%`,
                height: '100%',
                backgroundColor: 'primary.main',
                borderRadius: 1,
              }}
            />
          </Box>
          <Typography variant="caption" sx={{ width: 110, textAlign: 'right', flexShrink: 0 }}>
            {point.visitors} visitors · {point.sessions} sessions
          </Typography>
        </Stack>
      ))}
    </Stack>
  );
};

export const AdminAnalyticsPanel = () => {
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setData(await fetchAdminAnalytics(days));
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load product analytics.');
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <Stack spacing={3}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        justifyContent="space-between"
        alignItems={{ xs: 'stretch', sm: 'center' }}
        spacing={1.5}
      >
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 700 }}>Product analytics</Typography>
          <Typography variant="body2" color="text.secondary">
            First-party anonymous visitors, sessions and meaningful product actions.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <TextField
            select
            size="small"
            label="Period"
            value={days}
            onChange={(event) => setDays(Number(event.target.value))}
            sx={{ minWidth: 120 }}
          >
            <MenuItem value={7}>7 days</MenuItem>
            <MenuItem value={30}>30 days</MenuItem>
            <MenuItem value={90}>90 days</MenuItem>
            <MenuItem value={365}>1 year</MenuItem>
          </TextField>
          <Button variant="outlined" startIcon={<RefreshIcon />} onClick={load} disabled={loading}>
            Refresh
          </Button>
        </Stack>
      </Stack>

      {loading && <LinearProgress />}
      {error && <Alert severity="error">{error}</Alert>}

      {data && (
        <>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} lg={3}>
              <InsightCard label="Anonymous visitors" value={data.unique_visitors} detail={`${data.window_days}-day window`} />
            </Grid>
            <Grid item xs={12} sm={6} lg={3}>
              <InsightCard label="Sessions" value={data.unique_sessions} detail={`${data.total_events.toLocaleString()} captured events`} />
            </Grid>
            <Grid item xs={12} sm={6} lg={3}>
              <InsightCard label="Map → site" value={`${data.map_to_site_rate}%`} detail={`${data.site_detail_sessions} of ${data.map_sessions} map sessions`} />
            </Grid>
            <Grid item xs={12} sm={6} lg={3}>
              <InsightCard
                label="Planner → results"
                value={`${data.trip_planner.results_rate}%`}
                detail={`${data.trip_planner.results_sessions} of ${data.trip_planner.submitted_sessions} sessions`}
              />
            </Grid>
          </Grid>

          <Grid container spacing={3}>
            <Grid item xs={12} lg={7}>
              <Paper variant="outlined" sx={{ p: 2.5, height: '100%' }}>
                <SectionTitle detail="Distinct anonymous visitors and sessions by day">Daily activity</SectionTitle>
                <ActivityBars daily={data.daily} />
              </Paper>
            </Grid>
            <Grid item xs={12} lg={5}>
              <Paper variant="outlined" sx={{ p: 2.5, height: '100%' }}>
                <SectionTitle detail="Distinct sessions reaching each stage">Trip Planner funnel</SectionTitle>
                <Stack spacing={1.5}>
                  <Stack direction="row" justifyContent="space-between">
                    <Typography>Submitted criteria</Typography>
                    <Typography fontWeight={700}>{data.trip_planner.submitted_sessions}</Typography>
                  </Stack>
                  <Stack direction="row" justifyContent="space-between">
                    <Typography>Viewed results</Typography>
                    <Typography fontWeight={700}>
                      {data.trip_planner.results_sessions} ({data.trip_planner.results_rate}%)
                    </Typography>
                  </Stack>
                  <Stack direction="row" justifyContent="space-between">
                    <Typography>Opened a suggested site</Typography>
                    <Typography fontWeight={700}>
                      {data.trip_planner.opened_site_sessions} ({data.trip_planner.site_open_rate}%)
                    </Typography>
                  </Stack>
                </Stack>
              </Paper>
            </Grid>
          </Grid>

          <Grid container spacing={3}>
            <Grid item xs={12} lg={6}>
              <Paper variant="outlined" sx={{ p: 2.5 }}>
                <SectionTitle detail="What visitors actually do">Top events</SectionTitle>
                <TableContainer sx={{ maxHeight: 360 }}>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell>Event</TableCell>
                        <TableCell align="right">Events</TableCell>
                        <TableCell align="right">Visitors</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {data.event_counts.map((row) => (
                        <TableRow key={row.event_name} hover>
                          <TableCell>{row.event_name}</TableCell>
                          <TableCell align="right">{row.events}</TableCell>
                          <TableCell align="right">{row.visitors}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            </Grid>
            <Grid item xs={12} lg={6}>
              <Paper variant="outlined" sx={{ p: 2.5 }}>
                <SectionTitle detail="Site-detail and planner-result interactions">Most engaged sites</SectionTitle>
                <TableContainer sx={{ maxHeight: 360 }}>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell>Site</TableCell>
                        <TableCell align="right">Interactions</TableCell>
                        <TableCell align="right">Visitors</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {data.top_sites.map((row) => (
                        <TableRow key={row.site_id || row.site_name} hover>
                          <TableCell>{row.site_name || `Site ${row.site_id}`}</TableCell>
                          <TableCell align="right">{row.interactions}</TableCell>
                          <TableCell align="right">{row.visitors}</TableCell>
                        </TableRow>
                      ))}
                      {data.top_sites.length === 0 && (
                        <TableRow><TableCell colSpan={3}>No site interactions yet.</TableCell></TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            </Grid>
          </Grid>

          <Grid container spacing={3}>
            <Grid item xs={12} lg={6}>
              <Paper variant="outlined" sx={{ p: 2.5 }}>
                <SectionTitle detail="Contextual helpful / not-helpful responses">Recommendation feedback</SectionTitle>
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Surface</TableCell>
                        <TableCell align="right">Helpful</TableCell>
                        <TableCell align="right">Not helpful</TableCell>
                        <TableCell align="right">Rate</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {data.recommendation_feedback.map((row) => (
                        <TableRow key={row.surface} hover>
                          <TableCell>{row.surface}</TableCell>
                          <TableCell align="right">{row.helpful}</TableCell>
                          <TableCell align="right">{row.not_helpful}</TableCell>
                          <TableCell align="right">{row.helpful_rate == null ? '—' : `${row.helpful_rate}%`}</TableCell>
                        </TableRow>
                      ))}
                      {data.recommendation_feedback.length === 0 && (
                        <TableRow><TableCell colSpan={4}>No contextual feedback yet.</TableCell></TableRow>
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            </Grid>
            <Grid item xs={12} lg={6}>
              <Paper variant="outlined" sx={{ p: 2.5 }}>
                <SectionTitle detail="Routes receiving the most captured activity">Top paths</SectionTitle>
                <TableContainer sx={{ maxHeight: 320 }}>
                  <Table size="small" stickyHeader>
                    <TableHead>
                      <TableRow>
                        <TableCell>Path</TableCell>
                        <TableCell align="right">Events</TableCell>
                        <TableCell align="right">Visitors</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {data.top_paths.map((row) => (
                        <TableRow key={row.path} hover>
                          <TableCell>{row.path}</TableCell>
                          <TableCell align="right">{row.events}</TableCell>
                          <TableCell align="right">{row.visitors}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </Paper>
            </Grid>
          </Grid>
        </>
      )}
    </Stack>
  );
};

export const AdminUsersPanel = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setData(await fetchAdminUsers(250));
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load registered users.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <Stack spacing={3}>
      <Stack direction="row" justifyContent="space-between" alignItems="center">
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 700 }}>Registered users</Typography>
          <Typography variant="body2" color="text.secondary">
            Account growth and adoption of favorites, notifications and push delivery.
          </Typography>
        </Box>
        <Button variant="outlined" startIcon={<RefreshIcon />} onClick={load} disabled={loading}>
          Refresh
        </Button>
      </Stack>
      {loading && <LinearProgress />}
      {error && <Alert severity="error">{error}</Alert>}
      {data && (
        <>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} lg={3}>
              <InsightCard label="Registered" value={data.total_users} detail={`${data.active_users} active accounts`} />
            </Grid>
            <Grid item xs={12} sm={6} lg={3}>
              <InsightCard label="New users" value={data.new_users_30d} detail={`${data.new_users_7d} in the last 7 days`} />
            </Grid>
            <Grid item xs={12} sm={6} lg={3}>
              <InsightCard label="Using favorites" value={data.users_with_favorites} detail={`${data.total_users ? Math.round(100 * data.users_with_favorites / data.total_users) : 0}% adoption`} />
            </Grid>
            <Grid item xs={12} sm={6} lg={3}>
              <InsightCard label="Using alerts" value={data.users_with_notifications} detail={`${data.users_with_push} with active push`} />
            </Grid>
          </Grid>

          <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: '65vh' }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell>User</TableCell>
                  <TableCell>Registered</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">Favorites</TableCell>
                  <TableCell align="right">Alerts</TableCell>
                  <TableCell align="right">Push subscriptions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.items.map((user) => (
                  <TableRow key={user.user_id} hover>
                    <TableCell>
                      <Stack spacing={0.25}>
                        <Typography variant="body2">{user.display_name || user.email}</Typography>
                        {user.display_name && <Typography variant="caption" color="text.secondary">{user.email}</Typography>}
                      </Stack>
                    </TableCell>
                    <TableCell>{formatDateTime(user.created_at)}</TableCell>
                    <TableCell>
                      <Stack direction="row" spacing={0.5}>
                        <Chip size="small" label={user.is_active ? 'active' : 'inactive'} color={user.is_active ? 'success' : 'default'} />
                        {user.role === 'admin' && <Chip size="small" label="admin" color="primary" />}
                      </Stack>
                    </TableCell>
                    <TableCell align="right">{user.favorite_count}</TableCell>
                    <TableCell align="right">{user.notification_count}</TableCell>
                    <TableCell align="right">{user.active_push_subscriptions}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      )}
    </Stack>
  );
};

export const AdminFeedbackPanel = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setData(await fetchAdminFeedback(250));
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load feedback.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <Stack spacing={3}>
      <Stack direction="row" justifyContent="space-between" alignItems="center">
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 700 }}>Written feedback</Typography>
          <Typography variant="body2" color="text.secondary">
            Messages submitted through the authenticated feedback form.
          </Typography>
        </Box>
        <Button variant="outlined" startIcon={<RefreshIcon />} onClick={load} disabled={loading}>
          Refresh
        </Button>
      </Stack>
      {loading && <LinearProgress />}
      {error && <Alert severity="error">{error}</Alert>}
      {data && (
        <>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} lg={3}>
              <InsightCard label="Submissions" value={data.total} detail={`Showing latest ${data.items.length}`} />
            </Grid>
          </Grid>
          <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: '65vh' }}>
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ width: 170 }}>Submitted</TableCell>
                  <TableCell sx={{ width: 240 }}>User</TableCell>
                  <TableCell>Message</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.items.map((feedback) => (
                  <TableRow key={feedback.id} hover>
                    <TableCell>{formatDateTime(feedback.created_at)}</TableCell>
                    <TableCell>
                      <Stack spacing={0.25}>
                        <Typography variant="body2">{feedback.display_name || feedback.user_email || 'Deleted user'}</Typography>
                        {feedback.display_name && feedback.user_email && (
                          <Typography variant="caption" color="text.secondary">{feedback.user_email}</Typography>
                        )}
                      </Stack>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {feedback.message}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
                {data.items.length === 0 && (
                  <TableRow><TableCell colSpan={3} align="center">No written feedback yet.</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      )}
    </Stack>
  );
};
