import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { 
  AppBar, 
  Toolbar, 
  Typography, 
  Box, 
  IconButton, 
  Menu, 
  MenuItem, 
  Drawer, 
  List, 
  ListItem, 
  ListItemText,
  ListItemIcon,
  useMediaQuery,
  useTheme,
  Divider,
  ListItemButton,
  Tooltip,
} from '@mui/material';
import AccountCircle from '@mui/icons-material/AccountCircle';
import CloseIcon from '@mui/icons-material/Close';
import ExploreIcon from '@mui/icons-material/Explore';
import HomeIcon from '@mui/icons-material/Home';
import InfoIcon from '@mui/icons-material/Info';
import LogoutIcon from '@mui/icons-material/Logout';
import MenuIcon from '@mui/icons-material/Menu';
import FavoriteIcon from '@mui/icons-material/Favorite';
import PersonIcon from '@mui/icons-material/Person';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import SearchBar from '../components/SearchBar';
import DisclaimerModal from '../components/DisclaimerModal';
import NotificationDropdown from '../components/NotificationDropdown';
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
    <Box sx={{ width: 280 }}>
      {/* Header with logo and close button */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          px: 2,
          py: 1.5,
          borderBottom: 1,
          borderColor: 'divider',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <img src="/logo192.png" alt="Parra-Glideator" style={{ height: 28 }} />
          <Typography variant="h6" sx={{ fontWeight: 'bold', color: 'primary.main' }}>
            Parra-Glideator
          </Typography>
        </Box>
        <IconButton onClick={() => setMobileDrawerOpen(false)} size="small">
          <CloseIcon />
        </IconButton>
      </Box>

      {/* Search Bar */}
      <Box sx={{ px: 2, py: 1.5 }}>
        <SearchBar 
          sites={sites}
          onSiteSelect={(site) => {
            setSelectedSite(site);
            setMobileDrawerOpen(false);
          }}
          mobile={true}
        />
      </Box>

      <Divider />

      {/* Main Navigation */}
      <List sx={{ py: 1 }}>
        <ListItemButton onClick={() => handleMobileMenuClick('/')}>
          <ListItemIcon><HomeIcon /></ListItemIcon>
          <ListItemText primary="Home" />
        </ListItemButton>
        
        <ListItemButton onClick={() => handleMobileMenuClick('/trip-planner')}>
          <ListItemIcon><ExploreIcon /></ListItemIcon>
          <ListItemText primary="Plan a Trip" />
        </ListItemButton>

        <ListItemButton onClick={() => handleMobileMenuClick('/about')}>
          <ListItemIcon><InfoIcon /></ListItemIcon>
          <ListItemText primary="How It Works" />
        </ListItemButton>
      </List>

      <Divider />

      {/* User Section */}
      <List sx={{ py: 1 }}>
        {isAuthenticated ? (
          <>
            <ListItemButton onClick={() => handleMobileMenuClick('/favorites')}>
              <ListItemIcon><FavoriteIcon /></ListItemIcon>
              <ListItemText primary="Favorites" />
            </ListItemButton>
            <ListItemButton onClick={() => handleMobileMenuClick('/profile')}>
              <ListItemIcon><PersonIcon /></ListItemIcon>
              <ListItemText primary="Profile" />
            </ListItemButton>
          </>
        ) : (
          <>
            <ListItemButton onClick={() => handleMobileMenuClick('/login')}>
              <ListItemIcon><PersonIcon /></ListItemIcon>
              <ListItemText primary="Log In" />
            </ListItemButton>
            <ListItemButton onClick={() => handleMobileMenuClick('/register')}>
              <ListItemIcon><PersonIcon /></ListItemIcon>
              <ListItemText primary="Register" />
            </ListItemButton>
          </>
        )}
      </List>

      {/* Logout at bottom */}
      {isAuthenticated && (
        <>
          <Divider />
          <List sx={{ py: 1 }}>
            <ListItemButton onClick={handleMobileLogout}>
              <ListItemIcon><LogoutIcon /></ListItemIcon>
              <ListItemText primary="Log Out" />
            </ListItemButton>
          </List>
        </>
      )}
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
          {/* Mobile: Hamburger menu */}
          {isMobile && (
            <IconButton
              color="inherit"
              aria-label="open menu"
              edge="start"
              onClick={handleMobileDrawerToggle}
            >
              <MenuIcon />
            </IconButton>
          )}
          
          {/* Logo - links to home */}
          <Box
            component={RouterLink}
            to="/"
            sx={{
              display: 'flex',
              alignItems: 'center',
              textDecoration: 'none',
              ml: isMobile ? 1 : 0,
              '&:hover': { opacity: 0.9 },
            }}
          >
            <img
              src="/logo192.png"
              alt="Parra-Glideator"
              style={{ height: 32, marginRight: isMobile ? 0 : 8 }}
            />
            {!isMobile && (
              <Typography
                variant="h6"
                sx={{ color: 'white', fontWeight: 'bold' }}
              >
                Parra-Glideator
              </Typography>
            )}
          </Box>
          
          {/* Desktop: Search bar */}
          {!isMobile && (
            <Box sx={{ ml: 3, flexGrow: 1, maxWidth: 400 }}>
              <SearchBar 
                sites={sites}
                onSiteSelect={setSelectedSite}
              />
            </Box>
          )}

          <Box sx={{ flexGrow: 1 }} />

          {/* Right side icons */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            {/* Desktop: Plan a Trip */}
            {!isMobile && (
              <Tooltip title="Plan a Trip">
                <IconButton
                  component={RouterLink}
                  to="/trip-planner"
                  color="inherit"
                >
                  <ExploreIcon />
                </IconButton>
              </Tooltip>
            )}

            {/* Desktop: How It Works */}
            {!isMobile && (
              <Tooltip title="How It Works">
                <IconButton
                  component={RouterLink}
                  to="/about"
                  color="inherit"
                >
                  <InfoIcon />
                </IconButton>
              </Tooltip>
            )}

            {/* Desktop: Favorites (authenticated only) */}
            {!isMobile && isAuthenticated && (
              <Tooltip title="Favorites">
                <IconButton
                  component={RouterLink}
                  to="/favorites"
                  color="inherit"
                >
                  <FavoriteIcon />
                </IconButton>
              </Tooltip>
            )}

            {/* Notifications - always visible */}
            <NotificationDropdown iconColor="inherit" />

            {/* Profile menu */}
            {isAuthenticated ? (
              <>
                <Tooltip title="Account">
                  <IconButton color="inherit" onClick={handleMenuOpen}>
                    <AccountCircle />
                  </IconButton>
                </Tooltip>
                <Menu
                  anchorEl={anchorEl}
                  open={Boolean(anchorEl)}
                  onClose={handleMenuClose}
                  anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
                  transformOrigin={{ vertical: 'top', horizontal: 'right' }}
                >
                  <MenuItem disabled sx={{ opacity: 1 }}>
                    <Typography variant="body2" color="text.secondary">
                      {displayLabel}
                    </Typography>
                  </MenuItem>
                  <Divider />
                  <MenuItem component={RouterLink} to="/profile" onClick={handleMenuClose}>
                    <ListItemIcon><PersonIcon fontSize="small" /></ListItemIcon>
                    Profile
                  </MenuItem>
                  <MenuItem onClick={handleLogout}>
                    <ListItemIcon><LogoutIcon fontSize="small" /></ListItemIcon>
                    Log Out
                  </MenuItem>
                </Menu>
              </>
            ) : (
              /* Not authenticated - show login icon on desktop */
              !isMobile && (
                <Tooltip title="Log In">
                  <IconButton
                    component={RouterLink}
                    to="/login"
                    color="inherit"
                  >
                    <PersonIcon />
                  </IconButton>
                </Tooltip>
              )
            )}
          </Box>
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
