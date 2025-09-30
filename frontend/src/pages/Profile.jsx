import React, { useEffect, useState } from 'react';
import {
  Box,
  Button,
  Container,
  TextField,
  Typography,
  Alert,
} from '@mui/material';
import { useAuth } from '../context/AuthContext';

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
    <Container maxWidth="sm" sx={{ mt: 8 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Profile
      </Typography>
      {status.type && (
        <Alert severity={status.type} sx={{ mb: 2 }}>
          {status.message}
        </Alert>
      )}
      <Typography variant="body1" sx={{ mb: 2 }}>
        Logged in as {user?.email}
      </Typography>
      <Box component="form" onSubmit={handleSubmit}>
        <TextField
          fullWidth
          margin="normal"
          label="Display Name"
          name="display_name"
          value={form.display_name}
          onChange={handleChange}
        />
        <Box sx={{ display: 'flex', gap: 2 }}>
          <TextField
            fullWidth
            margin="normal"
            label="Home Latitude"
            name="home_lat"
            type="number"
            value={form.home_lat}
            onChange={handleChange}
            inputProps={{ step: 'any' }}
          />
          <TextField
            fullWidth
            margin="normal"
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
          margin="normal"
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
          sx={{ mt: 2 }}
          disabled={submitting}
        >
          {submitting ? 'Saving…' : 'Save Profile'}
        </Button>
      </Box>
    </Container>
  );
};

export default Profile;

