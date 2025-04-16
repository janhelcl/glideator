import React from 'react';
import { Link } from 'react-router-dom';
import { Box, Typography, Button, Container, Paper } from '@mui/material';

const NotFound = () => {
  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          py: { xs: 2, sm: 4 },
        }}
      >
        <Paper
          elevation={3}
          sx={{
            p: { xs: 2, sm: 4 },
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: { xs: 2, sm: 3 },
            width: '100%',
          }}
        >
          <Box
            component="img"
            src="/assets/images/404.png"
            alt="404 Not Found"
            sx={{
              width: '100%',
              maxWidth: { xs: '200px', sm: '300px' },
              height: 'auto',
              mb: 2,
            }}
          />
          <Typography 
            variant="h4" 
            component="h1" 
            gutterBottom 
            align="center" 
            sx={{ 
              color: 'black', 
              fontSize: { xs: '1.75rem', sm: '2.125rem' }
            }}
          >
            404 - Page Not Found
          </Typography>
          <Typography 
            variant="body1" 
            align="center" 
            color="text.secondary" 
            sx={{ 
              mb: { xs: 2, sm: 3 }
            }}
          >
            The page you're looking for doesn't exist or has been moved.
          </Typography>
          <Button
            component={Link}
            to="/"
            variant="contained"
            color="primary"
            size="large"
            sx={{
              minWidth: { xs: '160px', sm: '200px' },
            }}
          >
            Return to Home
          </Button>
        </Paper>
      </Box>
    </Container>
  );
};

export default NotFound; 