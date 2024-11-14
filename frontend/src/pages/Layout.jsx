import React from 'react';
import { Link, Outlet } from 'react-router-dom';
import { AppBar, Toolbar, Typography, Box } from '@mui/material';

const Layout = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {/* Top Navigation Bar */}
      <AppBar
        position="fixed"
        sx={{
          backgroundColor: '#424242',
          zIndex: (theme) => theme.zIndex.drawer + 1,
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
          flexGrow: 1,
          height: 'calc(100vh - 94px)',
          marginTop: '64px',
          marginBottom: '30px',
          backgroundColor: '#f5f5f5',
          padding: 0,
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
          height: '30px',
          top: 'auto',
          bottom: 0,
          zIndex: (theme) => theme.zIndex.drawer + 1,
        }}
      >
        <Toolbar 
          variant="dense"
          sx={{ minHeight: '30px' }}
        >
          <Typography
            variant="body2"
            color="white"
            align="center"
            component="div"
            sx={{ width: '100%' }}
          >
            © 2024 Glideator
          </Typography>
        </Toolbar>
      </AppBar>
    </div>
  );
};

export default Layout;
