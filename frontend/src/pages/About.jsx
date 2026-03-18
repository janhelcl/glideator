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
  return (
    <Box sx={{ maxWidth: '1000px', margin: '0 auto', p: { xs: 1.5, sm: 2 }, minHeight: '100%' }}>
      <Helmet>
        <title>How It Works – Parra-Glideator</title>
        <meta
          name="description"
          content="Learn how Parra-Glideator turns forecast data and real flight history into practical paragliding decision support."
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
        <Box sx={{ p: { xs: 3, sm: 4 }, display: 'flex', flexDirection: { xs: 'column', md: 'row' }, gap: 3, alignItems: { xs: 'stretch', md: 'center' } }}>
          <Box sx={{ flex: 1 }}>
            <Chip
              label="Public Beta"
              size="small"
              sx={{ mb: 2, backgroundColor: 'rgba(255,255,255,0.2)', color: '#fff', fontWeight: 'bold' }}
            />
            <Typography variant="h3" component="h1" sx={{ fontWeight: 'bold', mb: 1, fontSize: { xs: '1.75rem', sm: '2.5rem' } }}>
              Find the promising days. Verify the details. Make the call yourself.
            </Typography>
            <Typography variant="body1" sx={{ opacity: 0.92, mb: 1.5, fontSize: { xs: '1rem', sm: '1.05rem' } }}>
              Meet Parra-Glideator: a parrot who traded natural flight for a paraglider.<br />Nobody knows why.
            </Typography>
            <Typography variant="body1" sx={{ opacity: 0.92, mb: 2, fontSize: { xs: '1rem', sm: '1.05rem' } }}>
            Parra-Glideator reads the forecast through the lens of real flights, helping you spot which sites are likely to be on.
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.65, mt: 1.5 }}>
              250 sites across Europe &middot; 7-day forecasts &middot; Updated 4&times; daily
            </Typography>
          </Box>

          <Box
            component="img"
            src={`${process.env.PUBLIC_URL || ''}/logo512.png`}
            alt="Parra-Glideator mascot"
            sx={{
              width: { xs: 120, md: 220 },
              height: 'auto',
              alignSelf: { xs: 'center', md: 'center' },
              flexShrink: 0,
            }}
          />
        </Box>
      </Paper>

      {/* How Predictions Work — Pipeline */}
      <Paper elevation={2} sx={{ mb: 3, borderRadius: 3 }}>
        <Box sx={{ p: { xs: 2.5, sm: 3.5 } }}>
          <Typography variant="h5" component="h2" sx={{ fontWeight: 'bold', mb: 1 }}>
            How the forecast becomes a flying signal
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            Every update starts with fresh NOAA GFS data. From there, Glideator compares the forecast with patterns from real flights and turns that mess into something you can actually use.
          </Typography>

          <Box sx={{
            display: 'flex',
            flexDirection: { xs: 'column', sm: 'row' },
            gap: { xs: 4, sm: 2 },
            mb: 2,
          }}>
            <PipelineStep
              icon={<CloudIcon sx={{ fontSize: 30 }} />}
              title="Forecast data"
              description="The full atmospheric profile over each site, pulled from NOAA's global GFS model every 6 hours. Wind, lift, clouds, and the rest of the weather spaghetti."
            />
            <PipelineStep
              icon={<PsychologyIcon sx={{ fontSize: 30 }} />}
              title="Learned from real flights"
              description="A model trained on actual paragliding flights learns which forecast patterns tend to line up with days when pilots really flew."
            />
            <PipelineStep
              icon={<TrendingUpIcon sx={{ fontSize: 30 }} />}
              title="Flight chances"
              description="The result is a simple score for each site and day that helps you see where conditions look worth a closer look."
              isLast
            />
          </Box>
        </Box>
      </Paper>

      {/* The Score — Interactive Demo */}
      <Paper elevation={2} sx={{ mb: 3, borderRadius: 3, overflow: 'hidden' }}>
        <Box sx={{ p: { xs: 2.5, sm: 3.5 } }}>
          <Typography variant="h5" component="h2" sx={{ fontWeight: 'bold', mb: 1 }}>
            What the score actually means
          </Typography>
          <Typography variant="body1" color="text.secondary" paragraph>
            The map can show the estimated chance of a flight — or the chance of a stronger day, like a 20+ or 80+ point flight. Drag the slider to see how the interpretation changes when you ask a more ambitious question.
          </Typography>

          <ScoreDemo />

          <Typography variant="body2" color="text.secondary" sx={{ mt: 2, fontStyle: 'italic', textAlign: 'center' }}>
          Decision support, not divine revelation. Always check local conditions and use your judgment.
          </Typography>
        </Box>
      </Paper>

      {/* Features */}
      <Paper elevation={2} sx={{ mb: 3, borderRadius: 3, overflow: 'hidden' }}>
        <Box sx={{ p: { xs: 2.5, sm: 3.5 } }}>
          <Typography variant="h5" component="h2" sx={{ fontWeight: 'bold', mb: 0.5 }}>
            How people actually use it
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            Glideator is best at helping you narrow the search, compare options quickly, and notice when a good window might be opening.
          </Typography>

          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <FeatureCard
                icon={<MapIcon />}
                title="Scan the map"
                description="Get a fast read on where the interesting days seem to be. The map is there to orient you quickly, not make the final decision for you."
                to="/"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FeatureCard
                icon={<ExploreIcon />}
                title="Compare trip options"
                description="Set your travel range and dates, then let Trip Planner compress the search space instead of manually checking half a continent."
                to="/trip-planner"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FeatureCard
                icon={<PlaceIcon />}
                title="Inspect the evidence"
                description="Open any site to dig into hourly forecasts, flight-quality distributions, seasonal patterns, and similar historical days with real XContest flights."
                to="/details/133?tab=activity"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FeatureCard
                icon={<FavoriteIcon />}
                title="Keep your shortlist ready"
                description="Save the places you care about most so checking conditions feels like a quick scan, not a ritual involving twelve tabs and mild despair."
                to="/favorites"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FeatureCard
                icon={<NotificationsActiveIcon />}
                title="Get nudged when it matters"
                description="Set thresholds for your favorite sites and let Glideator alert you when conditions start looking interesting. Better than remembering to refresh everything yourself."
                to="/notifications?tab=settings"
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FeatureCard
                icon={<SmartToyIcon />}
                title="Ask your AI"
                description={'Use Glideator through any MCP-compatible assistant when you want to ask things like “Where should I fly this weekend?” in plain language.'}
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
              Talk to your AI about flying
            </Typography>
          </Box>
          <Typography variant="body1" color="text.secondary" paragraph>
            Glideator exposes an MCP server, so compatible AI assistants can query forecasts and site data directly. That means you can ask normal planning questions instead of forcing a chatbot to improvise about valley winds.
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

    </Box>
  );
};

export default About;
