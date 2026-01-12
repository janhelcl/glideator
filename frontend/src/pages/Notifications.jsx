import React from 'react';
import { Box, Paper, Tab, Tabs, Typography } from '@mui/material';
import { Helmet } from 'react-helmet-async';
import { useSearchParams } from 'react-router-dom';
import HistoryIcon from '@mui/icons-material/History';
import SettingsIcon from '@mui/icons-material/Settings';

import NotificationManager from '../components/NotificationManager';
import NotificationHistory from '../components/NotificationHistory';
import { useAuth } from '../context/AuthContext';

const NotificationsPage = () => {
  const { profile, user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const defaultMetric = profile?.preferred_metric || 'XC0';
  const identityLabel = profile?.display_name || user?.email || undefined;

  const activeTab = searchParams.get('tab') || 'history';

  const handleTabChange = (event, newValue) => {
    setSearchParams({ tab: newValue });
  };

  return (
    <Box sx={{ maxWidth: '1200px', margin: '0 auto', p: 2, minHeight: '100%' }}>
      <Helmet>
        <title>Notifications – Parra-Glideator</title>
        <meta
          name="description"
          content="View notification history and manage your Glideator notification settings."
        />
      </Helmet>

      <Paper elevation={2}>
        <Box sx={{ p: { xs: 2, sm: 3 } }}>
          {/* Header */}
          <Box
            sx={{
              p: 2,
              borderBottom: 1,
              borderColor: 'divider',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold' }}>
              Notifications
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <img
                src="/logo192.png"
                alt="Glideator Logo"
                style={{ height: '60px', width: 'auto' }}
              />
            </Box>
          </Box>

          {/* Tabs */}
          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            sx={{
              borderBottom: 1,
              borderColor: 'divider',
              mb: 3,
              '& .MuiTab-root': {
                textTransform: 'none',
                minHeight: 48,
              },
            }}
          >
            <Tab
              value="history"
              label="History"
              icon={<HistoryIcon />}
              iconPosition="start"
            />
            <Tab
              value="settings"
              label="Settings"
              icon={<SettingsIcon />}
              iconPosition="start"
            />
          </Tabs>

          {/* Tab Content */}
          {activeTab === 'history' && <NotificationHistory />}
          {activeTab === 'settings' && (
            <>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Register your devices and create rules to receive push alerts when forecast
                metrics meet your criteria.
              </Typography>
              <NotificationManager defaultMetric={defaultMetric} identityLabel={identityLabel} />
            </>
          )}
        </Box>
      </Paper>
    </Box>
  );
};

export default NotificationsPage;
