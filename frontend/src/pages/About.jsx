import React from 'react';
import {
  Box, Paper, Typography, Grid, Chip, useTheme, useMediaQuery,
} from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import MapIcon from '@mui/icons-material/Map';
import ExploreIcon from '@mui/icons-material/Explore';
import PlaceIcon from '@mui/icons-material/Place';
import FavoriteIcon from '@mui/icons-material/Favorite';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import CloudIcon from '@mui/icons-material/Cloud';
import PsychologyIcon from '@mui/icons-material/Psychology';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import ScoreDemo from '../components/ScoreDemo';

const PipelineStep = ({ icon, title, description, isLast }) => {
  const theme = useTheme();
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'));

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: 1, position: 'relative' }}>
      <Box
        sx={{
          width: 64,
          height: 64,
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #1976d2 0%, #42a5f5 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#fff',
          mb: 1.5,
          boxShadow: '0 4px 14px rgba(25, 118, 210, 0.3)',
        }}
      >
        {icon}
      </Box>
      <Typography variant="subtitle1" sx={{ fontWeight: 'bold', textAlign: 'center' }}>{title}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', mt: 0.5, px: 1 }}>
        {description}
      </Typography>
      {!isLast && (
        <Box sx={{
          position: 'absolute',
          right: isSmall ? '50%' : -12,
          bottom: isSmall ? -20 : 'auto',
          top: isSmall ? 'auto' : 28,
          transform: isSmall ? 'translateX(50%)' : 'none',
          color: 'primary.main',
          opacity: 0.5,
        }}>
          {isSmall ? <ArrowDownwardIcon /> : <ArrowForwardIcon />}
        </Box>
      )}
    </Box>
  );
};

const FeatureCard = ({ icon, title, description, to }) => (
  <Paper
    component={RouterLink}
    to={to}
    elevation={0}
    sx={{
      p: 2.5,
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      gap: 1,
      textDecoration: 'none',
      color: 'inherit',
      border: 1,
      borderColor: 'divider',
      borderRadius: 2,
      transition: 'all 0.2s ease',
      '&:hover': {
        borderColor: 'primary.main',
        boxShadow: '0 4px 20px rgba(25, 118, 210, 0.12)',
        transform: 'translateY(-2px)',
      },
    }}
  >
    <Box sx={{ color: 'primary.main', display: 'flex', alignItems: 'center', gap: 1 }}>
      {icon}
      <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>{title}</Typography>
    </Box>
    <Typography variant="body2" color="text.secondary">{description}</Typography>
  </Paper>
);

const About = () => {
  const theme = useTheme();
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'));

  return (
    <Box sx={{ maxWidth: '1000px', margin: '0 auto', p: { xs: 1.5, sm: 2 }, minHeight: '100%' }}>
      <Helmet>
        <title>How It Works – Parra-Glideator</title>
        <meta
          name="description"
          content="Learn how Parra-Glideator uses AI and real flight data to predict paragliding conditions across Europe."
        />
      </Helmet>

      {/* Hero */}
      <Paper
        elevation={3}
        sx={{
          mb: 3,
          overflow: 'hidden',
          borderRadius: 3,
          background: 'linear-gradient(135deg, #2e7d32 0%, #1b5e20 40%, #33691e 100%)',
          color: '#fff',
          position: 'relative',
        }}
      >
        <Box sx={{ p: { xs: 3, sm: 4 }, display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 3, alignItems: 'center' }}>
          <Box sx={{ flex: 1 }}>
            <Chip
              label="Public Beta"
              size="small"
              sx={{ mb: 2, backgroundColor: 'rgba(255,255,255,0.2)', color: '#fff', fontWeight: 'bold' }}
            />
            <Typography variant="h3" component="h1" sx={{ fontWeight: 'bold', mb: 1, fontSize: { xs: '1.75rem', sm: '2.5rem' } }}>
              Should you fly tomorrow?
            </Typography>
            <Typography variant="h6" sx={{ mb: 2, opacity: 0.9, fontWeight: 'normal', fontSize: { xs: '1rem', sm: '1.15rem' } }}>
              Parra-Glideator crunches weather forecasts and real paragliding flight data
              to tell you when and where conditions look best.
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.75 }}>
              250 sites across Europe &middot; 7-day forecasts &middot; Updated 4&times; daily
            </Typography>
          </Box>
          <Box
            component="img"
            src={`${process.env.PUBLIC_URL || ''}/assets/images/parraglideator_disclaimer.png`}
            alt="Parra-Glideator — The skies are wild, the thermals treacherous. Be brave — but not foolish!"
            sx={{
              width: { xs: '100%', md: 280 },
              maxWidth: 320,
              borderRadius: 2,
              boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
            }}
          />
        </Box>
      </Paper>

      {/* How Predictions Work — Pipeline */}
      <Paper elevation={2} sx={{ mb: 3, borderRadius: 3 }}>
        <Box sx={{ p: { xs: 2.5, sm: 3.5 } }}>
          <Typography variant="h5" component="h2" sx={{ fontWeight: 'bold', mb: 1 }}>
            How Predictions Work
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            Three ingredients go into every forecast. New predictions are generated
            each time NOAA publishes fresh GFS data — roughly every 6 hours.
          </Typography>

          <Box sx={{
            display: 'flex',
            flexDirection: { xs: 'column', sm: 'row' },
            gap: { xs: 4, sm: 2 },
            mb: 2,
          }}>
            <PipelineStep
              icon={<CloudIcon sx={{ fontSize: 30 }} />}
              title="Weather Forecast"
              description="The full vertical profile of the atmosphere over each site — pulled from NOAA's global GFS model every 6 hours."
            />
            <PipelineStep
              icon={<PsychologyIcon sx={{ fontSize: 30 }} />}
              title="Neural Network"
              description="An AI trained on real flights learns which weather patterns historically produced flyable days at each site."
            />
            <PipelineStep
              icon={<TrendingUpIcon sx={{ fontSize: 30 }} />}
              title="Flyability Score"
              description="The result: a simple 0–100 score for each site and day telling you how good conditions look."
              isLast
            />
          </Box>
        </Box>
      </Paper>

      {/* The Score — Interactive Demo */}
      <Paper elevation={2} sx={{ mb: 3, borderRadius: 3, overflow: 'hidden' }}>
        <Box sx={{ p: { xs: 2.5, sm: 3.5 } }}>
          <Typography variant="h5" component="h2" sx={{ fontWeight: 'bold', mb: 1 }}>
            The Flyability Score
          </Typography>
          <Typography variant="body1" color="text.secondary" paragraph>
            Every dot on the map is a paragliding site. The score is a calibrated probability
            that at least one pilot will fly there that day. Drag the slider to see how the
            score changes when you ask about longer, more ambitious flights.
          </Typography>

          <ScoreDemo />

          <Typography variant="body2" color="text.secondary" sx={{ mt: 2, fontStyle: 'italic', textAlign: 'center' }}>
            Still a forecast, not a guarantee. Always check local conditions
            and use your pilot judgment.
          </Typography>
        </Box>
      </Paper>

      {/* Features */}
      <Paper elevation={2} sx={{ mb: 3, borderRadius: 3, overflow: 'hidden' }}>
        <Box sx={{ p: { xs: 2.5, sm: 3.5 } }}>
          <Typography variant="h5" component="h2" sx={{ fontWeight: 'bold', mb: 0.5 }}>
            What You Can Do
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            Explore the forecast, plan trips, and never miss a flyable day.
          </Typography>

          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <FeatureCard
                icon={<MapIcon />}
                title="Map View"
                description="See every site at a glance. Color-coded dots show the 7-day forecast — zoom in, pick a date, and spot where conditions are shaping up."
                to="/"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FeatureCard
                icon={<ExploreIcon />}
                title="Trip Planner"
                description="Set your travel range, pick your dates, and let the planner rank the best sites you can reach. Filter by flyability, altitude, and tags."
                to="/trip-planner"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FeatureCard
                icon={<PlaceIcon />}
                title="Site Details"
                description="Dive into any site for hourly forecasts, flight-quality distributions, seasonal patterns, and a list of historically similar days with real XContest flights."
                to="/details/133?tab=activity"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FeatureCard
                icon={<FavoriteIcon />}
                title="Favorites"
                description="Save the sites you fly most. Your favorites get a dedicated dashboard so you can check conditions in seconds."
                to="/favorites"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FeatureCard
                icon={<NotificationsActiveIcon />}
                title="Notifications"
                description="Set a flyability threshold for your favorite sites. Get an alert when conditions cross it — so you can pack the car instead of refreshing the forecast."
                to="/notifications?tab=settings"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FeatureCard
                icon={<SmartToyIcon />}
                title="AI Assistant (MCP)"
                description={`Ask your AI assistant "Where should I fly this weekend?" and get answers backed by Glideator data. Works with Claude and any MCP-compatible client.`}
                to="/about#mcp"
              />
            </Grid>
          </Grid>
        </Box>
      </Paper>

      {/* MCP Section */}
      <Paper id="mcp" elevation={2} sx={{ mb: 3, borderRadius: 3 }}>
        <Box sx={{ p: { xs: 2.5, sm: 3.5 } }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <SmartToyIcon color="primary" />
            <Typography variant="h5" component="h2" sx={{ fontWeight: 'bold' }}>
              Talk to Your AI About Flying
            </Typography>
          </Box>
          <Typography variant="body1" color="text.secondary" paragraph>
            Glideator exposes an MCP (Model Context Protocol) server, which means AI assistants
            can query forecasts and site data on your behalf. Ask in plain language:
          </Typography>

          <Box sx={{
            display: 'flex',
            flexDirection: 'column',
            gap: 1,
            mb: 2,
            pl: 2,
            borderLeft: 3,
            borderColor: 'primary.main',
          }}>
            {[
              '"Where should I fly near Innsbruck this weekend?"',
              '"What\'s the best day to fly at Bassano in the next week?"',
              '"Find me sites above 1500m with a score over 70 on Friday."',
            ].map((q, i) => (
              <Typography key={i} variant="body2" sx={{ fontStyle: 'italic', color: 'text.secondary' }}>
                {q}
              </Typography>
            ))}
          </Box>

          <Paper variant="outlined" sx={{ p: 2, borderRadius: 2, backgroundColor: 'grey.50' }}>
            <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
              MCP server URL:{' '}
              <Box component="span" sx={{ fontWeight: 'bold', color: 'primary.main' }}>
                https://www.parra-glideator.com/mcp
              </Box>
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
              Add this URL to Claude Desktop, ChatGPT, or any MCP-compatible client.
            </Typography>
          </Paper>
        </Box>
      </Paper>

      {/* Meet Parra-Glideator */}
      <Paper
        elevation={2}
        sx={{
          borderRadius: 3,
          overflow: 'hidden',
          background: 'linear-gradient(135deg, #4e342e 0%, #3e2723 100%)',
          color: '#fff',
        }}
      >
        <Box sx={{ p: { xs: 2.5, sm: 3.5 }, display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, gap: 3, alignItems: 'center' }}>
          <Box
            component="img"
            src={`${process.env.PUBLIC_URL || ''}/logo192.png`}
            alt="Parra-Glideator mascot"
            sx={{ width: { xs: 100, sm: 120 }, height: 'auto', flexShrink: 0 }}
          />
          <Box>
            <Typography variant="h5" component="h2" sx={{ fontWeight: 'bold', mb: 1 }}>
              Meet Parra-Glideator
            </Typography>
            <Typography variant="body1" sx={{ opacity: 0.9, mb: 1 }}>
              Our mascot is a parrot who traded natural flight for a paraglider. Nobody knows why.
              Ask him and he&rsquo;ll dodge the question:{' '}
              <Box component="em">&ldquo;I have chosen the noble path of man-borne flight, for wings alone
              cannot lift one&rsquo;s soul!&rdquo;</Box>
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.7 }}>
              Like every pilot, Parra faces uncertainty — weather, site choice, timing.
              This app is built to give you (and him) the odds before the battle.
            </Typography>
          </Box>
        </Box>
      </Paper>
    </Box>
  );
};

export default About;
