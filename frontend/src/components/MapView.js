import React from 'react';
import { MapContainer, TileLayer, Marker, Popup, LayersControl } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { useNavigate } from 'react-router-dom';
import L from 'leaflet';
import './MapView.css'; // Import the CSS for glowing markers

const { BaseLayer } = LayersControl;

const MapView = ({ sites, selectedMetric, selectedDate }) => {
  const navigate = useNavigate();

  // Function to convert RGB to RGBA with specified alpha
  const rgbToRgba = (rgb, alpha) => {
    const [r, g, b] = rgb.match(/\d+/g);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  };

  const getColor = (probability) => {
    const p = Math.max(0, Math.min(1, probability));
    const r = Math.round(255 * (1 - p));
    const g = Math.round(255 * p);
    return `rgb(${r}, ${g}, 0)`;
  };

  const getPrediction = (site, metric) => {
    return site.predictions.find(pred => pred.metric === metric);
  };

  const getProbability = (site, metric) => {
    const prediction = getPrediction(site, metric);
    if (!prediction || prediction.value === undefined || isNaN(prediction.value)) {
      return 'N/A';
    }
    return `${(prediction.value * 100).toFixed(2)}%`;
  };

  const createCustomIcon = (color) => {
    const rgbaGlow = rgbToRgba(color, 0.7); // For default glow
    const rgbaGlowHover = rgbToRgba(color, 1); // For hover glow

    // Unique identifier for CSS variables (optional)
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

  return (
    <MapContainer center={[50.0755, 14.4378]} zoom={7} style={{ height: '80vh', width: '100%' }}>
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
      {sites.map((site) => {
        const prediction = getPrediction(site, selectedMetric);
        const probability = prediction ? prediction.value : 0;
        const color = getColor(probability);

        return (
          <Marker
            key={site.name}
            position={[site.latitude, site.longitude]}
            icon={createCustomIcon(color)}
          >
            <Popup>
              <strong>{site.name}</strong><br />
              Probability: {getProbability(site, selectedMetric)}<br />
              <button onClick={() => navigate(`/sites/${site.name}?date=${selectedDate}&metric=${selectedMetric}`)}>
                Details
              </button>
            </Popup>
          </Marker>
        );
      })}
    </MapContainer>
  );
};

export default MapView;