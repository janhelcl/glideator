import React from 'react';
import { Box, Typography, Button, Container, Paper } from '@mui/material';
import { useNavigate } from 'react-router-dom';

const Declined = () => {
  const navigate = useNavigate();

  const handleReload = () => {
    // Remove the localStorage item to make the disclaimer show again
    localStorage.removeItem('disclaimerAccepted');
    // Navigate back to the home page
    navigate('/');
  };

  return (
    <Container maxWidth="md" sx={{ mt: 5 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Box textAlign="center">
          <Typography variant="h4" component="h1" gutterBottom>
            Access Restricted
          </Typography>
          <Typography variant="body1" paragraph>
            You must accept the disclaimer to access this application.
          </Typography>
          <Typography variant="body1" paragraph>
            This application provides forecasts and data that should be used at your own risk.
            We require all users to acknowledge this before proceeding.
          </Typography>
          <Button 
            variant="contained" 
            color="primary" 
            onClick={handleReload}
            sx={{ mt: 2 }}
          >
            Return to Disclaimer
          </Button>
        </Box>
      </Paper>
    </Container>
  );
};

export default Declined; 