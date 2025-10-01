import React, { useEffect, useState } from 'react';
import {
  Container,
  Typography,
  List,
  ListItem,
  ListItemText,
  IconButton,
  CircularProgress,
} from '@mui/material';
import FavoriteIcon from '@mui/icons-material/Favorite';
import { Link as RouterLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { fetchSitesList } from '../api';

const Favorites = () => {
  const { favorites, toggleFavoriteSite } = useAuth();
  const [sites, setSites] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadSites = async () => {
      try {
        const data = await fetchSitesList();
        setSites(data || []);
      } finally {
        setLoading(false);
      }
    };

    loadSites();
  }, []);

  const favoriteSites = sites.filter((site) => favorites.includes(site.site_id));

  return (
    <Container maxWidth="sm" sx={{ mt: 8 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        My Favorites
      </Typography>

      {loading ? (
        <CircularProgress />
      ) : favoriteSites.length === 0 ? (
        <Typography variant="body1">You haven&rsquo;t added any favorites yet.</Typography>
      ) : (
        <List>
          {favoriteSites.map((site) => (
            <ListItem
              key={site.site_id}
              secondaryAction={
                <IconButton edge="end" onClick={() => toggleFavoriteSite(site.site_id)}>
                  <FavoriteIcon color="error" />
                </IconButton>
              }
              component={RouterLink}
              to={`/details/${site.site_id}`}
            >
              <ListItemText primary={site.name} />
            </ListItem>
          ))}
        </List>
      )}
    </Container>
  );
};

export default Favorites;

