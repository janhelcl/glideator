import React, { useMemo, useEffect, useState, useTransition } from 'react';
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
  getMarkerRef,
  mapRef,
}) => {
  const navigate = useNavigate();

  // Initialize useTransition
  const [isPending, startTransition] = useTransition();

  // Local state for slider value
  const [localSliderValue, setLocalSliderValue] = useState(metrics.indexOf(selectedMetric));

  // Synchronize localSliderValue when selectedMetric changes externally
  useEffect(() => {
    const index = metrics.indexOf(selectedMetric);
    if (index !== localSliderValue) {
      setLocalSliderValue(index);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedMetric, metrics]);

  const metricIndexMap = useMemo(() => {
    return metrics.reduce((acc, metric, index) => {
      acc[metric] = index;
      return acc;
    }, {});
  }, [metrics]);

  const rgbToRgba = (rgb, alpha) => {
    const [r, g, b] = rgb.match(/\d+/g);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  };

  const getPredictionValue = (site) => {
    const prediction = site.predictions.find(
      (pred) => pred.date === selectedDate
    );
    if (prediction && Array.isArray(prediction.values)) {
      const metricIdx = metricIndexMap[selectedMetric];
      const value = prediction.values[metricIdx];
      return value !== undefined ? value : 'N/A';
    }
    return 'N/A';
  };

  const getColor = (probability) => {
    if (probability === 'N/A') return 'gray';
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
          key={`site-${site.site_id}`}
          position={[site.latitude, site.longitude]}
          icon={createCustomIcon(color)}
          interactive={!isSmallMap}
          ref={(ref) => {
            if (ref && getMarkerRef) {
              getMarkerRef(site.site_id, ref);
            }
          }}
        >
          {!isSmallMap && (
            <Popup>
              <strong>{site.name}</strong><br />
              Probability: {probability !== 'N/A' ? probability.toFixed(2) : 'N/A'}<br />
              <a 
                href={`/sites/${site.site_id}?date=${selectedDate}&metric=${selectedMetric}`}
                onClick={(e) => {
                  e.preventDefault();
                  navigate(`/sites/${site.site_id}?date=${selectedDate}&metric=${selectedMetric}`);
                }}
              >
                Details
              </a>
            </Popup>
          )}
        </Marker>
      );
    });
  }, [sites, selectedMetric, selectedDate, navigate, isSmallMap, getMarkerRef]);

  // Handle slider change (updates local state)
  const handleSliderChange = (event, newValue) => {
    setLocalSliderValue(newValue);
  };

  // Handle slider change committed (updates selected metric)
  const handleSliderChangeCommitted = (event, newValue) => {
    if (newValue >= 0 && newValue < metrics.length) {
      // Use transition for updating the selected metric
      startTransition(() => {
        setSelectedMetric(metrics[newValue]);
      });
    }
  };

  const sliderValue = localSliderValue;
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
      zoomControl={false}
      doubleClickZoom={!isSmallMap}
      boxZoom={!isSmallMap}
      keyboard={!isSmallMap}
      tap={!isSmallMap}
      touchZoom={!isSmallMap}
      attributionControl={!isSmallMap}
      maxBoundsViscosity={1.0}
      ref={mapRef}
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
              onChangeCommitted={handleSliderChangeCommitted}
              valueLabelDisplay="off"
              aria-labelledby="metric-slider"
            />
          </Box>
        </PreventLeafletControl>
      )}
      {markers}
      
      {/* Optional: Display a loading indicator when a transition is pending */}
      {isPending && !isSmallMap && (
        <Box
          sx={{
            position: 'absolute',
            top: '10px',
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: 'rgba(255, 255, 255, 0.8)',
            padding: '4px 8px',
            borderRadius: '4px',
            zIndex: 1001,
          }}
        >
          <Typography variant="body2">Updating Metric...</Typography>
        </Box>
      )}
    </MapContainer>
  );
});

export default MapView;
