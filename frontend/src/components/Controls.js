import React from 'react';
import { Select, MenuItem, FormControl, InputLabel } from '@mui/material';

const Controls = ({
  metrics,
  selectedMetric,
  setSelectedMetric,
  dates,
  selectedDate,
  setSelectedDate,
}) => {
  return (
    <div>
      <FormControl sx={{ m: 1, minWidth: 120 }}>
        <InputLabel>Metric</InputLabel>
        <Select
          value={selectedMetric}
          onChange={(e) => setSelectedMetric(e.target.value)}
          label="Metric"
        >
          {metrics.map((metric) => (
            <MenuItem key={metric} value={metric}>
              {metric}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      <FormControl sx={{ m: 1, minWidth: 120 }}>
        <InputLabel>Date</InputLabel>
        <Select
          value={selectedDate}
          onChange={(e) => setSelectedDate(e.target.value)}
          label="Date"
        >
          {dates.map((date) => (
            <MenuItem key={date} value={date}>
              {date}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    </div>
  );
};

export default Controls;