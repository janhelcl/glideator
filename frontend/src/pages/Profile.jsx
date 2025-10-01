import React, { useEffect, useState } from 'react';
import {
  Box,
  Button,
  Paper,
  TextField,
  Typography,
  Alert,
  IconButton,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import MyLocationIcon from '@mui/icons-material/MyLocation';
import { useAuth } from '../context/AuthContext';
import { Helmet } from 'react-helmet-async';
import StandaloneMetricControl from '../components/StandaloneMetricControl';
import { AVAILABLE_METRICS } from '../types/ui-state';
import LoadingSpinner from '../components/LoadingSpinner';

const Profile = () => {
  const { profile, user, saveProfile, isLoading } = useAuth();
  const [form, setForm] = useState({
    display_name: '',
    home_lat: '',
    home_lon: '',
    preferred_metric: 'XC0',
  });
  const [status, setStatus] = useState({ type: null, message: null });
  const [submitting, setSubmitting] = useState(false);
  const [gettingLocation, setGettingLocation] = useState(false);

  useEffect(() => {
    if (profile) {
      setForm({
        display_name: profile.display_name || '',
        home_lat: profile.home_lat ?? '',
        home_lon: profile.home_lon ?? '',
        preferred_metric: profile.preferred_metric || 'XC0',
      });
    }
  }, [profile]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleMetricChange = (newMetric) => {
    setForm((prev) => ({ ...prev, preferred_metric: newMetric }));
  };

  const handleUseCurrentLocation = () => {
    if (!navigator.geolocation) {
      setStatus({ type: 'error', message: 'Geolocation is not supported by your browser' });
      return;
    }

    setGettingLocation(true);
    setStatus({ type: null, message: null });

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        setForm((prev) => ({
          ...prev,
          home_lat: latitude.toFixed(6),
          home_lon: longitude.toFixed(6),
        }));
        setStatus({ type: 'success', message: 'Location set successfully!' });
        setGettingLocation(false);
      },
      (error) => {
        let errorMessage = 'Unable to get location';
        switch (error.code) {
          case error.PERMISSION_DENIED:
            errorMessage = 'Location access denied. Please enable location permissions in your browser.';
            break;
          case error.POSITION_UNAVAILABLE:
            errorMessage = 'Location information is unavailable.';
            break;
          case error.TIMEOUT:
            errorMessage = 'Location request timed out.';
            break;
          default:
            errorMessage = 'An unknown error occurred while getting location.';
            break;
        }
        setStatus({ type: 'error', message: errorMessage });
        setGettingLocation(false);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0, // Don't use cached position
      }
    );
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setStatus({ type: null, message: null });
    setSubmitting(true);
    try {
      const payload = {
        display_name: form.display_name || null,
        home_lat: form.home_lat === '' ? null : Number(form.home_lat),
        home_lon: form.home_lon === '' ? null : Number(form.home_lon),
        preferred_metric: form.preferred_metric,
      };
      await saveProfile(payload);
      setStatus({ type: 'success', message: 'Profile updated successfully.' });
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to update profile.';
      setStatus({ type: 'error', message: Array.isArray(detail) ? detail.join(', ') : detail });
    } finally {
      setSubmitting(false);
    }
  };

  if (isLoading) {
    return <LoadingSpinner />;
  }

  return (
    <Box
      sx={{
        maxWidth: '1200px',
        margin: '0 auto',
        p: 2,
        minHeight: '100%',
      }}
    >
      <Helmet>
        <title>Profile – Parra-Glideator</title>
        <meta
          name="description"
          content="Manage your Parra-Glideator profile, home coordinates, and preferred metrics."
        />
      </Helmet>
      <Paper elevation={2}>
        <Box sx={{ p: { xs: 2, sm: 3 } }}>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              pb: 2,
              mb: 3,
              borderBottom: 1,
              borderColor: 'divider',
            }}
          >
            <Box>
              <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold', mb: 0.5 }}>
                Profile
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {user?.email ? `Logged in as ${user.email}` : 'Manage your profile information'}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <img
                src={`${process.env.PUBLIC_URL || ''}/logo192.png`}
                alt="Glideator Logo"
                style={{ height: 56, width: 'auto' }}
              />
            </Box>
          </Box>

          <Box sx={{ maxWidth: '700px', mx: 'auto' }}>
            {status.type && (
              <Alert severity={status.type} sx={{ mb: 2 }}>
                {status.message}
              </Alert>
            )}

            <Box
              component="form"
              onSubmit={handleSubmit}
              sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}
            >
            <TextField
              fullWidth
              label="Display Name"
              name="display_name"
              value={form.display_name}
              onChange={handleChange}
            />
            
            <Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                <Typography variant="body2" color="text.secondary">
                  Home Location
                </Typography>
                <Tooltip title="Use my current location">
                  <span>
                    <IconButton
                      onClick={handleUseCurrentLocation}
                      disabled={gettingLocation}
                      size="small"
                      color="primary"
                    >
                      {gettingLocation ? (
                        <CircularProgress size={20} />
                      ) : (
                        <MyLocationIcon />
                      )}
                    </IconButton>
                  </span>
                </Tooltip>
              </Box>
              <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, gap: 2 }}>
                <TextField
                  fullWidth
                  label="Home Latitude"
                  name="home_lat"
                  type="number"
                  value={form.home_lat}
                  onChange={handleChange}
                  inputProps={{ step: 'any' }}
                />
                <TextField
                  fullWidth
                  label="Home Longitude"
                  name="home_lon"
                  type="number"
                  value={form.home_lon}
                  onChange={handleChange}
                  inputProps={{ step: 'any' }}
                />
              </Box>
            </Box>
            
            <Box>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                <Typography variant="body2" color="text.secondary">
                  Preferred Flight Quality Metric
                </Typography>
                <StandaloneMetricControl
                  metrics={AVAILABLE_METRICS}
                  selectedMetric={form.preferred_metric}
                  onMetricChange={handleMetricChange}
                />
              </Box>
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                Currently selected: <strong>{form.preferred_metric}</strong> (minimum {form.preferred_metric.replace('XC', '')} XC points)
              </Typography>
            </Box>
            
            <Button
              type="submit"
              variant="contained"
              color="primary"
              fullWidth
              sx={{ mt: 1 }}
              disabled={submitting}
            >
              {submitting ? 'Saving…' : 'Save Profile'}
            </Button>
            </Box>
          </Box>
        </Box>
      </Paper>
    </Box>
  );
};

export default Profile;

