import React, { useState, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import { Box, Typography } from '@mui/material';
import { fetchSiteSpots } from '../api';
import './MapView.css'; // Import the MapView.css for popup styling

// Wind Direction Icon Component
const WindDirectionIcon = ({ direction }) => {
  // Map cardinal directions to degrees (clockwise from top)
  const directionToDegrees = {
    'N': 0,
    'NNE': 22.5,
    'NE': 45,
    'ENE': 67.5,
    'E': 90,
    'ESE': 112.5,
    'SE': 135,
    'SSE': 157.5,
    'S': 180,
    'SSW': 202.5,
    'SW': 225,
    'WSW': 247.5,
    'W': 270,
    'WNW': 292.5,
    'NW': 315,
    'NNW': 337.5
  };

  const parseDirection = (dirString) => {
    if (!dirString) return { start: 0, end: 0 };
    
    // Handle single direction
    if (!dirString.includes('-')) {
      const deg = directionToDegrees[dirString] || 0;
      return { start: deg - 22.5, end: deg + 22.5 }; // 45-degree segment centered on the direction
    }
    
    // Handle direction range
    const [start, end] = dirString.split('-');
    let startDeg = directionToDegrees[start] || 0;
    let endDeg = directionToDegrees[end] || 0;
    
    // Calculate the number of 45-degree segments
    const segmentCount = (endDeg - startDeg) / 45 + 1;
    const totalDegrees = segmentCount * 45;
    
    // Adjust start and end to center the segments
    startDeg -= (totalDegrees - (endDeg - startDeg)) / 2;
    endDeg = startDeg + totalDegrees;
    
    // Ensure clockwise arc
    if (endDeg < startDeg) {
      endDeg += 360;
    }
    
    return { start: startDeg, end: endDeg };
  };

  const { start, end } = parseDirection(direction);
  
  // Size and center of the circle
  const size = 40;
  const center = size / 2;
  const radius = size / 2 - 4; // Slightly smaller than half size for padding
  
  // Calculate arc coordinates
  const startRad = (start - 90) * Math.PI / 180; // Convert to radians, adjust for SVG coordinate system
  const endRad = (end - 90) * Math.PI / 180;
  
  // Calculate start and end points
  const startX = center + radius * Math.cos(startRad);
  const startY = center + radius * Math.sin(startRad);
  const endX = center + radius * Math.cos(endRad);
  const endY = center + radius * Math.sin(endRad);
  
  // Determine if arc should take the long way around (more than 180 degrees)
  const largeArcFlag = end - start > 180 ? 1 : 0;
  
  // Create SVG path for the arc
  const arcPath = `M ${center} ${center} L ${startX} ${startY} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${endX} ${endY} Z`;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ display: 'inline-block', verticalAlign: 'middle', marginLeft: '5px' }}>
      {/* Outer circle */}
      <circle cx={center} cy={center} r={radius} stroke="#ccc" strokeWidth="1" fill="white" />
      
      {/* Cardinal direction markers */}
      <text x={center} y={6} fontSize="8" textAnchor="middle" fill="#666">N</text>
      <text x={size - 3} y={center + 3} fontSize="8" textAnchor="middle" fill="#666">E</text>
      <text x={center} y={size - 2} fontSize="8" textAnchor="middle" fill="#666">S</text>
      <text x={3} y={center + 3} fontSize="8" textAnchor="middle" fill="#666">W</text>
      
      {/* Direction arc */}
      <path d={arcPath} fill="rgba(66, 133, 244, 0.5)" stroke="rgba(66, 133, 244, 0.8)" strokeWidth="1" />
      
      {/* Center dot */}
      <circle cx={center} cy={center} r={2} fill="#333" />
    </svg>
  );
};

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
            <Popup closeButton={false} className="custom-popup">
              <div className="popup-content">
                <div className="popup-header">
                  <h3>{spot.name} ({spot.type})</h3>
                </div>
                <div className="popup-metric-bar">
                  <div style={{ 
                    textAlign: 'center',
                    padding: '2px 6px',
                    fontSize: '11px',
                    fontWeight: 500
                  }}>
                    <div style={{ whiteSpace: 'nowrap' }}>Altitude: {spot.altitude}m</div>
                    {spot.wind_direction && spot.type === 'takeoff' && (
                      <div style={{ 
                        marginTop: '2px', 
                        whiteSpace: 'nowrap',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                      }}>
                        <span>Wind: {spot.wind_direction}</span>
                        <WindDirectionIcon direction={spot.wind_direction} />
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </Box>
  );
};

export default SiteMap; 