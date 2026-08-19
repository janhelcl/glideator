import React, { useCallback, useEffect, useState } from 'react';
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
import { fetchAdminBotAnalytics } from '../../adminApi';

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

const AdminBotAnalyticsPanel = () => {
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setData(await fetchAdminBotAnalytics(days));
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load bot analytics.');
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
          <Typography variant="h5" sx={{ fontWeight: 700 }}>Bot traffic</Typography>
          <Typography variant="body2" color="text.secondary">
            Known crawlers detected from the request User-Agent. Only the canonical bot name is stored; the raw User-Agent is not retained.
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
              <MetricCard label="Bot events" value={data.total_events.toLocaleString()} detail={`${data.window_days}-day window`} />
            </Grid>
            <Grid item xs={12} sm={6} lg={3}>
              <MetricCard label="Bot sessions" value={data.unique_sessions.toLocaleString()} detail={`${data.unique_visitors.toLocaleString()} anonymous visitor IDs`} />
            </Grid>
            <Grid item xs={12} sm={6} lg={3}>
              <MetricCard label="Bot types" value={data.bot_types} detail="Distinct known crawler identities" />
            </Grid>
          </Grid>

          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Bot</TableCell>
                  <TableCell align="right">Events</TableCell>
                  <TableCell align="right">Sessions</TableCell>
                  <TableCell align="right">Visitor IDs</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.bots.map((row) => (
                  <TableRow key={row.bot_name} hover>
                    <TableCell>{row.bot_name}</TableCell>
                    <TableCell align="right">{row.events.toLocaleString()}</TableCell>
                    <TableCell align="right">{row.sessions.toLocaleString()}</TableCell>
                    <TableCell align="right">{row.visitors.toLocaleString()}</TableCell>
                  </TableRow>
                ))}
                {data.bots.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={4} align="center">No known bot traffic captured in this period.</TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </>
      )}
    </Stack>
  );
};

export default AdminBotAnalyticsPanel;
