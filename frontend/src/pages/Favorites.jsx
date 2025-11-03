import React, { useEffect, useState } from 'react';
import { Box, Typography, IconButton, Paper, Alert, Snackbar, Button, Tooltip } from '@mui/material';
import FavoriteIcon from '@mui/icons-material/Favorite';
import NotificationsActiveIcon from '@mui/icons-material/NotificationsActive';
import { Helmet } from 'react-helmet-async';
import { useAuth } from '../context/AuthContext';
import { fetchSites, fetchSiteRecommendations } from '../api';
import SiteList from '../components/SiteList';
import LoadingSpinner from '../components/LoadingSpinner';
import { useNavigate } from 'react-router-dom';

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
  const navigate = useNavigate();
  const [allSites, setAllSites] = useState([]);
  const [favoriteSites, setFavoriteSites] = useState([]);
  const [recommendedSites, setRecommendedSites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [recommendationsLoading, setRecommendationsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [lastRemovedSite, setLastRemovedSite] = useState(null);

  useEffect(() => {
    const loadSites = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchSites();
        setAllSites(data || []);
      } catch (err) {
        console.error('Failed to load favorite sites', err);
        setError('Failed to load favorite sites. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    loadSites();
  }, []);

  useEffect(() => {
    if (!allSites || allSites.length === 0) {
      setFavoriteSites([]);
      return;
    }

    const filtered = allSites.filter((site) => favorites.includes(site.site_id));

    const transformed = filtered
      .map(transformSite)
      .filter(Boolean)
      .sort((a, b) => a.site_name.localeCompare(b.site_name));

    setFavoriteSites(transformed);
  }, [allSites, favorites]);

  // Fetch recommendations when favorites change
  useEffect(() => {
    const loadRecommendations = async () => {
      if (!favorites || favorites.length === 0 || !allSites || allSites.length === 0) {
        setRecommendedSites([]);
        return;
      }

      try {
        setRecommendationsLoading(true);
        const response = await fetchSiteRecommendations(favorites, 5);
        
        if (response.recommendations && response.recommendations.length > 0) {
          // Get site details for recommended site IDs
          const recommendedSiteIds = response.recommendations.map(rec => rec.site_id);
          const recommendedSitesData = allSites.filter(site => 
            recommendedSiteIds.includes(site.site_id)
          );
          
          // Transform and sort by similarity score
          const transformed = recommendedSitesData
            .map(transformSite)
            .filter(Boolean)
            .sort((a, b) => {
              const aScore = response.recommendations.find(rec => rec.site_id === parseInt(a.site_id))?.similarity_score || 0;
              const bScore = response.recommendations.find(rec => rec.site_id === parseInt(b.site_id))?.similarity_score || 0;
              return bScore - aScore; // Sort by similarity score descending
            });
          
          setRecommendedSites(transformed);
        } else {
          setRecommendedSites([]);
        }
      } catch (err) {
        console.error('Failed to load recommendations', err);
        setRecommendedSites([]);
      } finally {
        setRecommendationsLoading(false);
      }
    };

    loadRecommendations();
  }, [favorites, allSites]);

  const handleCreateNotification = (site) => {
    navigate('/notifications', {
      state: {
        notificationSetup: {
          siteId: Number(site.site_id),
          metric: METRIC,
        },
      },
    });
  };

  const handleRemoveFavorite = async (site) => {
    const siteId = Number(site.site_id);
    setLastRemovedSite(site);
    setFavoriteSites((prev) => prev.filter((item) => item.site_id !== site.site_id));
    setSnackbarOpen(true);
    try {
      await toggleFavoriteSite(siteId);
    } catch (err) {
      console.error('Failed to update favorite status', err);
      // Revert optimistic update on failure
      setFavoriteSites((prev) => [...prev, site].sort((a, b) => a.site_name.localeCompare(b.site_name)));
      setLastRemovedSite(null);
      setSnackbarOpen(false);
      setError('Failed to remove from favorites. Please try again.');
    }
  };

  const handleAddFavorite = async (site) => {
    const siteId = Number(site.site_id);
    try {
      await toggleFavoriteSite(siteId);
      // Add to favorites list optimistically
      setFavoriteSites((prev) => [...prev, site].sort((a, b) => a.site_name.localeCompare(b.site_name)));
      // Remove from recommendations
      setRecommendedSites((prev) => prev.filter((item) => item.site_id !== site.site_id));
    } catch (err) {
      console.error('Failed to add to favorites', err);
      setError('Failed to add to favorites. Please try again.');
    }
  };

  const handleUndoRemove = async () => {
    if (!lastRemovedSite) return;

    const siteId = Number(lastRemovedSite.site_id);
    try {
      await toggleFavoriteSite(siteId);
    } catch (err) {
      console.error('Failed to restore favorite', err);
      setError('Failed to restore favorite. Please try again.');
      setSnackbarOpen(false);
      setLastRemovedSite(null);
      return;
    }

    setFavoriteSites((prev) =>
      [...prev, lastRemovedSite].sort((a, b) => a.site_name.localeCompare(b.site_name))
    );
    setSnackbarOpen(false);
    setLastRemovedSite(null);
  };

  const handleSnackbarClose = (event, reason) => {
    if (reason === 'clickaway') {
      return;
    }
    setSnackbarOpen(false);
    setLastRemovedSite(null);
  };

  const hasFavorites = favorites && favorites.length > 0;
  const snackbarMessage = lastRemovedSite
    ? `${lastRemovedSite.site_name} removed from favorites`
    : '';

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
                  <Tooltip title="Create notification">
                    <IconButton
                      size="small"
                      color="primary"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleCreateNotification(site);
                      }}
                    >
                      <NotificationsActiveIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRemoveFavorite(site);
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

      {/* Recommendations Section */}
      {hasFavorites && (
        <Paper elevation={2} sx={{ mt: 3 }}>
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
              <Typography variant="h5" component="h2" sx={{ fontWeight: 'bold' }}>
                You may also like
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Based on your favorites
              </Typography>
            </Box>

            {recommendationsLoading ? (
              <LoadingSpinner />
            ) : recommendedSites.length === 0 ? (
              <Typography variant="body1" color="text.secondary">
                No recommendations available at the moment.
              </Typography>
            ) : (
              <SiteList
                sites={recommendedSites}
                selectedMetric={METRIC}
                showRanking={false}
                renderSiteActions={(site, { defaultAction }) => (
                  <>
                    <Tooltip title="Create notification">
                      <IconButton
                        size="small"
                        color="primary"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleCreateNotification(site);
                        }}
                      >
                        <NotificationsActiveIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAddFavorite(site);
                      }}
                      color="primary"
                      aria-label={`Add ${site.site_name} to favorites`}
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
      )}

      <Snackbar
        open={snackbarOpen}
        autoHideDuration={6000}
        onClose={handleSnackbarClose}
        message={snackbarMessage}
        action={
          lastRemovedSite ? (
            <Button color="secondary" size="small" onClick={handleUndoRemove}>
              Undo
            </Button>
          ) : null
        }
      />
    </Box>
  );
};

export default Favorites;
