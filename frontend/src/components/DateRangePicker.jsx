import React from 'react';
import { Box, Button, TextField } from '@mui/material';

const DateRangePicker = ({ startDate, endDate, onStartDateChange, onEndDateChange, onSearch, loading }) => {
  // Convert Date objects to string format for input fields
  const formatDateForInput = (date) => {
    if (!date) return '';
    return date.toISOString().split('T')[0];
  };

  // Convert string from input to Date object
  const handleStartDateChange = (event) => {
    const dateStr = event.target.value;
    if (dateStr) {
      onStartDateChange(new Date(dateStr));
    } else {
      onStartDateChange(null);
    }
  };

  const handleEndDateChange = (event) => {
    const dateStr = event.target.value;
    if (dateStr) {
      onEndDateChange(new Date(dateStr));
    } else {
      onEndDateChange(null);
    }
  };

  return (
    <Box 
      sx={{ 
        display: 'flex', 
        gap: 2, 
        alignItems: 'center',
        flexWrap: 'wrap',
        mb: 3
      }}
    >
      <TextField
        label="Start Date"
        type="date"
        value={formatDateForInput(startDate)}
        onChange={handleStartDateChange}
        size="small"
        sx={{ minWidth: 150 }}
        InputLabelProps={{
          shrink: true,
        }}
      />
      <TextField
        label="End Date"
        type="date"
        value={formatDateForInput(endDate)}
        onChange={handleEndDateChange}
        inputProps={{
          min: formatDateForInput(startDate)
        }}
        size="small"
        sx={{ minWidth: 150 }}
        InputLabelProps={{
          shrink: true,
        }}
      />
      <Button
        variant="contained"
        onClick={onSearch}
        disabled={loading || !startDate || !endDate}
        sx={{ 
          px: 3,
          height: 40,
          backgroundColor: '#1976d2',
          '&:hover': {
            backgroundColor: '#1565c0'
          }
        }}
      >
        {loading ? 'Planning...' : 'GO'}
      </Button>
    </Box>
  );
};

export default DateRangePicker; 