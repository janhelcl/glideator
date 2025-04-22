import React, { useMemo, useEffect, useState, useTransition, useCallback, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { useNavigate, useSearchParams } from 'react-router-dom';
import L from 'leaflet';
import './MapView.css';
import { Box, IconButton } from '@mui/material';
import PreventLeafletControl from './PreventLeafletControl';
import MetricControl from './MetricControl';
import MyLocationIcon from '@mui/icons-material/MyLocation';
import LayersIcon from '@mui/icons-material/Layers';
import debounce from 'lodash/debounce';
import LoadingSpinner from './LoadingSpinner';

// Fix default icon issues with Webpack
delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

// Component to handle map events and update shared state
const MapEventHandler = ({ setMapState, updateUrlParams }) => {
  const map = useMap();

  useEffect(() => {
    const handleMoveEnd = () => {
      const currentBounds = map.getBounds();
      const center = map.getCenter();
      const zoom = map.getZoom();
      
      setMapState({
        center: [center.lat, center.lng],
        zoom: zoom,
        bounds: currentBounds
      });

      // Update URL parameters
      updateUrlParams([center.lat, center.lng], zoom);
    };

    map.on('moveend', handleMoveEnd);
    handleMoveEnd();

    return () => {
      map.off('moveend', handleMoveEnd);
    };
  }, [map, setMapState, updateUrlParams]);

  return null;
};

// Component to synchronize small map views with main map
const SynchronizeMapView = ({ bounds }) => {
  const map = useMap();
  const lastBoundsRef = useRef(null);

  useEffect(() => {
    // Make sure map is defined before using it
    if (!map) return;
    
    if (bounds) {
      // Only update bounds if there's a significant change
      if (!lastBoundsRef.current || 
          !lastBoundsRef.current.getCenter() || 
          Math.abs(bounds.getCenter().lat - lastBoundsRef.current.getCenter().lat) > 0.01 ||
          Math.abs(bounds.getCenter().lng - lastBoundsRef.current.getCenter().lng) > 0.01 ||
          Math.abs(bounds.getNorth() - lastBoundsRef.current.getNorth()) > 0.02) {
        
        // Clone the bounds to ensure we have a new reference
        lastBoundsRef.current = L.latLngBounds(
          L.latLng(bounds.getSouth(), bounds.getWest()),
          L.latLng(bounds.getNorth(), bounds.getEast())
        );
        
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
    }
  }, [bounds, map]);

  return null;
};

// New component to listen for base layer changes and update the URL parameter "mapType"
const MapBaseLayerHandler = ({ searchParams, setSearchParams }) => {
  const map = useMap();
  useEffect(() => {
    const handleBaseLayerChange = (e) => {
      const newMapType = e.name.toLowerCase();
      const currentParams = Object.fromEntries(searchParams.entries());
      setSearchParams(
        {
          ...currentParams,
          mapType: newMapType
        },
        { replace: true }
      );
    };
    map.on('baselayerchange', handleBaseLayerChange);
    return () => {
      map.off('baselayerchange', handleBaseLayerChange);
    };
  }, [map, searchParams, setSearchParams]);
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
  lightweight = false,
  metrics,
  getMarkerRef,
  mapRef,
}) => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  // Initialize useTransition
  const [isPending, startTransition] = useTransition();

  // Get location and zoom from URL or use defaults
  const initialCenter = useMemo(() => {
    const lat = parseFloat(searchParams.get('lat'));
    const lng = parseFloat(searchParams.get('lng'));
    return (lat && lng) ? [lat, lng] : center;
  }, [center, searchParams]);

  const initialZoom = useMemo(() => {
    const z = parseInt(searchParams.get('zoom'));
    return !isNaN(z) ? z : zoom;
  }, [zoom, searchParams]);

  // New: Get mapType from URL parameter ("basic" or "topographic")
  const initialMapType = useMemo(() => {
    const m = searchParams.get('mapType');
    return m ? m.toLowerCase() : 'basic';
  }, [searchParams]);

  // Debounced function to update URL parameters
  const updateUrlParams = useMemo(
    () =>
      debounce((center, zoom) => {
        const currentParams = Object.fromEntries(searchParams.entries());
        setSearchParams(
          {
            ...currentParams,
            lat: center[0].toFixed(4),
            lng: center[1].toFixed(4),
            zoom: zoom
          },
          { replace: true }
        );
      }, 1000),
    [searchParams, setSearchParams]
  );

  // Cleanup debounce on unmount
  useEffect(() => {
    return () => {
      updateUrlParams.cancel();
    };
  }, [updateUrlParams]);

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

  const getPredictionValue = useCallback((site) => {
    const prediction = site.predictions.find(
      (pred) => pred.date === selectedDate
    );
    if (prediction && Array.isArray(prediction.values)) {
      const metricIdx = metricIndexMap[selectedMetric];
      const value = prediction.values[metricIdx];
      return value !== undefined ? value : 'N/A';
    }
    return 'N/A';
  }, [selectedMetric, selectedDate, metricIndexMap]);

  const getColor = (probability) => {
    if (probability === 'N/A') return 'gray';
    const p = Math.max(0, Math.min(1, probability));
    const r = Math.round(255 * (1 - p));
    const g = Math.round(255 * p);
    return `rgb(${r}, ${g}, 0)`;
  };

  const createCustomIcon = useCallback((color, isLightweight = false) => {
    if (isLightweight) {
      // Create a much simpler icon for lightweight maps - no glow, no hover effects
      return L.divIcon({
        className: '',
        html: `
          <div class="simple-marker" style="background-color: ${color}; width: 4px; height: 4px; border-radius: 50%; border: 0.5px solid rgba(0,0,0,0.5);"></div>
        `,
        iconSize: [4, 4],
        iconAnchor: [2, 2],
      });
    }
    
    // Regular detailed icon with glow for standard maps
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
  }, []);

  const markers = useMemo(() => {
    return sites.map((site) => {
      const probability = getPredictionValue(site);
      const color = probability !== 'N/A' ? getColor(probability) : 'gray';
      const percentValue = probability !== 'N/A' ? `${Math.round(probability * 100)}%` : 'N/A';

      return (
        <Marker
          key={`site-${site.site_id}`}
          position={[site.latitude, site.longitude]}
          icon={createCustomIcon(color, isSmallMap && lightweight)}
          interactive={!isSmallMap}
          ref={(ref) => {
            if (ref && getMarkerRef && typeof getMarkerRef === 'function') {
              getMarkerRef(site.site_id, ref);
            }
          }}
        >
          {!isSmallMap && (
            <Popup closeButton={false} className="custom-popup">
              <div className="popup-content">
                <div className="popup-header">
                  <h3>{site.name}</h3>
                </div>
                <div className="popup-metric-bar">
                  <span 
                    className="popup-metric-value" 
                    style={{ 
                      backgroundColor: color,
                      opacity: probability !== 'N/A' ? 1 : 0.5
                    }}
                  >
                    {percentValue}
                  </span>
                </div>
                <div className="popup-footer">
                  <button 
                    className="popup-details-button"
                    onClick={(e) => {
                      // Only handle left clicks here, middle clicks are handled by onMouseUp
                      if (e.button === 0 || e.button === undefined) {
                        navigate(`/details/${site.site_id}?date=${selectedDate}&metric=${selectedMetric}`);
                      }
                    }}
                    onMouseUp={(e) => {
                      // Handle middle mouse button (mousewheel) click
                      if (e.button === 1) {
                        // Prevent default to avoid potential scrolling behavior
                        e.preventDefault();
                        // Open in new tab
                        window.open(`/details/${site.site_id}?date=${selectedDate}&metric=${selectedMetric}`, '_blank');
                      }
                    }}
                  >
                    View Details
                  </button>
                </div>
              </div>
            </Popup>
          )}
        </Marker>
      );
    });
  }, [sites, selectedMetric, selectedDate, navigate, isSmallMap, lightweight, getMarkerRef, createCustomIcon, getPredictionValue]);

  // Handle slider change (updates local state)
  const handleSliderChange = (event, newValue) => {
    setLocalSliderValue(newValue);
  };

  // Create debounced version of slider change committed
  const debouncedHandleSliderChangeCommitted = useMemo(
    () => debounce((event, newValue) => {
      if (newValue >= 0 && newValue < metrics.length) {
        // Use transition for updating the selected metric
        startTransition(() => {
          setSelectedMetric(metrics[newValue]);
        });
      }
    }, 150), // Wait 150ms after sliding stops before updating
    [metrics, setSelectedMetric]
  );

  // Cleanup debounce on unmount
  useEffect(() => {
    return () => {
      debouncedHandleSliderChangeCommitted.cancel();
    };
  }, [debouncedHandleSliderChangeCommitted]);

  // Handle slider change committed (updates selected metric)
  const handleSliderChangeCommitted = (event, newValue) => {
    debouncedHandleSliderChangeCommitted(event, newValue);
  };

  const sliderValue = localSliderValue;

  // Handle location click
  const handleLocationClick = () => {
    if ("geolocation" in navigator && mapRef && mapRef.current) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          const currentZoom = mapRef.current?.getZoom() || zoom;
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

  // Add state to track current map type
  const [mapType, setMapType] = useState(initialMapType);

  // Function to toggle between map types
  const toggleMapType = () => {
    const newMapType = mapType === 'basic' ? 'topographic' : 'basic';
    setMapType(newMapType);
    
    // Update URL parameter
    const currentParams = Object.fromEntries(searchParams.entries());
    setSearchParams(
      {
        ...currentParams,
        mapType: newMapType
      },
      { replace: true }
    );
    
    // If we have a map reference, manually update the tile layer
    if (mapRef.current) {
      // This is handled by the effect below
    }
  };

  // Effect to update tile layer when mapType changes
  useEffect(() => {
    if (!isSmallMap && mapRef && mapRef.current) {
      const map = mapRef.current;
      let newLayerUrl = '';
      let newLayerAttribution = '';

      // Determine the new layer URL and attribution
      if (mapType === 'basic') {
        newLayerUrl = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
        newLayerAttribution = 'Map data: &copy; <a href="https://www.openstreetmap.org">OpenStreetMap</a> contributors';
      } else { // topographic
        newLayerUrl = "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png";
        newLayerAttribution = 'Map data: &copy; <a href="https://www.openstreetmap.org">OpenTopoMap</a> contributors, SRTM | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (CC-BY-SA)';
      }

      // Find and remove existing TileLayer
      let existingTileLayer = null;
      map.eachLayer(layer => {
        if (layer instanceof L.TileLayer) {
          existingTileLayer = layer;
        }
      });

      if (existingTileLayer) {
        map.removeLayer(existingTileLayer);
      }

      // Create and add the new TileLayer
      const newTileLayer = L.tileLayer(newLayerUrl, {
        attribution: newLayerAttribution
      });
      newTileLayer.addTo(map);

      console.log('Explicitly changed map type to:', mapType);
    }
  }, [mapType, isSmallMap, mapRef]); // Depend on mapType

  // Add memory management for map instances, especially for lightweight maps
  useEffect(() => {
    // Capture the current map instance only if mapRef exists
    const mapInstance = mapRef ? mapRef.current : null;

    // Return cleanup function to run on unmount
    return () => {
      // Use the captured map instance in the cleanup

      // If this is a small lightweight map, do extra cleanup
      if (isSmallMap && lightweight && mapInstance) { // Use the captured mapInstance
        console.log('Performing cleanup for lightweight map');

        try {
          // Force garbage collection of tiles
          mapInstance.eachLayer(layer => { // Use the captured mapInstance
            if (layer instanceof L.TileLayer) {
              // Reduce tile buffer to minimum
              layer.options.keepBuffer = 0;

              // Remove all tiles from cache
              if (layer._removeAllTiles) {
                layer._removeAllTiles();
              }

              // Cancel any pending tile requests
              if (layer._cancelTilesLoading) {
                layer._cancelTilesLoading();
              }
            }
          });

          // Remove event listeners
          mapInstance.off(); // Use the captured mapInstance

          // Clear any bounds
          if (mapInstance._boundsCenterZoom) { // Use the captured mapInstance
            mapInstance._boundsCenterZoom = null;
          }

          // Additional cleanup for markers
          if (mapInstance._layers) { // Use the captured mapInstance
            Object.keys(mapInstance._layers).forEach(key => {
              const layer = mapInstance._layers[key];
              if (layer instanceof L.Marker) {
                mapInstance.removeLayer(layer); // Use the captured mapInstance
              }
            });
          }
        } catch (e) {
          // Safely handle any errors during cleanup
          console.warn('Error during map cleanup:', e);
        }
      }
    };
  }, [isSmallMap, lightweight, mapRef]); // Keep mapRef in the dependencies

  return (
    <MapContainer
      center={initialCenter}
      zoom={initialZoom}
      style={{ 
        height: isSmallMap ? '100px' : '100%', 
        width: isSmallMap ? '150px' : '100%',
        position: 'relative',
        minWidth: isSmallMap ? '150px' : 'auto',
        margin: 0,
        padding: 0
      }}
      dragging={!isSmallMap && !lightweight}
      scrollWheelZoom={!isSmallMap && !lightweight}
      zoomControl={false}
      doubleClickZoom={!isSmallMap && !lightweight}
      boxZoom={!isSmallMap && !lightweight}
      keyboard={!isSmallMap && !lightweight}
      tap={!isSmallMap && !lightweight}
      touchZoom={!isSmallMap && !lightweight}
      attributionControl={!isSmallMap && !lightweight}
      maxBoundsViscosity={1.0}
      preferCanvas={isSmallMap || lightweight}
      ref={mapRef}
    >
      {/* Pass isSmallMap to SynchronizeMapView */}
      {isSmallMap && <SynchronizeMapView bounds={bounds} />}

      {/* Handle map state updates for the main map */}
      {!isSmallMap && !lightweight && setMapState && (
        <MapEventHandler 
          setMapState={setMapState} 
          updateUrlParams={updateUrlParams}
        />
      )}

      {/* New: Listen to base layer changes and update "mapType" URL parameter */}
      {!isSmallMap && !lightweight && (
        <MapBaseLayerHandler searchParams={searchParams} setSearchParams={setSearchParams} />
      )}

      {/* Replace LayersControl with conditional TileLayers based on mapType */}
      {(isSmallMap || lightweight) ? (
        /* Render a simplified TileLayer for small/lightweight maps */
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}.png"
          attribution="" // No attribution for small maps
          tileSize={256}
          zoomOffset={0}
          updateWhenIdle={true}
          updateWhenZooming={false}
          updateInterval={500}
          keepBuffer={1}
        />
      ) : (
        /* Initial render based on initialMapType */
        initialMapType === 'basic' ? (
          <TileLayer
            key="basic-tiles-initial" // Key for initial render consistency
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='Map data: &copy; <a href="https://www.openstreetmap.org">OpenStreetMap</a> contributors'
          />
        ) : (
          <TileLayer
            key="topo-tiles-initial" // Key for initial render consistency
            url="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png"
            attribution='Map data: &copy; <a href="https://www.openstreetmap.org">OpenTopoMap</a> contributors, SRTM | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (CC-BY-SA)'
          />
        )
      )}

      {/* Conditionally render the Metric Slider only on the main map */}
      {!isSmallMap && !lightweight && (
        <PreventLeafletControl>
          <MetricControl
            metrics={metrics}
            sliderValue={sliderValue}
            onSliderChange={handleSliderChange}
            onSliderChangeCommitted={handleSliderChangeCommitted}
          />
        </PreventLeafletControl>
      )}
      {markers}
      
      {/* Optional: Display a loading indicator when a transition is pending */}
      {isPending && !isSmallMap && !lightweight && (
        <LoadingSpinner />
      )}

      {/* Update controls container to include both location and map type buttons */}
      {!isSmallMap && !lightweight && (
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
      )}

      {/* Add custom map type control */}
      {!isSmallMap && !lightweight && (
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
      )}
    </MapContainer>
  );
});

export default MapView;
