import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { AppBar, Toolbar, Typography, Box } from '@mui/material';
import SearchBar from '../components/SearchBar';
import DisclaimerModal from '../components/DisclaimerModal';
import useDisclaimer from '../hooks/useDisclaimer';
import { fetchSites } from '../api';  // Make sure this import matches your API setup

const Layout = () => {
  // This state and function will be passed down to components that need it
  const [selectedSite, setSelectedSite] = useState(null);
  const [sites, setSites] = useState([]);
  const { showDisclaimer, handleAccept, handleDecline } = useDisclaimer();

  // Update these values
  const headerHeight = '64px';
  const footerHeight = '30px';

  useEffect(() => {
    document.documentElement.style.setProperty('--header-height', headerHeight);
    document.documentElement.style.setProperty('--footer-height', footerHeight);
  }, [headerHeight, footerHeight]);

  useEffect(() => {
    const loadSites = async () => {
      try {
        const sitesData = await fetchSites();
        setSites(sitesData);
      } catch (error) {
        console.error('Error loading sites:', error);
      }
    };

    loadSites();
  }, []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      {/* Disclaimer Modal */}
      <DisclaimerModal 
        open={showDisclaimer} 
        onAccept={handleAccept} 
        onDecline={handleDecline} 
      />
      
      {/* Top Navigation Bar */}
      <AppBar
        position="static"
        sx={{
          backgroundColor: '#424242',
          zIndex: (theme) => theme.zIndex.drawer + 1,
          height: headerHeight,
        }}
      >
        <Toolbar>
          <Typography
            variant="h6"
            component="a"
            href="/"
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
          <SearchBar 
            sites={sites}  // Pass the actual sites data
            onSiteSelect={setSelectedSite}
          />
        </Toolbar>
      </AppBar>

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          height: `calc(100vh - ${headerHeight} - ${footerHeight})`,
          overflow: 'auto',
          backgroundColor: '#f5f5f5',
          padding: 0,
        }}
      >
        {/* This is where child routes will be rendered */}
        <Outlet context={{ selectedSite, setSelectedSite }} />
      </Box>

      {/* Bottom Footer Bar */}
      <AppBar
        position="static"
        sx={{
          backgroundColor: '#424242',
          height: footerHeight,
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
            © {new Date().getFullYear()} Parra-Glideator
          </Typography>
        </Toolbar>
      </AppBar>
    </div>
  );
};

export default Layout;
