import React from 'react';
import { Link, Outlet } from 'react-router-dom';
import { AppBar, Toolbar, Typography, Box } from '@mui/material';

const Layout = () => {
  return (
    <div>
      {/* Top Navigation Bar */}
      <AppBar
        position="fixed"
        sx={{
          backgroundColor: '#424242',
        }}
      >
        <Toolbar>
          <Typography
            variant="h6"
            component={Link}
            to="/"
            sx={{
              color: 'white',
              textDecoration: 'none',
              '&:hover': {
                color: 'black',
              },
            }}
          >
            Home
          </Typography>
        </Toolbar>
      </AppBar>

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          padding: '2rem',
          minHeight: '80vh',
          paddingTop: '64px',
        }}
      >
        {/* This is where child routes will be rendered */}
        <Outlet />
      </Box>

      {/* Bottom Footer Bar */}
      <AppBar
        position="fixed"
        sx={{
          backgroundColor: '#424242',
          height: '40px',
          top: 'auto',
          bottom: 0,
        }}
      >
        <Toolbar variant="dense">
          {/* Footer is currently empty */}
        </Toolbar>
      </AppBar>
    </div>
  );
};

export default Layout;
