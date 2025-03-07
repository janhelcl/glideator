import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import { Box, Typography } from '@mui/material';
import { fetchSiteSpots } from '../api';

// Component to fit map bounds to all spots with max zoom limit
const FitBoundsToSpots = ({ spots }) => {
  const map = useMap();
  
  useEffect(() => {
    if (spots && spots.length > 0) {
      const bounds = L.latLngBounds(spots.map(spot => [spot.latitude, spot.longitude]));
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
      
      // Double-check that zoom is not higher than 15
      if (map.getZoom() > 15) {
        map.setZoom(15);
      }
    }
  }, [map, spots]);
  
  return null;
};

const SiteMap = ({ siteId, siteName }) => {
  const [spots, setSpots] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [defaultCenter, setDefaultCenter] = useState([50, 15]); // Default center

  useEffect(() => {
    const loadSpots = async () => {
      if (!siteId) return;
      
      setIsLoading(true);
      try {
        const spotsData = await fetchSiteSpots(siteId);
        setSpots(spotsData);
        
        // Calculate initial center for map
        if (spotsData.length > 0) {
          const lats = spotsData.map(spot => spot.latitude);
          const lngs = spotsData.map(spot => spot.longitude);
          const centerLat = (Math.max(...lats) + Math.min(...lats)) / 2;
          const centerLng = (Math.max(...lngs) + Math.min(...lngs)) / 2;
          setDefaultCenter([centerLat, centerLng]);
        }
      } catch (error) {
        console.error('Error loading spots:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadSpots();
  }, [siteId]);

  // Create takeoff icon - now with green color
  const createTakeoffIcon = () => {
    return L.divIcon({
      className: '',
      html: `
        <div style="position: relative; width: 24px; height: 24px;">
          <div style="
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: #4CAF50;
            border-radius: 50%;
            border: 2px solid white;
            box-shadow: 0 0 4px rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
          ">
            <div style="
              width: 0;
              height: 0;
              border-left: 5px solid transparent;
              border-right: 5px solid transparent;
              border-bottom: 8px solid white;
              margin-bottom: 2px;
            "></div>
          </div>
        </div>
      `,
      iconSize: [24, 24],
      iconAnchor: [12, 12],
      popupAnchor: [0, -12]
    });
  };

  // Create landing icon
  const createLandingIcon = () => {
    return L.divIcon({
      className: '',
      html: `
        <div style="position: relative; width: 24px; height: 24px;">
          <div style="
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: #4285f4;
            border-radius: 50%;
            border: 2px solid white;
            box-shadow: 0 0 4px rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
          ">
            <div style="
              width: 0;
              height: 0;
              border-left: 5px solid transparent;
              border-right: 5px solid transparent;
              border-top: 8px solid white;
              margin-top: 2px;
            "></div>
          </div>
        </div>
      `,
      iconSize: [24, 24],
      iconAnchor: [12, 12],
      popupAnchor: [0, -12]
    });
  };

  // Create icons once
  const takeoffIcon = createTakeoffIcon();
  const landingIcon = createLandingIcon();

  if (isLoading) {
    return <Box sx={{ p: 2 }}><Typography>Loading site spots...</Typography></Box>;
  }

  if (spots.length === 0) {
    return <Box sx={{ p: 2 }}><Typography>No takeoff or landing information available for this site.</Typography></Box>;
  }

  return (
    <Box sx={{ width: '100%', height: 400, borderRadius: 1, overflow: 'hidden' }}>
      <MapContainer 
        center={defaultCenter}
        zoom={14}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={true}
        zoomControl={false}
      >
        <TileLayer
          url="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png"
          attribution='Map data: &copy; <a href="https://www.openstreetmap.org">OpenTopoMap</a> contributors'
        />
        
        <FitBoundsToSpots spots={spots} />
        
        {spots.map(spot => (
          <Marker
            key={spot.spot_id}
            position={[spot.latitude, spot.longitude]}
            icon={spot.type === 'takeoff' ? takeoffIcon : landingIcon}
          >
            <Popup>
              <Typography variant="subtitle2">{spot.name}</Typography>
              <Typography variant="body2">Type: {spot.type.charAt(0).toUpperCase() + spot.type.slice(1)}</Typography>
              <Typography variant="body2">Altitude: {spot.altitude}m</Typography>
              {spot.wind_direction && (
                <Typography variant="body2">Wind direction: {spot.wind_direction}</Typography>
              )}
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </Box>
  );
};

export default SiteMap; 