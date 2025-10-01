import React, { useState, useEffect } from 'react';
import { TextField, Autocomplete, Box } from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import FavoriteIcon from '@mui/icons-material/Favorite';

const SearchBar = ({ sites, onSiteSelect, mobile = false }) => {
  const [options, setOptions] = useState([]);
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, favorites } = useAuth();

  useEffect(() => {
    const sortedSites = sites && sites.length > 0
      ? [...sites].sort((a, b) => a.site_id - b.site_id)
      : [];

    const favoriteSet = new Set(favorites);
    const siteOptions = sortedSites.map(site => ({
      label: `${site.name} (${site.site_id})`,
      site,
      favorite: favoriteSet.has(site.site_id),
    }));
    setOptions(siteOptions);
  }, [sites, favorites]);

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
        onChange={handleSelect}
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