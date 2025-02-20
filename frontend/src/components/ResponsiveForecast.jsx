import React, { useState, useEffect } from 'react';
import { Button, Box, Collapse } from '@mui/material';
import Plot from 'react-plotly.js';
import { fetchSiteForecast } from '../api';

const ResponsiveForecast = ({ siteId, queryDate }) => {
  // State to toggle forecast visibility
  const [showForecast, setShowForecast] = useState(false);
  // Hold the fetched forecast data
  const [forecastData, setForecastData] = useState(null);
  const [error, setError] = useState(null);
  // Selected forecast hour (9, 12, or 15)
  const [selectedHour, setSelectedHour] = useState(9);

  // Fetch forecast data when siteId or queryDate changes
  useEffect(() => {
    const loadForecast = async () => {
      try {
        const data = await fetchSiteForecast(siteId, queryDate);
        setForecastData(data);
      } catch (err) {
        console.error("Error fetching forecast:", err);
        setError("Failed to load forecast data.");
      }
    };

    if (siteId && queryDate) {
      loadForecast();
    }
  }, [siteId, queryDate]);

  const createCombinedPlot = (forecast) => {
    // Calculate the temperature range for RH markers positioning
    const maxTemp = Math.max(...forecast.temperature_iso_c);
    const rhPosition = maxTemp + 5; // Place RH markers 5 degrees to the right of max temp

    return (
      <Plot
        data={[
          // Temperature line
          {
            x: forecast.temperature_iso_c,
            y: forecast.hpa_lvls,
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Temperature',
            line: { color: 'red', width: 2 },
            marker: { size: 6 },
            hovertemplate: 'Temperature: %{x}°C<br>Pressure: %{y} hPa<extra></extra>',
          },
          // Dewpoint line
          {
            x: forecast.dewpoint_iso_c,
            y: forecast.hpa_lvls,
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Dewpoint',
            line: { color: 'blue', width: 2, dash: 'dot' },
            marker: { size: 6 },
            hovertemplate: 'Dewpoint: %{x}°C<br>Pressure: %{y} hPa<extra></extra>',
          },
          // Wind arrows
          {
            type: 'scatter',
            mode: 'markers',
            name: 'Wind',
            x: forecast.wind_speed_iso_ms,
            y: forecast.hpa_lvls,
            marker: {
              symbol: 'arrow',
              size: 12,
              angle: forecast.wind_direction_iso_dgr.map(angle => (angle + 180) % 360),
              color: 'green',
            },
            hovertemplate: 
              'Wind Speed: %{x} m/s<br>' +
              'Direction: %{customdata}°<br>' +
              'Pressure: %{y} hPa<extra></extra>',
            customdata: forecast.wind_direction_iso_dgr,
          },
          // Relative Humidity as colored markers
          {
            type: 'scatter',
            mode: 'markers',
            name: 'RH',
            x: Array(forecast.hpa_lvls.length).fill(rhPosition),
            y: forecast.hpa_lvls,
            marker: {
              size: 20,
              color: forecast.relative_humidity_iso_pct,
              colorscale: [
                [0, 'rgb(255,255,255)'],
                [0.5, 'rgb(166,206,227)'],
                [1, 'rgb(31,120,180)']
              ],
              showscale: true,
              colorbar: {
                title: 'Relative Humidity %',
                x: 1.15,
                thickness: 15,
              }
            },
            text: forecast.relative_humidity_iso_pct.map(rh => `${Math.round(rh)}%`),
            textposition: 'middle center',
            textfont: {
              color: forecast.relative_humidity_iso_pct.map(rh => rh > 50 ? 'white' : 'black'),
              size: 10,
            },
            hovertemplate: 'RH: %{marker.color}%<br>Pressure: %{y} hPa<extra></extra>',
          }
        ]}
        layout={{
          title: `Atmospheric Profile - ${selectedHour}:00`,
          hovermode: 'closest',
          xaxis: {
            title: 'Temperature (°C) / Wind Speed (m/s)',
            zeroline: false,
            showgrid: true,
            gridcolor: 'rgba(0,0,0,0.1)',
          },
          yaxis: {
            title: 'Pressure (hPa)',
            autorange: 'reversed',
            showgrid: true,
            gridcolor: 'rgba(0,0,0,0.1)',
          },
          showlegend: true,
          legend: {
            x: 0,
            y: 1,
            orientation: 'h',
          },
          margin: { 
            l: 60, 
            r: 80, 
            t: 40, 
            b: 60 
          },
          height: 500,
          plot_bgcolor: 'white',
          paper_bgcolor: 'white',
        }}
        config={{ 
          responsive: true, 
          displayModeBar: false,
        }}
        style={{
          width: '100%',
          height: '100%',
        }}
      />
    );
  };

  const renderForecast = () => {
    if (!forecastData) {
      return <Box>Loading forecast data...</Box>;
    }

    const forecast = forecastData[`forecast_${selectedHour}`];
    if (!forecast) {
      return <Box>No forecast data available for hour {selectedHour}.</Box>;
    }

    return (
      <Box sx={{ width: '100%', mt: 2 }}>
        {createCombinedPlot(forecast)}
      </Box>
    );
  };

  return (
    <Box
      sx={{
        my: 2,
        p: 2,
        border: '1px solid #e0e0e0',
        borderRadius: 1,
        boxShadow: 1,
        bgcolor: 'background.paper',
      }}
    >
      <Button
        variant="contained"
        onClick={() => setShowForecast(!showForecast)}
        fullWidth
        sx={{ mb: showForecast ? 2 : 0 }}
      >
        {showForecast ? "Hide GFS Forecast" : "Show GFS Forecast"}
      </Button>
      
      <Collapse in={showForecast}>
        <Box sx={{ mt: 2 }}>
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'center',
              gap: 1,
              mb: 2,
            }}
          >
            {[9, 12, 15].map((hour) => (
              <Button
                key={hour}
                variant={selectedHour === hour ? "contained" : "outlined"}
                onClick={() => setSelectedHour(hour)}
              >
                {hour}:00
              </Button>
            ))}
          </Box>
          {error ? <Box>{error}</Box> : renderForecast()}
        </Box>
      </Collapse>
    </Box>
  );
};

export default ResponsiveForecast; 