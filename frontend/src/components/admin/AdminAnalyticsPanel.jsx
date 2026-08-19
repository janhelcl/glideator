import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
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
import { fetchAdminAnalytics } from '../../adminApi';

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

const AdminAnalyticsPanel = () => {
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
              <InsightCard
                label="Map → site"
                value={`${data.map_to_site_rate}%`}
                detail={`${data.map_to_site_sessions} of ${data.map_sessions} map sessions opened a site`}
              />
            </Grid>
            <Grid item xs={12} sm={6} lg={3}>
              <InsightCard
                label="Site opens / map session"
                value={data.sites_opened_per_map_session}
                detail={`${data.map_site_open_events} site opens across ${data.map_sessions} map sessions`}
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
                <SectionTitle detail="Distinct sessions: planner visit → results → suggested site">Trip Planner funnel</SectionTitle>
                <Stack spacing={1.5}>
                  <Stack direction="row" justifyContent="space-between">
                    <Typography>Planner sessions</Typography>
                    <Typography fontWeight={700}>{data.trip_planner.planner_sessions}</Typography>
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
                  <Stack direction="row" justifyContent="space-between">
                    <Typography color="text.secondary">Explicit criteria submits</Typography>
                    <Typography color="text.secondary" fontWeight={700}>
                      {data.trip_planner.submitted_sessions}
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

export default AdminAnalyticsPanel;
