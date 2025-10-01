import React, { useEffect, useState } from 'react';
import {
  Box,
  Button,
  Paper,
  TextField,
  Typography,
  Alert,
} from '@mui/material';
import { useAuth } from '../context/AuthContext';
import { Helmet } from 'react-helmet-async';

const Profile = () => {
  const { profile, user, saveProfile } = useAuth();
  const [form, setForm] = useState({
    display_name: '',
    home_lat: '',
    home_lon: '',
    preferred_metric: 'XC0',
  });
  const [status, setStatus] = useState({ type: null, message: null });
  const [submitting, setSubmitting] = useState(false);

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
            <TextField
              fullWidth
              label="Preferred Metric"
              name="preferred_metric"
              value={form.preferred_metric}
              onChange={handleChange}
              helperText="e.g., XC0, XC50"
            />
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
      </Paper>
    </Box>
  );
};

export default Profile;

