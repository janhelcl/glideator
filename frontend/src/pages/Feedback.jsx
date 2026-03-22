import React, { useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Container,
  Paper,
  TextField,
  Typography,
} from '@mui/material';
import { Helmet } from 'react-helmet-async';

import { submitFeedback } from '../api';
import { useAuth } from '../context/AuthContext';

const MAX_MESSAGE_LEN = 10000;

const Feedback = () => {
  const { user } = useAuth();
  const [message, setMessage] = useState('');
  const [status, setStatus] = useState({ type: null, message: null });
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setStatus({ type: null, message: null });
    const trimmed = message.trim();
    if (!trimmed) {
      setStatus({ type: 'error', message: 'Please enter a message.' });
      return;
    }
    setSubmitting(true);
    try {
      await submitFeedback(trimmed);
      setStatus({ type: 'success', message: 'Thanks — your message was sent.' });
      setMessage('');
    } catch (err) {
      const detail = err?.response?.data?.detail;
      let msg = 'Could not send your message. Please try again later.';
      if (typeof detail === 'string') {
        msg = detail;
      } else if (Array.isArray(detail)) {
        msg = detail.map((d) => d.msg || JSON.stringify(d)).join(' ');
      }
      setStatus({ type: 'error', message: msg });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Container maxWidth="sm" sx={{ py: { xs: 2, sm: 4 } }}>
      <Helmet>
        <title>Feedback – Parra-Glideator</title>
        <meta
          name="description"
          content="Sign in to send feedback, report bugs, or suggest improvements for Parra-Glideator."
        />
      </Helmet>
      <Paper elevation={2}>
        <Box sx={{ p: { xs: 2.5, sm: 4 }, display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              pb: 2,
              mb: 1,
              borderBottom: 1,
              borderColor: 'divider',
            }}
          >
            <Box>
              <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold' }}>
                Feedback
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

          <Typography variant="body1" color="text.secondary" sx={{ mb: 0 }}>
            Wrong data, feature ideas, and anything else you want us to know are welcome. Your
            message is stored securely for the team to review. You are sending as{' '}
            <Box component="span" sx={{ fontWeight: 600, color: 'text.primary' }}>
              {user?.email || 'your account'}
            </Box>
            .
          </Typography>

          {status.type && (
            <Alert
              severity={status.type}
              onClose={() => setStatus({ type: null, message: null })}
            >
              {status.message}
            </Alert>
          )}

          <Box
            component="form"
            onSubmit={handleSubmit}
            sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 0.5 }}
          >
            <TextField
              required
              fullWidth
              multiline
              minRows={6}
              label="Message"
              name="message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              inputProps={{ maxLength: MAX_MESSAGE_LEN }}
              helperText={`${message.length} / ${MAX_MESSAGE_LEN}`}
            />
            <Box>
              <Button type="submit" variant="contained" color="primary" size="large" disabled={submitting}>
                {submitting ? 'Sending…' : 'Send message'}
              </Button>
            </Box>
          </Box>
        </Box>
      </Paper>
    </Container>
  );
};

export default Feedback;
