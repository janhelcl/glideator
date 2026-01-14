import React from 'react';
import { Box, Paper, Typography, List, ListItem, ListItemIcon, ListItemText } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import MapIcon from '@mui/icons-material/Map';
import ExploreIcon from '@mui/icons-material/Explore';
import PlaceIcon from '@mui/icons-material/Place';
import FavoriteIcon from '@mui/icons-material/Favorite';
import NotificationsIcon from '@mui/icons-material/Notifications';
import CloudIcon from '@mui/icons-material/Cloud';
import FlightIcon from '@mui/icons-material/Flight';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';

const About = () => {
  return (
    <Box sx={{ maxWidth: '1200px', margin: '0 auto', p: 2, minHeight: '100%' }}>
      <Helmet>
        <title>How It Works – Parra-Glideator</title>
        <meta
          name="description"
          content="Learn how Parra-Glideator helps paraglider pilots find the best flying conditions with AI-powered predictions."
        />
      </Helmet>

      {/* Hero Section */}
      <Paper elevation={2} sx={{ mb: 3 }}>
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
                How It Works
              </Typography>
              <Typography variant="body2" color="text.secondary">
                AI-powered flying predictions for paraglider pilots
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

          <Box sx={{ maxWidth: '800px' }}>
            <Typography variant="body1" paragraph>
              Parra-Glideator helps you find when and where conditions look promising for paragliding.
              We analyze weather forecasts and compare them to historical flying patterns to give you
              a simple flyability score for each site and day.
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Currently covering sites across Europe with 7-day forecasts updated daily.
            </Typography>
          </Box>
        </Box>
      </Paper>

      {/* How Predictions Work */}
      <Paper elevation={2} sx={{ mb: 3 }}>
        <Box sx={{ p: { xs: 2, sm: 3 } }}>
          <Typography variant="h5" component="h2" sx={{ fontWeight: 'bold', mb: 2 }}>
            The Predictions
          </Typography>

          <List>
            <ListItem sx={{ px: 0 }}>
              <ListItemIcon>
                <CloudIcon color="primary" />
              </ListItemIcon>
              <ListItemText
                primary="Weather Data"
                secondary="We pull forecast data from NOAA's GFS model — wind speed, direction, thermals, cloud cover, and more."
              />
            </ListItem>
            <ListItem sx={{ px: 0 }}>
              <ListItemIcon>
                <FlightIcon color="primary" />
              </ListItemIcon>
              <ListItemText
                primary="Learned from Real Flights"
                secondary="Our model was trained on thousands of actual paragliding flights to understand what makes a good flying day."
              />
            </ListItem>
            <ListItem sx={{ px: 0 }}>
              <ListItemIcon>
                <TrendingUpIcon color="primary" />
              </ListItemIcon>
              <ListItemText
                primary="Flyability Score (0-100)"
                secondary="Higher scores mean conditions are more similar to days when pilots actually flew well. It's not a guarantee — always check local conditions and use your judgment."
              />
            </ListItem>
          </List>
        </Box>
      </Paper>

      {/* Features */}
      <Paper elevation={2} sx={{ mb: 3 }}>
        <Box sx={{ p: { xs: 2, sm: 3 } }}>
          <Typography variant="h5" component="h2" sx={{ fontWeight: 'bold', mb: 2 }}>
            Features
          </Typography>

          <List>
            <ListItem
              sx={{ px: 0, cursor: 'pointer' }}
              component={RouterLink}
              to="/"
            >
              <ListItemIcon>
                <MapIcon color="primary" />
              </ListItemIcon>
              <ListItemText
                primary="Map View"
                secondary="Browse all sites on an interactive map. See 7-day forecasts at a glance with color-coded predictions."
              />
            </ListItem>
            <ListItem
              sx={{ px: 0, cursor: 'pointer' }}
              component={RouterLink}
              to="/trip-planner"
            >
              <ListItemIcon>
                <ExploreIcon color="primary" />
              </ListItemIcon>
              <ListItemText
                primary="Trip Planner"
                secondary="Find the best sites within your travel range. Filter by distance, altitude, date range, and minimum flyability."
              />
            </ListItem>
            <ListItem sx={{ px: 0 }}>
              <ListItemIcon>
                <PlaceIcon color="primary" />
              </ListItemIcon>
              <ListItemText
                primary="Site Details"
                secondary="Dive deep into any site with hourly forecasts, seasonal statistics, and similar historical days."
              />
            </ListItem>
            <ListItem
              sx={{ px: 0, cursor: 'pointer' }}
              component={RouterLink}
              to="/favorites"
            >
              <ListItemIcon>
                <FavoriteIcon color="primary" />
              </ListItemIcon>
              <ListItemText
                primary="Favorites"
                secondary="Save your favorite sites for quick access. Get personalized recommendations based on your preferences."
              />
            </ListItem>
            <ListItem
              sx={{ px: 0, cursor: 'pointer' }}
              component={RouterLink}
              to="/notifications?tab=settings"
            >
              <ListItemIcon>
                <NotificationsIcon color="primary" />
              </ListItemIcon>
              <ListItemText
                primary="Notifications"
                secondary="Set up alerts to get notified when conditions at your favorite sites look promising."
              />
            </ListItem>
          </List>
        </Box>
      </Paper>

      {/* Getting Started */}
      <Paper elevation={2}>
        <Box sx={{ p: { xs: 2, sm: 3 } }}>
          <Typography variant="h5" component="h2" sx={{ fontWeight: 'bold', mb: 2 }}>
            Getting Started
          </Typography>

          <List sx={{ listStyleType: 'decimal', pl: 2 }}>
            <ListItem sx={{ display: 'list-item', px: 1 }}>
              <ListItemText
                primary="Browse the map or search for a site"
                secondary="Use the search bar or zoom into your area to find paragliding sites."
              />
            </ListItem>
            <ListItem sx={{ display: 'list-item', px: 1 }}>
              <ListItemText
                primary="Tap a site to see the forecast"
                secondary="View the 7-day prediction and click through to see detailed forecasts and statistics."
              />
            </ListItem>
            <ListItem sx={{ display: 'list-item', px: 1 }}>
              <ListItemText
                primary="Create a free account"
                secondary="Sign up to save your favorite sites and get personalized recommendations."
              />
            </ListItem>
            <ListItem sx={{ display: 'list-item', px: 1 }}>
              <ListItemText
                primary="Set up notifications"
                secondary="Never miss a good flying day — get alerts when conditions meet your criteria."
              />
            </ListItem>
          </List>
        </Box>
      </Paper>
    </Box>
  );
};

export default About;
