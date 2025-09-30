import React, { useState, useEffect } from 'react';
import { TextField, Autocomplete, Box } from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import FavoriteIcon from '@mui/icons-material/Favorite';

const SearchBar = ({ sites, onSiteSelect }) => {
  const [options, setOptions] = useState([]);
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, isFavorite } = useAuth();

  useEffect(() => {
    // Transform sites into options format, sorting by site_id first
    const sortedSites = sites && sites.length > 0
      ? [...sites].sort((a, b) => a.site_id - b.site_id) // Sort by site_id (numeric)
      : [];

    const siteOptions = sortedSites.map(site => ({
      label: `${site.name} (${site.site_id})`,
      site,
      favorite: isFavorite(site.site_id),
    }));
    setOptions(siteOptions);
  }, [sites]);

  const handleSelect = (event, value) => {
    if (!value) return;

    // Get current URL parameters
    const currentParams = new URLSearchParams(location.search);
    
    if (location.pathname === '/') {
      // On Home page - keep existing behavior
      onSiteSelect(value.site);
    } else {
      // On other pages - navigate to Details page
      // Preserve current URL parameters when navigating
      navigate(`/details/${value.site.site_id}?${currentParams.toString()}`);
    }
  };

  return (
    <Box sx={{ width: 300, margin: '0 20px' }}>
      <Autocomplete
        options={options}
        onChange={handleSelect}
        renderInput={(params) => (
          <TextField
            {...params}
            label="Search sites"
            variant="outlined"
            size="small"
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
        renderOption={(props, option) => (
          <li {...props}>
            {isAuthenticated && option.favorite && (
              <FavoriteIcon fontSize="small" color="error" sx={{ mr: 1 }} />
            )}
            {option.label}
          </li>
        )}
      />
    </Box>
  );
};

export default SearchBar;