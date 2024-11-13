import React, { useMemo, useState, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, LayersControl } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { useNavigate } from 'react-router-dom';
import L from 'leaflet';
import './MapView.css';
import { Slider, Typography, Box } from '@mui/material';
import PreventLeafletControl from './PreventLeafletControl';

const { BaseLayer } = LayersControl;

// Fix default icon issues with Webpack
delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

const MapView = React.memo(({ sites, selectedMetric, setSelectedMetric, selectedDate, metrics }) => {
  const navigate = useNavigate();

  const [mapState, setMapState] = useState({
    center: [50.0755, 14.4378],
    zoom: 7,
  });

  const handleMoveEnd = (map) => {
    setMapState({
      center: map.getCenter(),
      zoom: map.getZoom(),
    });
  };

  const rgbToRgba = (rgb, alpha) => {
    const [r, g, b] = rgb.match(/\d+/g);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  };

  const getPredictionValue = (site) => {
    const prediction = site.predictions.find(
      (pred) => pred.metric === selectedMetric && pred.date === selectedDate
    );
    return prediction ? prediction.value : 'N/A';
  };

  const getColor = (probability) => {
    const p = Math.max(0, Math.min(1, probability));
    const r = Math.round(255 * (1 - p));
    const g = Math.round(255 * p);
    return `rgb(${r}, ${g}, 0)`;
  };

  const createCustomIcon = (color) => {
    const rgbaGlow = rgbToRgba(color, 0.7);
    const rgbaGlowHover = rgbToRgba(color, 1);
    const uniqueId = `marker-${Math.random().toString(36).substr(2, 9)}`;

    const styleTag = `
      <style>
        #${uniqueId} {
          --marker-color: ${color};
          --marker-glow-color: ${rgbaGlow};
          --marker-glow-hover-color: ${rgbaGlowHover};
        }
      </style>
    `;

    return L.divIcon({
      className: '',
      html: `
        ${styleTag}
        <div class="glowing-marker" id="${uniqueId}">
          <div class="glow"></div>
          <div class="point"></div>
        </div>
      `,
      iconSize: [12, 12],
      iconAnchor: [6, 6],
      popupAnchor: [0, -6],
    });
  };

  const markers = useMemo(() => {
    return sites.map((site) => {
      const probability = getPredictionValue(site);
      const color = probability !== 'N/A' ? getColor(probability) : 'gray';

      return (
        <Marker
          key={`${site.name}-${site.latitude}-${site.longitude}`}
          position={[site.latitude, site.longitude]}
          icon={createCustomIcon(color)}
        >
          <Popup>
            <strong>{site.name}</strong><br />
            Probability: {probability !== 'N/A' ? probability.toFixed(2) : 'N/A'}<br />
            <button onClick={() => navigate(`/sites/${encodeURIComponent(site.name)}?date=${selectedDate}&metric=${selectedMetric}`)}>
              Details
            </button>
          </Popup>
        </Marker>
      );
    });
  }, [sites, selectedMetric, selectedDate, navigate]);

  const sliderRef = useRef(null);

  const handleSliderChange = (event, newValue) => {
    event.stopPropagation();
    if (newValue >= 0 && newValue < metrics.length) {
      setSelectedMetric(metrics[newValue]);
    }
  };

  const sliderValue = metrics.indexOf(selectedMetric);
  const marks = metrics.map((metric, index) => ({
    value: index,
    label: metric,
  }));

  return (
    <MapContainer
      center={mapState.center}
      zoom={mapState.zoom}
      style={{ height: '80vh', width: '100%', position: 'relative' }}
      whenCreated={(map) => {
        map.on('moveend', () => handleMoveEnd(map));

        // Initial disable of click and scroll propagation for the slider container
        const sliderContainer = sliderRef.current;
        if (sliderContainer) {
          L.DomEvent.disableClickPropagation(sliderContainer);
          L.DomEvent.disableScrollPropagation(sliderContainer);
        }
      }}
    >
      <LayersControl position="topright">
        <BaseLayer checked name="Basic">
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='Map data: &copy; <a href="https://www.openstreetmap.org">OpenStreetMap</a> contributors'
          />
        </BaseLayer>
        <BaseLayer name="Topographic">
          <TileLayer
            url="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png"
            attribution='Map data: &copy; <a href="https://www.opentopomap.org">OpenTopoMap</a> contributors, SRTM | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (CC-BY-SA)'
          />
        </BaseLayer>
      </LayersControl>

      <PreventLeafletControl>
        <div className="metric-slider-container">
          <div className="metric-slider-wrapper">
            <Box
              ref={sliderRef}
              className="metric-slider"
              sx={{
                '& *': {
                  pointerEvents: 'auto !important'
                }
              }}
            >
              <Typography variant="subtitle1" gutterBottom>
                Select Metric
              </Typography>
              <Slider
                orientation="vertical"
                value={sliderValue === -1 ? 0 : sliderValue}
                min={0}
                max={metrics.length - 1}
                step={1}
                marks={marks}
                onChange={handleSliderChange}
                valueLabelDisplay="off"
                aria-labelledby="metric-slider"
              />
            </Box>
          </div>
        </div>
      </PreventLeafletControl>

      {markers}
    </MapContainer>
  );
});

export default MapView;
