import React, { useMemo, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, LayersControl, useMap } from 'react-leaflet';
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

// Component to handle map events and update shared state
const MapEventHandler = ({ setMapState }) => {
  const map = useMap();

  useEffect(() => {
    const handleMoveEnd = () => {
      const currentBounds = map.getBounds();
      console.log('Main map bounds:', currentBounds);
      
      setMapState({
        center: [map.getCenter().lat, map.getCenter().lng],
        zoom: map.getZoom(),
        bounds: currentBounds
      });
    };

    map.on('moveend', handleMoveEnd);
    handleMoveEnd();

    return () => {
      map.off('moveend', handleMoveEnd);
    };
  }, [map, setMapState]);

  return null;
};

// Component to synchronize small map views with main map
const SynchronizeMapView = ({ bounds }) => {
  const map = useMap();

  useEffect(() => {
    if (bounds) {
      console.log('Small map receiving bounds:', bounds);
      try {
        // Get the container size
        const container = map.getContainer();
        const containerWidth = container.clientWidth;
        const containerHeight = container.clientHeight;

        // Calculate the aspect ratio of the container
        const aspectRatio = containerWidth / containerHeight;

        // Calculate the bounds dimensions
        const boundsWidth = bounds.getEast() - bounds.getWest();
        const boundsHeight = bounds.getNorth() - bounds.getSouth();
        const boundsAspectRatio = boundsWidth / boundsHeight;

        // Calculate padding to maintain aspect ratio
        let padding;
        if (boundsAspectRatio > aspectRatio) {
          // Bounds are wider than container
          const heightDiff = (boundsHeight * (boundsAspectRatio / aspectRatio) - boundsHeight) / 2;
          padding = [-heightDiff * containerHeight, 0];
        } else {
          // Bounds are taller than container
          const widthDiff = (boundsWidth * (aspectRatio / boundsAspectRatio) - boundsWidth) / 2;
          padding = [0, -widthDiff * containerWidth];
        }

        map.fitBounds(bounds, {
          animate: false,
          padding: padding
        });
      } catch (error) {
        console.error('Error fitting bounds:', error);
      }
    }
  }, [bounds, map]);

  return null;
};

const MapView = React.memo(({
  sites,
  selectedMetric,
  setSelectedMetric,
  selectedDate,
  center,
  zoom,
  bounds,
  setMapState,
  isSmallMap = false,
  metrics,
}) => {
  const navigate = useNavigate();

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

  const handleSliderChange = (event, newValue) => {
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
      center={center}
      zoom={zoom}
      style={{ 
        height: isSmallMap ? '100px' : '100%', 
        width: isSmallMap ? '150px' : '100%',
        position: 'relative',
        minWidth: isSmallMap ? '150px' : 'auto',
        margin: 0,
        padding: 0
      }}
      dragging={!isSmallMap}
      scrollWheelZoom={!isSmallMap}
      zoomControl={!isSmallMap}
      doubleClickZoom={!isSmallMap}
      boxZoom={!isSmallMap}
      keyboard={!isSmallMap}
      tap={!isSmallMap}
      touchZoom={!isSmallMap}
      attributionControl={!isSmallMap}
      maxBoundsViscosity={1.0}
    >
      {/* Pass isSmallMap to SynchronizeMapView */}
      {isSmallMap && <SynchronizeMapView bounds={bounds} />}

      {/* Handle map state updates for the main map */}
      {!isSmallMap && setMapState && <MapEventHandler setMapState={setMapState} />}

      {/* Conditionally render LayersControl only on the main map */}
      {!isSmallMap ? (
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
      ) : (
        /* Render a default TileLayer without attribution on small maps */
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="" // No attribution for small maps
        />
      )}

      {/* Conditionally render the Metric Slider only on the main map */}
      {!isSmallMap && (
        <PreventLeafletControl>
          <Box
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
        </PreventLeafletControl>
      )}
      {markers}
    </MapContainer>
  );
});

export default MapView;
