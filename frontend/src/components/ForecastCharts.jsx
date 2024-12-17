import React, { useEffect, useState } from 'react';
import Plot from 'react-plotly.js';
import { fetchSiteForecast } from '../api';
import './ForecastCharts.css'; // Ensure CSS is imported

const ForecastCharts = ({ siteId, queryDate }) => {
  const [forecastData, setForecastData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadForecastData = async () => {
      try {
        const data = await fetchSiteForecast(siteId, queryDate);
        setForecastData(data);
      } catch (err) {
        console.error("Error fetching forecast data:", err);
        setError("Failed to load forecast data.");
      }
    };
    loadForecastData();
  }, [siteId, queryDate]);

  if (error) {
    return <div>{error}</div>;
  }

  if (!forecastData) {
    return <div>Loading forecast data...</div>;
  }

  // Function to create Temperature and Dewpoint Plot
  const createTempDewPlot = (forecast, title) => {
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
          title: title,
          hovermode: 'y unified',
          xaxis: { 
            title: 'Temperature / Dewpoint (°C)',
            zeroline: false,
            showgrid: false,
            tickfont: { size: 12 },
            titlefont: { size: 14 },
          },
          yaxis: { 
            title: 'Pressure (hPa)', 
            autorange: 'reversed',
            tickfont: { size: 12 },
            titlefont: { size: 14 },
          },
          margin: { l: 60, r: 40, b: 50, t: 60, pad: 4 },
          autosize: true,
        }}
        config={{ responsive: true }}
        className="temp-dew-chart"
        style={{ width: '100%', height: '100%' }}
      />
    );
  };

  // Function to create Wind Speed and Direction Plot
  const createWindPlot = (forecast, title) => {
    const { wind_speed_iso_ms, wind_direction_iso_dgr, hpa_lvls } = forecast;

    // Calculate the maximum wind speed to position arrows on the right
    const maxWindSpeed = Math.max(...wind_speed_iso_ms);

    // Set all arrow X positions to a fixed value on the right side
    const fixedArrowX = maxWindSpeed * 1.2; // Adjust the multiplier as needed
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
            // Add original wind directions as customdata for tooltips
            customdata: wind_direction_iso_dgr,
            hovertemplate: 'Wind Direction: %{customdata}°<extra></extra>',
          },
        ]}
        layout={{
          title: title,
          hovermode: 'y unified',
          xaxis: { 
            title: 'Wind Speed (m/s)', 
            zeroline: false,
            showgrid: false,
            tickfont: { size: 12 },
            titlefont: { size: 14 },
            range: [0, fixedArrowX + maxWindSpeed * 0.2], // Ensure arrows are visible
          },
          yaxis: { 
            title: 'Pressure (hPa)', 
            autorange: 'reversed',
            tickfont: { size: 12 },
            titlefont: { size: 14 },
          },
          margin: { l: 60, r: 60, b: 50, t: 60, pad: 4 },
          autosize: true,
        }}
        config={{ responsive: true }}
        className="wind-chart"
        style={{ width: '100%', height: '100%' }}
      />
    );
  };

  // **Updated Function:** Create Relative Humidity Heatmap
  const createRelativeHumidityPlot = (forecast, title) => {
    // Transform z to be an Nx1 matrix for a vertical heatmap
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
              [0, '#E0E0E0'], // Light Gray for 0% RH
              [0.5, '#A0A0A0'], // Medium Gray for 50% RH
              [1, '#434343'] // Dark Gray for 100% RH
            ],
            colorbar: {
              title: 'RH (%)',
              titleside: 'top',
              ticks: 'outside',
              tick0: 0,
              dtick: 20,
              nticks: 6, // Ensures ticks at 0, 20, 40, 60, 80, 100
            },
            hovertemplate: 'Pressure: %{y} hPa<br>Relative Humidity: %{z}%<extra></extra>',
            showscale: true, // Display color scale for contextual reference
          },
        ]}
        layout={{
          title: title,
          yaxis: { 
            title: 'Pressure (hPa)', 
            autorange: 'reversed',
            tickfont: { size: 12 },
            titlefont: { size: 14 },
          },
          xaxis: { 
            title: '', 
            showticklabels: false, 
            showgrid: false 
          },
          margin: { l: 60, r: 80, b: 50, t: 60, pad: 4 }, // Increased right margin for colorbar
          zmin: 0, // Define the minimum RH value
          zmax: 100, // Define the maximum RH value
          annotations: forecast.relative_humidity_iso_pct.map((rh, index) => ({
            x: 'Relative Humidity',
            y: forecast.hpa_lvls[index],
            text: `${Math.round(rh)}%`, // **Rounded RH Values**
            showarrow: false,
            font: {
              color: rh > 50 ? 'white' : 'black', // Ensure text readability
              size: 12
            }
          })),
          autosize: true,
        }}
        config={{ responsive: true }}
        className="relative-humidity-chart"
        style={{ width: '100%', height: '100%' }}
      />
    );
  };

  // Helper function to render plots for each forecast
  const renderForecastPlots = (forecast, forecastLabel) => {
    return (
      <div className="forecast-row" key={forecastLabel}>
        <div className="plot-container">
          {createTempDewPlot(forecast, `${forecastLabel} - Temperature & Dewpoint`)}
        </div>
        <div className="plot-container">
          {createWindPlot(forecast, `${forecastLabel} - Wind Speed & Direction`)}
        </div>
        <div className="plot-container">
          {createRelativeHumidityPlot(forecast, `${forecastLabel} - Relative Humidity`)}
        </div>
      </div>
    );
  };

  return (
    <div className="forecast-charts">
      <h2>
        Forecast Charts for Site ID {siteId} on {queryDate}
      </h2>
      {forecastData.forecast_9 && renderForecastPlots(forecastData.forecast_9, 'Forecast 9')}
      {forecastData.forecast_12 && renderForecastPlots(forecastData.forecast_12, 'Forecast 12')}
      {forecastData.forecast_15 && renderForecastPlots(forecastData.forecast_15, 'Forecast 15')}
    </div>
  );
};

export default ForecastCharts;
