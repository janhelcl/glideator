import React, { useState, useEffect } from 'react';
import { TextField, Autocomplete, Box } from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import FavoriteIcon from '@mui/icons-material/Favorite';
import apiClient from '../api';

const buildOptions = (sites, favorites, boostFavorites = false) => {
  const favoriteSet = new Set(favorites);
  const sortedSites = [...(sites || [])].sort((a, b) => {
    if (boostFavorites) {
      const favoriteDifference = Number(favoriteSet.has(b.site_id)) - Number(favoriteSet.has(a.site_id));
      if (favoriteDifference !== 0) return favoriteDifference;
    }
    return a.name.localeCompare(b.name);
  });

  return sortedSites.map(site => ({
    label: site.name,
    site,
    favorite: favoriteSet.has(site.site_id),
  }));
};

const SearchBar = ({ sites, onSiteSelect, mobile = false }) => {
  const [options, setOptions] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, favorites } = useAuth();

  useEffect(() => {
    const cleanedQuery = inputValue.trim();

    if (!cleanedQuery) {
      setOptions(buildOptions(sites, favorites, true));
      setLoading(false);
      return undefined;
    }

    const controller = new AbortController();
    const timeoutId = window.setTimeout(async () => {
      setLoading(true);
      try {
        const response = await apiClient.get('/sites/search', {
          params: { query: cleanedQuery, limit: 10 },
          signal: controller.signal,
        });
        setOptions(buildOptions(response.data, favorites));
      } catch (error) {
        if (error?.code !== 'ERR_CANCELED') {
          console.error('Error searching sites:', error);
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }, 200);

    return () => {
      window.clearTimeout(timeoutId);
      controller.abort();
    };
  }, [sites, favorites, inputValue]);

  const handleSelect = (event, value) => {
    if (!value) return;

    const currentParams = new URLSearchParams(location.search);
    
    if (location.pathname === '/') {
      onSiteSelect(value.site);
    } else {
      navigate(`/details/${value.site.site_id}?${currentParams.toString()}`);
    }
  };

  return (
    <Box sx={{ 
      width: mobile ? '100%' : 300, 
      margin: mobile ? '0' : '0 20px',
      maxWidth: mobile ? 'none' : '300px'
    }}>
      <Autocomplete
        options={options}
        inputValue={inputValue}
        loading={loading}
        filterOptions={(availableOptions) => availableOptions}
        onInputChange={(event, value) => setInputValue(value)}
        onChange={handleSelect}
        isOptionEqualToValue={(option, value) => option.site.site_id === value.site.site_id}
        renderOption={(props, option) => (
          <li {...props}>
            {isAuthenticated && option.favorite && (
              <FavoriteIcon fontSize="small" color="error" sx={{ mr: 1 }} />
            )}
            {option.label}
          </li>
        )}
        renderInput={(params) => (
          <TextField
            {...params}
            label="Search sites"
            variant="outlined"
            size={mobile ? "medium" : "small"}
            sx={{
              backgroundColor: 'white',
              borderRadius: '4px',
              '& .MuiOutlinedInput-root': {
                '& fieldset': {
                  borderColor: 'rgba(0, 0, 0, 0.23)',
                },
                '&:hover fieldset': {
                  borderColor: 'rgba(0, 0, 0, 0.87)',
                },
              },
            }}
          />
        )}
      />
    </Box>
  );
};

export default SearchBar;