import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { 
  AppBar, 
  Toolbar, 
  Typography, 
  Box, 
  Button, 
  IconButton, 
  Menu, 
  MenuItem, 
  Drawer, 
  List, 
  ListItem, 
  ListItemText,
  useMediaQuery,
  useTheme,
  Divider,
  ListItemButton
} from '@mui/material';
import AccountCircle from '@mui/icons-material/AccountCircle';
import MenuIcon from '@mui/icons-material/Menu';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import SearchBar from '../components/SearchBar';
import DisclaimerModal from '../components/DisclaimerModal';
import MissedNotificationsBanner from '../components/MissedNotificationsBanner';
import useDisclaimer from '../hooks/useDisclaimer';
import { fetchSitesList } from '../api';  // Reverted back to fetchSitesList
import { useAuth } from '../context/AuthContext';

const Layout = () => {
  // This state and function will be passed down to components that need it
  const [selectedSite, setSelectedSite] = useState(null);
  const [sites, setSites] = useState([]);
  const { showDisclaimer, handleAccept, handleDecline } = useDisclaimer();
  const { isAuthenticated, logout, user, profile } = useAuth();
  const [anchorEl, setAnchorEl] = useState(null);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const navigate = useNavigate();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  // Update these values - make header taller on mobile for better touch targets
  const headerHeight = isMobile ? '56px' : '64px';
  const footerHeight = '30px';

  useEffect(() => {
    document.documentElement.style.setProperty('--header-height', headerHeight);
    document.documentElement.style.setProperty('--footer-height', footerHeight);
  }, [headerHeight, footerHeight]);

  useEffect(() => {
    const loadSites = async () => {
      try {
        const sitesData = await fetchSitesList();
        setSites(sitesData);
      } catch (error) {
        console.error('Error loading sites:', error);
      }
    };

    loadSites();
  }, []);

  const handleMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = async () => {
    await logout();
    handleMenuClose();
    navigate('/');
  };

  const handleMobileDrawerToggle = () => {
    setMobileDrawerOpen(!mobileDrawerOpen);
  };

  const handleMobileMenuClick = (path) => {
    navigate(path);
    setMobileDrawerOpen(false);
  };

  const handleMobileLogout = async () => {
    await logout();
    setMobileDrawerOpen(false);
    navigate('/');
  };

  const displayLabel = profile?.display_name || user?.email;

  // Mobile drawer content
  const mobileDrawerContent = (
    <Box sx={{ width: 280, pt: 2 }}>
      <List>
        <ListItem>
          <Typography variant="h6" sx={{ fontWeight: 'bold', color: '#424242' }}>
            Parra-Glideator
          </Typography>
        </ListItem>
        <Divider sx={{ my: 1 }} />
        
        <ListItemButton onClick={() => handleMobileMenuClick('/')}>
          <ListItemText primary="Home" />
        </ListItemButton>
        
        <ListItemButton onClick={() => handleMobileMenuClick('/trip-planner')}>
          <ListItemText primary="Plan a Trip" />
        </ListItemButton>
        
        <Divider sx={{ my: 1 }} />
        
        {/* Search Bar in Mobile Drawer */}
        <ListItem sx={{ px: 2, py: 1 }}>
          <Box sx={{ width: '100%' }}>
            <SearchBar 
              sites={sites}
              onSiteSelect={(site) => {
                setSelectedSite(site);
                setMobileDrawerOpen(false);
              }}
              mobile={true}
            />
          </Box>
        </ListItem>
        
        <Divider sx={{ my: 1 }} />
        
        {isAuthenticated ? (
          <>
            <ListItemButton onClick={() => handleMobileMenuClick('/favorites')}>
              <ListItemText primary="Favorites" />
            </ListItemButton>
            <ListItemButton onClick={() => handleMobileMenuClick('/notifications')}>
              <ListItemText primary="Notifications" />
            </ListItemButton>
            <ListItemButton onClick={() => handleMobileMenuClick('/profile')}>
              <ListItemText primary="Profile" />
            </ListItemButton>
            <ListItemButton onClick={handleMobileLogout}>
              <ListItemText primary="Logout" />
            </ListItemButton>
          </>
        ) : (
          <>
            <ListItemButton onClick={() => handleMobileMenuClick('/login')}>
              <ListItemText primary="Log In" />
            </ListItemButton>
            <ListItemButton onClick={() => handleMobileMenuClick('/register')}>
              <ListItemText primary="Register" />
            </ListItemButton>
          </>
        )}
      </List>
    </Box>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      {/* Disclaimer Modal */}
      <DisclaimerModal 
        open={showDisclaimer} 
        onAccept={handleAccept} 
        onDecline={handleDecline} 
      />

      {/* Mobile Navigation Drawer */}
      <Drawer
        anchor="left"
        open={mobileDrawerOpen}
        onClose={() => setMobileDrawerOpen(false)}
        sx={{ display: { xs: 'block', md: 'none' } }}
      >
        {mobileDrawerContent}
      </Drawer>
      
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
          {/* Mobile: Show hamburger menu */}
          {isMobile && (
            <IconButton
              color="inherit"
              aria-label="open drawer"
              edge="start"
              onClick={handleMobileDrawerToggle}
              sx={{ mr: 2 }}
            >
              <MenuIcon />
            </IconButton>
          )}
          
          {/* Logo/Home button - always visible */}
          <Button
            component={RouterLink}
            to="/"
            sx={{
              color: 'white',
              fontSize: isMobile ? '0.9rem' : '1rem',
              minWidth: 'auto',
              px: isMobile ? 1 : 2,
              '&:hover': {
                backgroundColor: 'rgba(255,255,255,0.1)',
              },
            }}
          >
            Home
          </Button>
          
          {/* Desktop navigation */}
          {!isMobile && (
            <>
              <Button
                component={RouterLink}
                to="/trip-planner"
                sx={{
                  color: 'white',
                  ml: 2,
                  '&:hover': {
                    backgroundColor: 'rgba(255,255,255,0.1)',
                  },
                }}
              >
                Plan a Trip
              </Button>
              
              <SearchBar 
                sites={sites}
                onSiteSelect={setSelectedSite}
              />
            </>
          )}

          <Box sx={{ flexGrow: 1 }} />

          {/* Desktop authentication menu */}
          {!isMobile && (
            <>
              {isAuthenticated ? (
                <>
                  <Button
                    component={RouterLink}
                    to="/favorites"
                    sx={{ color: 'white', mr: 1 }}
                  >
                    Favorites
                  </Button>
                  <Button
                    component={RouterLink}
                    to="/notifications"
                    sx={{ color: 'white', mr: 1 }}
                  >
                    Notifications
                  </Button>
                  <IconButton color="inherit" onClick={handleMenuOpen} size="large">
                    <AccountCircle />
                  </IconButton>
                  <Menu
                    anchorEl={anchorEl}
                    open={Boolean(anchorEl)}
                    onClose={handleMenuClose}
                  >
                  <MenuItem disabled>{displayLabel}</MenuItem>
                    <MenuItem component={RouterLink} to="/profile" onClick={handleMenuClose}>
                      Profile
                    </MenuItem>
                    <MenuItem component={RouterLink} to="/notifications" onClick={handleMenuClose}>
                      Notifications
                    </MenuItem>
                    <MenuItem onClick={handleLogout}>Logout</MenuItem>
                  </Menu>
                </>
              ) : (
                <>
                  <Button
                    component={RouterLink}
                    to="/login"
                    sx={{ color: 'white', ml: 2 }}
                  >
                    Log In
                  </Button>
                  <Button
                    component={RouterLink}
                    to="/register"
                    sx={{ color: 'white', ml: 1, border: '1px solid white' }}
                  >
                    Register
                  </Button>
                </>
              )}
            </>
          )}

          {/* Mobile: Show user icon if authenticated, nothing if not */}
          {isMobile && isAuthenticated && (
            <IconButton color="inherit" onClick={handleMenuOpen} size="large">
              <AccountCircle />
            </IconButton>
          )}
          
          {/* Mobile menu for authenticated users */}
          {isMobile && (
            <Menu
              anchorEl={anchorEl}
              open={Boolean(anchorEl)}
              onClose={handleMenuClose}
            >
              <MenuItem disabled>{displayLabel}</MenuItem>
              <MenuItem component={RouterLink} to="/profile" onClick={handleMenuClose}>
                Profile
              </MenuItem>
              <MenuItem component={RouterLink} to="/notifications" onClick={handleMenuClose}>
                Notifications
              </MenuItem>
              <MenuItem onClick={handleLogout}>Logout</MenuItem>
            </Menu>
          )}
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
          // Ensure proper touch scrolling on mobile
          WebkitOverflowScrolling: 'touch',
        }}
      >
        {/* This is where child routes will be rendered */}
        <Outlet context={{ selectedSite, setSelectedSite }} />
      </Box>

      {/* Missed notifications drawer - shows when app opens after being offline */}
      <MissedNotificationsBanner />

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
          sx={{ 
            minHeight: '30px',
            px: isMobile ? 1 : 2,
          }}
        >
          <Typography
            variant={isMobile ? "caption" : "body2"}
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
