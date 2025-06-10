import React, { useMemo, useCallback } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import './MapView.css';
import L from 'leaflet';
import { getColor } from '../utils/colorUtils';
import Sparkline from './Sparkline';

// Fix default icon issues with Webpack
delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

const PlannerMapView = ({ sites, onSiteClick, isVisible, maxSites = 10 }) => {
  // Validate and filter sites with valid coordinates
  const validSites = useMemo(() => {
    if (!sites || sites.length === 0) return [];
    
    const filtered = sites.filter(site => {
      const lat = parseFloat(site.latitude);
      const lng = parseFloat(site.longitude);
      const isValid = !isNaN(lat) && !isNaN(lng) && lat !== null && lng !== null;
      
      return isValid;
    }).slice(0, maxSites);
    
    return filtered;
  }, [sites, maxSites]);

  // Create color-coded markers using the same glowing marker system as main MapView
  const createColoredIcon = useCallback((probability) => {
    const color = getColor(probability);
    const rgbaGlow = color.replace('rgb', 'rgba').replace(')', ', 0.7)');
    const rgbaGlowHover = color.replace('rgb', 'rgba').replace(')', ', 1)');
    const uniqueId = `planner-marker-${Math.random().toString(36).substr(2, 9)}`;

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
  }, []);

  const handleSiteClick = useCallback((site) => {
    // Open site details in new tab with XC0 selected
    const url = `/details/${site.site_id}?metric=XC0`;
    window.open(url, '_blank');
  }, []);

  const markers = useMemo(() => {
    return validSites.map((site, index) => {
      const lat = parseFloat(site.latitude);
      const lng = parseFloat(site.longitude);
      
      return (
        <Marker
          key={`planner-site-${site.site_id}`}
          position={[lat, lng]}
          icon={createColoredIcon(site.average_flyability)}
        >
          <Popup closeButton={false} className="custom-popup">
            <div className="popup-content">
              <div className="popup-header">
                <h3>#{index + 1} {site.site_name}</h3>
              </div>
              <div className="popup-metric-bar">
                <div className="popup-metric-value">
                  <Sparkline dailyProbabilities={site.daily_probabilities} />
                </div>
              </div>
              <div className="popup-footer">
                <button
                  className="popup-details-button"
                  onClick={() => handleSiteClick(site)}
                >
                  View Details
                </button>
              </div>
            </div>
          </Popup>
        </Marker>
      );
    });
  }, [validSites, createColoredIcon, handleSiteClick]);

  // Calculate bounds to fit all markers with validation
  const bounds = useMemo(() => {
    if (validSites.length === 0) return null;
    
    const latitudes = validSites.map(site => parseFloat(site.latitude)).filter(lat => !isNaN(lat));
    const longitudes = validSites.map(site => parseFloat(site.longitude)).filter(lng => !isNaN(lng));
    
    if (latitudes.length === 0 || longitudes.length === 0) return null;
    
    const minLat = Math.min(...latitudes);
    const maxLat = Math.max(...latitudes);
    const minLng = Math.min(...longitudes);
    const maxLng = Math.max(...longitudes);
    
    // Ensure we have valid bounds
    if (isNaN(minLat) || isNaN(maxLat) || isNaN(minLng) || isNaN(maxLng)) {
      return null;
    }
    
    return [
      [minLat, minLng],
      [maxLat, maxLng]
    ];
  }, [validSites]);

  // Default center and zoom if no valid bounds
  const defaultCenter = [46.0569, 14.5058]; // Slovenia approximate center
  const defaultZoom = 8;

  if (!isVisible) {
    return null;
  }

  // Always render the map container, even if no sites
  return (
    <div style={{
      height: '40vh',
      width: '100%',
      transition: 'height 0.3s ease',
      borderTop: '1px solid #ddd'
    }}>
      {validSites.length > 0 ? (
        <MapContainer
          key={`map-${validSites.length}`} // Force re-render when sites change
          center={bounds ? undefined : defaultCenter}
          zoom={bounds ? undefined : defaultZoom}
          bounds={bounds || undefined}
          style={{ height: '100%', width: '100%' }}
          scrollWheelZoom={true}
          boundsOptions={{ padding: [20, 20] }}
          zoomControl={false}
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='Map data: &copy; <a href="https://www.openstreetmap.org">OpenStreetMap</a> contributors'
          />
          {markers}
        </MapContainer>
      ) : (
        <div style={{ 
          height: '100%', 
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#f5f5f5',
          color: '#666',
          border: '1px solid #ddd'
        }}>
          No valid sites to display on map
        </div>
      )}
    </div>
  );
};

export default PlannerMapView; 