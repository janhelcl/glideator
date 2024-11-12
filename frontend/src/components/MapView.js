import React, { useMemo, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, LayersControl } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { useNavigate } from 'react-router-dom';
import L from 'leaflet';
import './MapView.css'; // Import the CSS for glowing markers

const { BaseLayer } = LayersControl;

// Fix default icon issues with Webpack
delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

const MapView = React.memo(({ sites, selectedMetric, selectedDate }) => {
  const navigate = useNavigate();

  // State to preserve map's center and zoom
  const [mapState, setMapState] = useState({
    center: [50.0755, 14.4378], // Adjust to your default center
    zoom: 7, // Adjust to your default zoom level
  });

  // Function to handle map movements
  const handleMoveEnd = (map) => {
    setMapState({
      center: map.getCenter(),
      zoom: map.getZoom(),
    });
  };

  // Function to convert RGB to RGBA with specified alpha
  const rgbToRgba = (rgb, alpha) => {
    const [r, g, b] = rgb.match(/\d+/g);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  };

  // Function to get the prediction value for the selected metric and date
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

  // Function to create a custom icon with CSS variables for styling
  const createCustomIcon = (color) => {
    const rgbaGlow = rgbToRgba(color, 0.7); // For default glow
    const rgbaGlowHover = rgbToRgba(color, 1); // For hover glow

    // Unique identifier for CSS variables
    const uniqueId = `marker-${Math.random().toString(36).substr(2, 9)}`;

    // Create a style tag to define CSS variables for this marker
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
      iconSize: [12, 12], // Match the CSS size
      iconAnchor: [6, 6],  // Center the icon
      popupAnchor: [0, -6],
    });
  };

  // Memoize markers to prevent unnecessary re-renders
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

  return (
    <MapContainer
      center={mapState.center}
      zoom={mapState.zoom}
      style={{ height: '80vh', width: '100%' }}
      whenCreated={(map) => {
        map.on('moveend', () => handleMoveEnd(map));
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
      {markers}
    </MapContainer>
  );
});

export default MapView;