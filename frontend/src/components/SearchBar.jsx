import React, { useState, useEffect } from 'react';
import { TextField, Autocomplete, Box } from '@mui/material';

const SearchBar = ({ sites, onSiteSelect }) => {
  const [options, setOptions] = useState([]);

  useEffect(() => {
    // Transform sites into options format
    const siteOptions = sites.map(site => ({
      label: `${site.name} (${site.site_id})`,
      site: site
    }));
    setOptions(siteOptions);
  }, [sites]);

  const handleSelect = (event, value) => {
    if (value) {
      // Only center map and open popup
      onSiteSelect(value.site);
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