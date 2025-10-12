import React from 'react';
import { Box, Paper, Typography } from '@mui/material';
import { Helmet } from 'react-helmet-async';

import NotificationManager from '../components/NotificationManager';
import { useAuth } from '../context/AuthContext';

const NotificationsPage = () => {
  const { profile, user } = useAuth();
  const defaultMetric = profile?.preferred_metric || 'XC0';
  const identityLabel = profile?.display_name || user?.email || undefined;

  return (
    <Box sx={{ maxWidth: '1200px', margin: '0 auto', p: 2, minHeight: '100%' }}>
      <Helmet>
        <title>Notifications – Parra-Glideator</title>
        <meta
          name="description"
          content="Manage your Glideator push devices and notification rules."
        />
      </Helmet>

      <Paper elevation={2}>
        <Box sx={{ p: { xs: 2, sm: 3 } }}>
          <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold', mb: 2 }}>
            Notifications
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Register your devices and create rules to receive push alerts when forecast
            metrics meet your criteria.
          </Typography>
          <NotificationManager defaultMetric={defaultMetric} identityLabel={identityLabel} />
        </Box>
      </Paper>
    </Box>
  );
};

export default NotificationsPage;
