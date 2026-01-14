import React, { useMemo, useCallback, useState, useRef, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import './MapView.css';
import L from 'leaflet';
import { Box, IconButton } from '@mui/material';
import MyLocationIcon from '@mui/icons-material/MyLocation';
import LayersIcon from '@mui/icons-material/Layers';
import { getColor } from '../utils/colorUtils';
import Sparkline from './Sparkline';
import PreventLeafletControl from './PreventLeafletControl';
import LoadingSpinner from './LoadingSpinner';

// Fix default icon issues with Webpack
delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

const PlannerMapView = ({ sites, onSiteClick, isVisible, maxSites = 10, selectedMetric = 'XC0', userLocation = null, loading = false }) => {
  const mapRef = useRef(null);
  const [mapType, setMapType] = useState('basic');
  const [hasInitialized, setHasInitialized] = useState(false);
  const previousBoundsRef = useRef(null);

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

  const handleSiteClick = useCallback((site, event) => {
    const url = `/details/${site.site_id}?metric=${selectedMetric}`;

    // Check if middle-click or ctrl/cmd-click
    if (event && (event.button === 1 || event.ctrlKey || event.metaKey)) {
      window.open(url, '_blank');
    } else {
      window.location.href = url;
    }
  }, [selectedMetric]);

  // Function to center map on user's location
  const handleLocationClick = () => {
    if ("geolocation" in navigator && mapRef && mapRef.current) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          const currentZoom = mapRef.current?.getZoom() || 10;
          mapRef.current?.setView([latitude, longitude], currentZoom);
        },
        (error) => {
          console.error("Error getting location:", error);
          alert("Unable to get your location. Please check your browser permissions.");
        }
      );
    } else {
      alert("Geolocation is not supported by your browser.");
    }
  };

  // Function to toggle between map types
  const toggleMapType = () => {
    setMapType(prevType => prevType === 'basic' ? 'topographic' : 'basic');
  };

  const markers = useMemo(() => {
    const siteMarkers = validSites.map((site, index) => {
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
                  onClick={(e) => handleSiteClick(site, e)}
                  onAuxClick={(e) => {
                    if (e.button === 1) {
                      e.preventDefault();
                      handleSiteClick(site, e);
                    }
                  }}
                >
                  View Details
                </button>
              </div>
            </div>
          </Popup>
        </Marker>
      );
    });

    // Add user location marker if available
    if (userLocation) {
      const userMarker = (
        <Marker
          key="user-location"
          position={[userLocation.latitude, userLocation.longitude]}
          icon={L.divIcon({
            className: '',
            html: `
              <div style="
                width: 16px;
                height: 16px;
                background-color: #2196f3;
                border: 3px solid white;
                border-radius: 50%;
                box-shadow: 0 0 10px rgba(33, 150, 243, 0.5);
              "></div>
            `,
            iconSize: [16, 16],
            iconAnchor: [8, 8],
            popupAnchor: [0, -8],
          })}
        >
          <Popup closeButton={false}>
            <div style={{ textAlign: 'center', padding: '4px' }}>
              <strong>Your Location</strong>
            </div>
          </Popup>
        </Marker>
      );
      
      return [...siteMarkers, userMarker];
    }

    return siteMarkers;
  }, [validSites, createColoredIcon, handleSiteClick, userLocation]);

  // Calculate bounds to fit all markers with validation
  const bounds = useMemo(() => {
    if (validSites.length === 0) {
      // If loading and we have previous bounds, keep them
      if (loading && previousBoundsRef.current) {
        return previousBoundsRef.current;
      }
      return null;
    }
    
    const latitudes = validSites.map(site => parseFloat(site.latitude)).filter(lat => !isNaN(lat));
    const longitudes = validSites.map(site => parseFloat(site.longitude)).filter(lng => !isNaN(lng));
    
    if (latitudes.length === 0 || longitudes.length === 0) {
      // If loading and we have previous bounds, keep them
      if (loading && previousBoundsRef.current) {
        return previousBoundsRef.current;
      }
      return null;
    }
    
    const minLat = Math.min(...latitudes);
    const maxLat = Math.max(...latitudes);
    const minLng = Math.min(...longitudes);
    const maxLng = Math.max(...longitudes);
    
    // Ensure we have valid bounds
    if (isNaN(minLat) || isNaN(maxLat) || isNaN(minLng) || isNaN(maxLng)) {
      // If loading and we have previous bounds, keep them
      if (loading && previousBoundsRef.current) {
        return previousBoundsRef.current;
      }
      return null;
    }
    
    const newBounds = [
      [minLat, minLng],
      [maxLat, maxLng]
    ];
    
    // Store the new bounds for future use
    previousBoundsRef.current = newBounds;
    
    return newBounds;
  }, [validSites, loading]);

  // Default center and zoom if no valid bounds
  const defaultCenter = [46.0569, 14.5058]; // Slovenia approximate center
  const defaultZoom = 8;
  
  // Effect to update map bounds when new data arrives
  useEffect(() => {
    if (mapRef.current && bounds && !loading && validSites.length > 0) {
      // Fit bounds to new data after loading is complete
      setTimeout(() => {
        mapRef.current?.fitBounds(bounds, { padding: [20, 20] });
      }, 100);
    }
  }, [bounds, loading, validSites.length]);
  
  // Track initialization
  useEffect(() => {
    if (validSites.length > 0 && !hasInitialized) {
      setHasInitialized(true);
    }
  }, [validSites.length, hasInitialized]);

  if (!isVisible) {
    return null;
  }

  // Always render the map container, even if no sites
  return (
    <div style={{
      height: '40vh',
      width: '100%',
      transition: 'height 0.3s ease',
      borderTop: '1px solid #ddd',
      position: 'relative'
    }}>
      {(validSites.length > 0 || loading) ? (
        <MapContainer
          center={!hasInitialized && !bounds ? defaultCenter : undefined}
          zoom={!hasInitialized && !bounds ? defaultZoom : undefined}
          bounds={bounds || undefined}
          style={{ height: '100%', width: '100%' }}
          scrollWheelZoom={true}
          boundsOptions={{ padding: [20, 20] }}
          zoomControl={false}
          ref={mapRef}
        >
          {/* Conditional TileLayer based on mapType */}
          {mapType === 'basic' ? (
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='Map data: &copy; <a href="https://www.openstreetmap.org">OpenStreetMap</a> contributors'
            />
          ) : (
            <TileLayer
              url="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png"
              attribution='Map data: &copy; <a href="https://www.openstreetmap.org">OpenTopoMap</a> contributors, SRTM | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (CC-BY-SA)'
            />
          )}
          
          {markers}

          {/* Location control */}
          <PreventLeafletControl>
            <Box
              className="map-controls-container"
            >
              <IconButton
                onClick={handleLocationClick}
                className="location-button"
                title="My Location"
              >
                <MyLocationIcon />
              </IconButton>
            </Box>
          </PreventLeafletControl>

          {/* Map type control */}
          <PreventLeafletControl>
            <Box
              className="map-type-control"
            >
              <IconButton
                onClick={toggleMapType}
                className="map-type-button"
                title={`Switch to ${mapType === 'basic' ? 'Topographic' : 'Basic'} Map`}
              >
                <LayersIcon />
              </IconButton>
            </Box>
          </PreventLeafletControl>
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
          {loading ? (
            <LoadingSpinner />
          ) : (
            'No valid sites to display on map'
          )}
        </div>
      )}
      
      {/* Loading overlay */}
      {loading && validSites.length > 0 && (
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          zIndex: 1000,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          backgroundColor: 'rgba(255, 255, 255, 0.8)',
          pointerEvents: 'none'
        }}>
          <LoadingSpinner />
        </div>
      )}
    </div>
  );
};

export default PlannerMapView; 