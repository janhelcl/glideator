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

  // Helper: Create Temperature / Dewpoint Chart
  const createTempDewPlot = (forecast) => {
    return (
      <Plot
        data={[
          {
            x: forecast.temperature_iso_c,
            y: forecast.hpa_lvls,
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Temperature',
            line: { color: 'red' },
            hovertemplate: 'Temperature: %{x}°C<br>Pressure: %{y} hPa<extra></extra>',
          },
          {
            x: forecast.dewpoint_iso_c,
            y: forecast.hpa_lvls,
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Dewpoint',
            line: { color: 'blue' },
            hovertemplate: 'Dewpoint: %{x}°C<br>Pressure: %{y} hPa<extra></extra>',
          },
        ]}
        layout={{
          title: 'Temperature & Dewpoint',
          hovermode: 'y unified',
          xaxis: {
            title: '°C',
            zeroline: false,
            showgrid: false,
            tickfont: { size: 10 },
            titlefont: { size: 12 },
          },
          yaxis: {
            title: 'Pressure (hPa)',
            autorange: 'reversed',
            tickfont: { size: 10 },
            titlefont: { size: 12 },
          },
          margin: { l: 50, r: 30, b: 40, t: 40, pad: 4 },
          autosize: true,
          height: 300,
        }}
        config={{ responsive: true, displayModeBar: false }}
        style={{ width: '100%', height: '100%' }}
      />
    );
  };

  // Helper: Create Wind Speed / Direction Chart
  const createWindPlot = (forecast) => {
    const { wind_speed_iso_ms, wind_direction_iso_dgr, hpa_lvls } = forecast;
    const maxWindSpeed = Math.max(...wind_speed_iso_ms);
    const fixedArrowX = maxWindSpeed * 1.2;
    const arrowX = wind_speed_iso_ms.map(() => fixedArrowX);
    const arrowY = hpa_lvls;
    const arrowAngle = wind_direction_iso_dgr.map(angle => (angle + 180) % 360);

    return (
      <Plot
        data={[
          {
            x: wind_speed_iso_ms,
            y: hpa_lvls,
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Wind Speed',
            line: { color: 'green' },
            marker: { color: 'green', size: 8 },
            hovertemplate: 'Wind Speed: %{x} m/s<br>Pressure: %{y} hPa<extra></extra>',
          },
          {
            type: 'scatter',
            mode: 'markers',
            name: 'Wind Direction',
            x: arrowX,
            y: arrowY,
            marker: {
              symbol: 'arrow',
              size: 12,
              angleref: 0,
              angle: arrowAngle,
              color: '#ff7f0e',
            },
            customdata: wind_direction_iso_dgr,
            hovertemplate: 'Wind Direction: %{customdata}°<extra></extra>',
          },
        ]}
        layout={{
          title: 'Wind Speed & Direction',
          hovermode: 'y unified',
          xaxis: {
            title: 'Wind Speed (m/s)',
            zeroline: false,
            showgrid: false,
            tickfont: { size: 10 },
            titlefont: { size: 12 },
            range: [0, fixedArrowX + maxWindSpeed * 0.2],
          },
          yaxis: {
            title: 'Pressure (hPa)',
            autorange: 'reversed',
            tickfont: { size: 10 },
            titlefont: { size: 12 },
          },
          margin: { l: 50, r: 40, b: 40, t: 40, pad: 4 },
          autosize: true,
          height: 300,
        }}
        config={{ responsive: true, displayModeBar: false }}
        style={{ width: '100%', height: '100%' }}
      />
    );
  };

  // Helper: Create Relative Humidity Heatmap
  const createRelativeHumidityPlot = (forecast) => {
    const transformedZ = forecast.relative_humidity_iso_pct.map(rh => [rh]);
    return (
      <Plot
        data={[
          {
            z: transformedZ,
            x: ['Relative Humidity'],
            y: forecast.hpa_lvls,
            type: 'heatmap',
            colorscale: [
              [0, '#E0E0E0'],
              [0.5, '#A0A0A0'],
              [1, '#434343']
            ],
            colorbar: {
              title: 'RH (%)',
              titleside: 'top',
              ticks: 'outside',
              tick0: 0,
              dtick: 20,
              nticks: 6,
            },
            hovertemplate: 'Pressure: %{y} hPa<br>RH: %{z}%<extra></extra>',
            showscale: true,
          },
        ]}
        layout={{
          title: 'Relative Humidity',
          yaxis: {
            title: 'Pressure (hPa)',
            autorange: 'reversed',
            tickfont: { size: 10 },
            titlefont: { size: 12 },
          },
          xaxis: {
            showticklabels: false,
            showgrid: false,
          },
          margin: { l: 50, r: 60, b: 40, t: 40, pad: 4 },
          zmin: 0,
          zmax: 100,
          annotations: forecast.relative_humidity_iso_pct.map((rh, index) => ({
            x: 'Relative Humidity',
            y: forecast.hpa_lvls[index],
            text: `${Math.round(rh)}%`,
            showarrow: false,
            font: {
              color: rh > 50 ? 'white' : 'black',
              size: 10
            }
          })),
          autosize: true,
          height: 300,
        }}
        config={{ responsive: true, displayModeBar: false }}
        style={{ width: '100%', height: '100%' }}
      />
    );
  };

  // Render charts for the selected forecast hour
  const renderForecastCharts = () => {
    if (!forecastData) {
      return <Box>Loading forecast data...</Box>;
    }

    const forecast = forecastData[`forecast_${selectedHour}`];
    if (!forecast) {
      return <Box>No forecast data available for hour {selectedHour}.</Box>;
    }
    return (
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
        <Box sx={{ flex: 1, minWidth: { xs: '100%', sm: '300px' } }}>
          {createTempDewPlot(forecast)}
        </Box>
        <Box sx={{ flex: 1, minWidth: { xs: '100%', sm: '300px' } }}>
          {createWindPlot(forecast)}
        </Box>
        <Box sx={{ flex: 1, minWidth: { xs: '100%', sm: '300px' } }}>
          {createRelativeHumidityPlot(forecast)}
        </Box>
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
      }}
    >
      <Button
        variant="contained"
        onClick={() => setShowForecast(!showForecast)}
        fullWidth
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
                {hour}
              </Button>
            ))}
          </Box>
          {error ? <Box>{error}</Box> : renderForecastCharts()}
        </Box>
      </Collapse>
    </Box>
  );
};

export default ResponsiveForecast; 