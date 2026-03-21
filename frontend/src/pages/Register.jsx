import React, { useState } from 'react';
import {
  Box,
  Button,
  Paper,
  TextField,
  Typography,
  Alert,
  Link,
} from '@mui/material';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { useAuth } from '../context/AuthContext';

const passwordHint = 'Must be at least 8 characters and include three of: upper, lower, number, special.';

const Register = () => {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: '', password: '', confirmPassword: '' });
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);

    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setSubmitting(true);
    try {
      await register(form.email, form.password);
      navigate('/', { replace: true });
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Registration failed. Please try again.';
      setError(Array.isArray(detail) ? detail.join(', ') : detail);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Box sx={{ maxWidth: '500px', margin: '0 auto', p: 2, minHeight: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <Helmet>
        <title>Create Account – Parra-Glideator</title>
        <meta name="description" content="Create a free Parra-Glideator account to save favorite sites, set up notifications, and get personalized recommendations." />
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
                Create Account
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Join Parra-Glideator for free
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

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit} noValidate sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              fullWidth
              required
              label="Email"
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              autoComplete="email"
            />
            <TextField
              fullWidth
              required
              label="Password"
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              helperText={passwordHint}
              autoComplete="new-password"
            />
            <TextField
              fullWidth
              required
              label="Confirm Password"
              type="password"
              name="confirmPassword"
              value={form.confirmPassword}
              onChange={handleChange}
              autoComplete="new-password"
            />
            <Button
              type="submit"
              variant="contained"
              color="primary"
              fullWidth
              disabled={submitting}
              sx={{ mt: 1 }}
            >
              {submitting ? 'Creating account…' : 'Create Account'}
            </Button>
          </Box>

          <Typography variant="body2" sx={{ mt: 3, textAlign: 'center' }}>
            Already have an account?{' '}
            <Link component={RouterLink} to="/login">
              Log in
            </Link>
          </Typography>
        </Box>
      </Paper>
    </Box>
  );
};

export default Register;

