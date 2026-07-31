import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Grid,
  IconButton,
  LinearProgress,
  Link,
  Paper,
  Stack,
  Switch,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import EditIcon from '@mui/icons-material/Edit';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import RefreshIcon from '@mui/icons-material/Refresh';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import {
  fetchAdminForecastRuns,
  fetchAdminOverview,
  fetchAdminResources,
  fetchAdminSites,
  triggerAdminForecastCheck,
  updateAdminSite,
} from '../adminApi';

const formatDateTime = (value) => {
  if (!value) return '—';
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
};

const MetricCard = ({ label, value, detail }) => (
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

const Admin = () => {
  const [tab, setTab] = useState(0);
  const [overview, setOverview] = useState(null);
  const [runs, setRuns] = useState([]);
  const [sites, setSites] = useState([]);
  const [resources, setResources] = useState(null);
  const [missingResourcesOnly, setMissingResourcesOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [resourceLoading, setResourceLoading] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [editingSite, setEditingSite] = useState(null);
  const [savingSite, setSavingSite] = useState(false);

  const loadPrimaryData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [overviewData, runData, siteData] = await Promise.all([
        fetchAdminOverview(),
        fetchAdminForecastRuns(),
        fetchAdminSites(),
      ]);
      setOverview(overviewData);
      setRuns(runData);
      setSites(siteData);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load the administrator dashboard.');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadResources = useCallback(async () => {
    setResourceLoading(true);
    setError('');
    try {
      const data = await fetchAdminResources({
        missingOnly: missingResourcesOnly,
        limit: 250,
      });
      setResources(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load site resources.');
    } finally {
      setResourceLoading(false);
    }
  }, [missingResourcesOnly]);

  useEffect(() => {
    loadPrimaryData();
  }, [loadPrimaryData]);

  useEffect(() => {
    if (tab === 3) {
      loadResources();
    }
  }, [tab, loadResources]);

  const handleRefresh = async () => {
    setNotice('');
    await loadPrimaryData();
    if (tab === 3) {
      await loadResources();
    }
  };

  const handleTriggerForecast = async () => {
    setError('');
    setNotice('');
    try {
      const operation = await triggerAdminForecastCheck();
      setNotice(`Forecast check queued as task ${operation.task_id}.`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to queue the forecast check.');
    }
  };

  const openSiteEditor = (site) => {
    setEditingSite({
      ...site,
      tagsText: (site.tags || []).join(', '),
    });
  };

  const updateEditingField = (field) => (event) => {
    setEditingSite((current) => ({
      ...current,
      [field]: event.target.value,
    }));
  };

  const handleSaveSite = async () => {
    if (!editingSite) return;
    setSavingSite(true);
    setError('');
    try {
      const updated = await updateAdminSite(editingSite.site_id, {
        name: editingSite.name.trim(),
        latitude: Number(editingSite.latitude),
        longitude: Number(editingSite.longitude),
        altitude: Number(editingSite.altitude),
        lat_gfs: Number(editingSite.lat_gfs),
        lon_gfs: Number(editingSite.lon_gfs),
        country: editingSite.country?.trim() || null,
        html: editingSite.html || '',
        tags: editingSite.tagsText
          .split(',')
          .map((tag) => tag.trim())
          .filter(Boolean),
      });
      setSites((current) => current.map((site) => (
        site.site_id === updated.site_id ? updated : site
      )));
      setEditingSite(null);
      setNotice(`${updated.name} was updated.`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update the site.');
    } finally {
      setSavingSite(false);
    }
  };

  const forecastHealthy = overview && overview.covered_sites >= overview.total_sites;

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        justifyContent="space-between"
        alignItems={{ xs: 'stretch', sm: 'center' }}
        spacing={2}
        sx={{ mb: 3 }}
      >
        <Box>
          <Stack direction="row" spacing={1} alignItems="center">
            <AdminPanelSettingsIcon color="primary" />
            <Typography variant="h4" component="h1" sx={{ fontWeight: 700 }}>
              Glideator cockpit
            </Typography>
          </Stack>
          <Typography color="text.secondary" sx={{ mt: 0.5 }}>
            Forecast operations, site data and Ground Crew resources.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={handleRefresh}
            disabled={loading || resourceLoading}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<PlayArrowIcon />}
            onClick={handleTriggerForecast}
          >
            Check forecasts
          </Button>
        </Stack>
      </Stack>

      {loading && <LinearProgress sx={{ mb: 2 }} />}
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {notice && <Alert severity="success" sx={{ mb: 2 }}>{notice}</Alert>}

      <Paper variant="outlined">
        <Tabs
          value={tab}
          onChange={(_, value) => setTab(value)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{ px: 1, borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab label="Overview" />
          <Tab label="Forecast runs" />
          <Tab label="Sites" />
          <Tab label="Resources" />
        </Tabs>

        <Box sx={{ p: { xs: 2, md: 3 } }}>
          {tab === 0 && overview && (
            <Stack spacing={3}>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} lg={3}>
                  <MetricCard
                    label="Forecast coverage"
                    value={`${overview.coverage_percent}%`}
                    detail={`${overview.covered_sites} of ${overview.total_sites} sites`}
                  />
                </Grid>
                <Grid item xs={12} sm={6} lg={3}>
                  <MetricCard
                    label="Latest GFS cycle"
                    value={formatDateTime(overview.latest_gfs_forecast_at)}
                    detail={`Published ${formatDateTime(overview.latest_computed_at)}`}
                  />
                </Grid>
                <Grid item xs={12} sm={6} lg={3}>
                  <MetricCard
                    label="Forecast horizon"
                    value={overview.forecast_start_date || '—'}
                    detail={overview.forecast_end_date ? `through ${overview.forecast_end_date}` : null}
                  />
                </Grid>
                <Grid item xs={12} sm={6} lg={3}>
                  <MetricCard
                    label="Sites with resources"
                    value={overview.resource_sites ?? '—'}
                    detail={overview.resource_coverage_percent == null
                      ? 'Ground Crew data unavailable'
                      : `${overview.resource_coverage_percent}% coverage`}
                  />
                </Grid>
              </Grid>

              <Alert
                severity={forecastHealthy ? 'success' : 'warning'}
                icon={forecastHealthy ? <CheckCircleIcon /> : <WarningAmberIcon />}
              >
                {forecastHealthy
                  ? 'The latest forecast cycle covers every configured site.'
                  : `The latest cycle is missing ${Math.max(0, overview.total_sites - overview.covered_sites)} site(s).`}
              </Alert>
            </Stack>
          )}

          {tab === 1 && (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>GFS cycle</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="right">Coverage</TableCell>
                    <TableCell>Horizon</TableCell>
                    <TableCell>Completed</TableCell>
                    <TableCell align="right">Rows</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {runs.map((run) => (
                    <TableRow key={run.gfs_forecast_at} hover>
                      <TableCell>{formatDateTime(run.gfs_forecast_at)}</TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={run.status}
                          color={run.status === 'complete' ? 'success' : 'warning'}
                        />
                      </TableCell>
                      <TableCell align="right">
                        {run.covered_sites}/{run.expected_sites} ({run.coverage_percent}%)
                      </TableCell>
                      <TableCell>{run.forecast_start_date} – {run.forecast_end_date}</TableCell>
                      <TableCell>{formatDateTime(run.completed_at)}</TableCell>
                      <TableCell align="right">{run.prediction_rows.toLocaleString()}</TableCell>
                    </TableRow>
                  ))}
                  {!loading && runs.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={6} align="center">No forecast runs found.</TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          )}

          {tab === 2 && (
            <TableContainer sx={{ maxHeight: '65vh' }}>
              <Table stickyHeader size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Site</TableCell>
                    <TableCell>Country</TableCell>
                    <TableCell align="right">Altitude</TableCell>
                    <TableCell>GFS point</TableCell>
                    <TableCell>Tags</TableCell>
                    <TableCell>Latest forecast</TableCell>
                    <TableCell align="right">Edit</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {sites.map((site) => (
                    <TableRow key={site.site_id} hover>
                      <TableCell>
                        <Link href={`/details/${site.site_id}`} target="_blank" rel="noreferrer">
                          {site.name}
                        </Link>
                      </TableCell>
                      <TableCell>{site.country || '—'}</TableCell>
                      <TableCell align="right">{site.altitude} m</TableCell>
                      <TableCell>{site.lat_gfs}, {site.lon_gfs}</TableCell>
                      <TableCell>
                        <Stack direction="row" spacing={0.5} useFlexGap flexWrap="wrap">
                          {(site.tags || []).slice(0, 4).map((tag) => (
                            <Chip key={tag} label={tag} size="small" variant="outlined" />
                          ))}
                          {(site.tags || []).length > 4 && (
                            <Chip label={`+${site.tags.length - 4}`} size="small" />
                          )}
                        </Stack>
                      </TableCell>
                      <TableCell>{formatDateTime(site.latest_gfs_forecast_at)}</TableCell>
                      <TableCell align="right">
                        <Tooltip title="Edit site">
                          <IconButton size="small" onClick={() => openSiteEditor(site)}>
                            <EditIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}

          {tab === 3 && (
            <Stack spacing={2}>
              <FormControlLabel
                control={(
                  <Switch
                    checked={missingResourcesOnly}
                    onChange={(event) => setMissingResourcesOnly(event.target.checked)}
                  />
                )}
                label="Show only sites without resources"
              />
              {resourceLoading && <LinearProgress />}
              <TableContainer sx={{ maxHeight: '65vh' }}>
                <Table stickyHeader size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Site</TableCell>
                      <TableCell>Validated resources</TableCell>
                      <TableCell>Webcams</TableCell>
                      <TableCell>Meteostations</TableCell>
                      <TableCell>Last extraction</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {(resources?.items || []).map((site) => (
                      <TableRow key={site.site_id} hover>
                        <TableCell>
                          <Link href={`/details/${site.site_id}`} target="_blank" rel="noreferrer">
                            {site.site_name}
                          </Link>
                        </TableCell>
                        <TableCell>
                          <Stack spacing={0.5}>
                            {site.resources.map((resource) => (
                              <Link
                                key={resource.candidate_id}
                                href={resource.url}
                                target="_blank"
                                rel="noreferrer"
                                sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}
                              >
                                {resource.name || resource.host || resource.url}
                                <OpenInNewIcon sx={{ fontSize: 14 }} />
                              </Link>
                            ))}
                            {site.resources.length === 0 && (
                              <Typography variant="body2" color="text.secondary">None</Typography>
                            )}
                          </Stack>
                        </TableCell>
                        <TableCell>{site.webcam_urls.length}</TableCell>
                        <TableCell>{site.meteostation_urls.length}</TableCell>
                        <TableCell>{formatDateTime(site.run_extracted_at)}</TableCell>
                      </TableRow>
                    ))}
                    {!resourceLoading && (resources?.items || []).length === 0 && (
                      <TableRow>
                        <TableCell colSpan={5} align="center">No matching sites found.</TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
              {resources && (
                <Typography variant="caption" color="text.secondary">
                  Showing {resources.items.length} of {resources.total} matching sites.
                </Typography>
              )}
            </Stack>
          )}
        </Box>
      </Paper>

      <Dialog
        open={Boolean(editingSite)}
        onClose={() => !savingSite && setEditingSite(null)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>Edit site</DialogTitle>
        <DialogContent dividers>
          {editingSite && (
            <Grid container spacing={2} sx={{ mt: 0 }}>
              <Grid item xs={12} md={8}>
                <TextField
                  label="Name"
                  value={editingSite.name}
                  onChange={updateEditingField('name')}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12} md={4}>
                <TextField
                  label="Country"
                  value={editingSite.country || ''}
                  onChange={updateEditingField('country')}
                  fullWidth
                />
              </Grid>
              {[
                ['latitude', 'Latitude'],
                ['longitude', 'Longitude'],
                ['altitude', 'Altitude (m)'],
                ['lat_gfs', 'GFS latitude'],
                ['lon_gfs', 'GFS longitude'],
              ].map(([field, label]) => (
                <Grid item xs={12} sm={6} md={field === 'altitude' ? 4 : 6} key={field}>
                  <TextField
                    label={label}
                    type="number"
                    value={editingSite[field]}
                    onChange={updateEditingField(field)}
                    fullWidth
                  />
                </Grid>
              ))}
              <Grid item xs={12}>
                <TextField
                  label="Tags"
                  helperText="Comma-separated"
                  value={editingSite.tagsText}
                  onChange={updateEditingField('tagsText')}
                  fullWidth
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  label="Site information HTML"
                  value={editingSite.html || ''}
                  onChange={updateEditingField('html')}
                  multiline
                  minRows={8}
                  fullWidth
                />
              </Grid>
            </Grid>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditingSite(null)} disabled={savingSite}>Cancel</Button>
          <Button variant="contained" onClick={handleSaveSite} disabled={savingSite}>
            {savingSite ? 'Saving…' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default Admin;
