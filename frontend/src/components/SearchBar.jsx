import React, { useState, useEffect } from 'react';
import { TextField, Autocomplete, Box } from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';

const SearchBar = ({ sites, onSiteSelect }) => {
  const [options, setOptions] = useState([]);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    // Transform sites into options format
    const siteOptions = sites.map(site => ({
      label: `${site.name} (${site.site_id})`,
      site: site
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
      navigate(`/sites/${value.site.site_id}?${currentParams.toString()}`);
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
      />
    </Box>
  );
};

export default SearchBar;