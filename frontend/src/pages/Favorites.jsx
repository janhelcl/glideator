import React, { useEffect, useState } from 'react';
import { Box, Typography, IconButton, Paper, Alert } from '@mui/material';
import FavoriteIcon from '@mui/icons-material/Favorite';
import { Helmet } from 'react-helmet-async';
import { useAuth } from '../context/AuthContext';
import { fetchSites } from '../api';
import SiteList from '../components/SiteList';
import LoadingSpinner from '../components/LoadingSpinner';

const METRIC = 'XC0';

const transformSite = (site) => {
  if (!site) return null;

  const predictions = site.predictions || [];
  const metricIndex = 0;

  const metricValues = predictions
    .map((prediction) =>
      prediction.values && prediction.values.length > metricIndex
        ? prediction.values[metricIndex]
        : null
    )
    .filter((value) => value !== null && value !== undefined);

  const averageProbability =
    metricValues.length > 0
      ? metricValues.reduce((sum, value) => sum + value, 0) / metricValues.length
      : 0;

  const daily_probabilities = predictions.map((prediction) => ({
    date: prediction.date,
    probability:
      prediction.values && prediction.values.length > metricIndex
        ? prediction.values[metricIndex]
        : 0,
    source: 'forecast',
  }));

  return {
    site_id: String(site.site_id),
    site_name: site.name,
    latitude: site.latitude,
    longitude: site.longitude,
    altitude: site.altitude,
    average_flyability: averageProbability ?? 0,
    daily_probabilities,
  };
};

const Favorites = () => {
  const { favorites, toggleFavoriteSite } = useAuth();
  const [favoriteSites, setFavoriteSites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadSites = async () => {
      try {
        setLoading(true);
        setError(null);

        if (!favorites || favorites.length === 0) {
          setFavoriteSites([]);
          return;
        }

        const data = await fetchSites();

        const filtered = (data || []).filter((site) =>
          favorites.includes(site.site_id)
        );

        const transformed = filtered
          .map(transformSite)
          .filter(Boolean)
          .sort((a, b) => a.site_name.localeCompare(b.site_name));

        setFavoriteSites(transformed);
      } catch (err) {
        console.error('Failed to load favorite sites', err);
        setError('Failed to load favorite sites. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    loadSites();
  }, [favorites]);

  const hasFavorites = favorites && favorites.length > 0;

  return (
    <Box sx={{ maxWidth: '1200px', margin: '0 auto', p: 2 }}>
      <Helmet>
        <title>My Favorites – Parra-Glideator</title>
        <meta
          name="description"
          content="Your saved paragliding sites with quick access to site details and flyability snapshots."
        />
        <link rel="canonical" href={window.location.origin + '/favorites'} />
        <meta property="og:title" content="My Favorite Paragliding Sites" />
        <meta
          property="og:description"
          content="Review your bookmarked paragliding sites and jump into detailed forecasts."
        />
      </Helmet>

      <Paper elevation={2}>
        <Box sx={{ p: 3 }}>
          <Box
            sx={{
              p: 2,
              borderBottom: 1,
              borderColor: 'divider',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              mb: 3,
            }}
          >
            <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold' }}>
              My Favorites
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <img
                src="/logo192.png"
                alt="Glideator Logo"
                style={{ height: '60px', width: 'auto' }}
              />
            </Box>
          </Box>

          {loading ? (
            <LoadingSpinner />
          ) : error ? (
            <Alert severity="error">{error}</Alert>
          ) : !hasFavorites ? (
            <Typography variant="body1">
              You haven&rsquo;t added any favorites yet.
            </Typography>
          ) : favoriteSites.length === 0 ? (
            <Typography variant="body1">
              None of your favorite sites have forecast data yet. Check back soon!
            </Typography>
          ) : (
            <SiteList
              sites={favoriteSites}
              selectedMetric={METRIC}
              showRanking={false}
              renderSiteActions={(site, { defaultAction }) => (
                <>
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleFavoriteSite(Number(site.site_id));
                    }}
                    color="error"
                    aria-label={`Remove ${site.site_name} from favorites`}
                  >
                    <FavoriteIcon />
                  </IconButton>
                  {defaultAction}
                </>
              )}
            />
          )}
        </Box>
      </Paper>
    </Box>
  );
};

export default Favorites;

