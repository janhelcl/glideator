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
import { Link as RouterLink, useLocation, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { useAuth } from '../context/AuthContext';

const Login = () => {
  const { login, isAuthenticated, isLoading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const from = location.state?.from?.pathname || '/';

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(form.email, form.password);
      navigate(from, { replace: true });
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Login failed. Please check your credentials.';
      setError(Array.isArray(detail) ? detail.join(', ') : detail);
    } finally {
      setSubmitting(false);
    }
  };

  if (isAuthenticated && !isLoading) {
    navigate('/');
  }

  return (
    <Box sx={{ maxWidth: '500px', margin: '0 auto', p: 2, minHeight: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
      <Helmet>
        <title>Log In – Parra-Glideator</title>
        <meta name="description" content="Log in to your Parra-Glideator account to access favorites, notifications, and personalized features." />
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
                Log In
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Welcome back to Parra-Glideator
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
              autoComplete="current-password"
            />
            <Button
              type="submit"
              variant="contained"
              color="primary"
              fullWidth
              disabled={submitting}
              sx={{ mt: 1 }}
            >
              {submitting ? 'Logging in…' : 'Log In'}
            </Button>
          </Box>

          <Typography variant="body2" sx={{ mt: 3, textAlign: 'center' }}>
            Don&rsquo;t have an account?{' '}
            <Link component={RouterLink} to="/register">
              Create one
            </Link>
          </Typography>
        </Box>
      </Paper>
    </Box>
  );
};

export default Login;

