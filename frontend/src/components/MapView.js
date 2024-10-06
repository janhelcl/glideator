import React from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { useNavigate } from 'react-router-dom';

const MapView = ({ sites, selectedMetric }) => {
  const navigate = useNavigate();

  const getColor = (probability) => {
    // Ensure probability is between 0 and 1
    const p = Math.max(0, Math.min(1, probability));
    
    // Calculate RGB values
    const r = Math.round(255 * (1 - p));
    const g = Math.round(255 * p);
    
    // Return color in RGB format
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

  return (
    <MapContainer center={[50.0755, 14.4378]} zoom={7} style={{ height: '80vh', width: '100%' }}>
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution="&copy; OpenStreetMap contributors"
      />
      {sites.map((site) => {
        const prediction = getPrediction(site, selectedMetric);
        const probability = prediction ? prediction.value : 0;
        return (
          <CircleMarker
            key={site.name}
            center={[site.latitude, site.longitude]}
            radius={10}
            color={getColor(probability)}
          >
            <Popup>
              <strong>{site.name}</strong><br />
              Probability: {getProbability(site, selectedMetric)}<br />
              <button onClick={() => navigate(`/sites/${site.name}`)}>Details</button>
            </Popup>
          </CircleMarker>
        );
      })}
    </MapContainer>
  );
};

export default MapView;