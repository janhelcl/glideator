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
import { fetchAdminMcpAnalytics } from '../../adminApi';

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

const AdminMcpAnalyticsPanel = () => {
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setData(await fetchAdminMcpAnalytics(days));
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load MCP analytics.');
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
          <Typography variant="h5" sx={{ fontWeight: 700 }}>MCP usage</Typography>
          <Typography variant="body2" color="text.secondary">
            Privacy-minimal tool-call analytics. Arguments, prompts, IP addresses and raw client metadata are not stored.
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
              <MetricCard
                label="Tool calls"
                value={data.total_calls.toLocaleString()}
                detail={`${data.window_days}-day window`}
              />
            </Grid>
            <Grid item xs={12} sm={6} lg={3}>
              <MetricCard
                label="Success rate"
                value={`${data.success_rate}%`}
                detail={`${data.failed_calls.toLocaleString()} failed calls`}
              />
            </Grid>
            <Grid item xs={12} sm={6} lg={3}>
              <MetricCard
                label="Average duration"
                value={`${data.avg_duration_ms.toLocaleString()} ms`}
                detail="End-to-end tool execution"
              />
            </Grid>
            <Grid item xs={12} sm={6} lg={3}>
              <MetricCard
                label="Tools used"
                value={data.tools_used}
                detail="Distinct MCP tools called"
              />
            </Grid>
          </Grid>

          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Tool</TableCell>
                  <TableCell align="right">Calls</TableCell>
                  <TableCell align="right">Success</TableCell>
                  <TableCell align="right">Failed</TableCell>
                  <TableCell align="right">Success rate</TableCell>
                  <TableCell align="right">Avg duration</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.tools.map((row) => (
                  <TableRow key={row.tool_name} hover>
                    <TableCell>{row.tool_name}</TableCell>
                    <TableCell align="right">{row.calls.toLocaleString()}</TableCell>
                    <TableCell align="right">{row.successful_calls.toLocaleString()}</TableCell>
                    <TableCell align="right">{row.failed_calls.toLocaleString()}</TableCell>
                    <TableCell align="right">{row.success_rate}%</TableCell>
                    <TableCell align="right">{row.avg_duration_ms.toLocaleString()} ms</TableCell>
                  </TableRow>
                ))}
                {data.tools.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} align="center">No MCP tool calls captured in this period.</TableCell>
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

export default AdminMcpAnalyticsPanel;
