import React, { useEffect, useRef } from 'react';
import { DomEvent } from 'leaflet';
import { useMap } from 'react-leaflet';

const PreventLeafletControl = ({ children }) => {
  const controlRef = useRef();
  const map = useMap();

  useEffect(() => {
    const handleInteractionStart = () => {
      // Disable map interactions
      map.doubleClickZoom.disable();
      map.dragging.disable();
      map.scrollWheelZoom.disable();
      map.boxZoom.disable();
      map.keyboard.disable();
      if (map.tap) map.tap.disable();
    };

    const handleInteractionEnd = () => {
      // Enable map interactions
      map.doubleClickZoom.enable();
      map.dragging.enable();
      map.scrollWheelZoom.enable();
      map.boxZoom.enable();
      map.keyboard.enable();
      if (map.tap) map.tap.enable();
    };

    const current = controlRef.current;
    if (current) {
      // Mouse events
      DomEvent.on(current, 'mouseover', handleInteractionStart);
      DomEvent.on(current, 'mouseout', handleInteractionEnd);
      
      // Touch events
      DomEvent.on(current, 'touchstart', handleInteractionStart);
      DomEvent.on(current, 'touchend', handleInteractionEnd);
      DomEvent.on(current, 'touchcancel', handleInteractionEnd);
    }

    // Cleanup event listeners on unmount
    return () => {
      if (current) {
        // Mouse events
        DomEvent.off(current, 'mouseover', handleInteractionStart);
        DomEvent.off(current, 'mouseout', handleInteractionEnd);
        
        // Touch events
        DomEvent.off(current, 'touchstart', handleInteractionStart);
        DomEvent.off(current, 'touchend', handleInteractionEnd);
        DomEvent.off(current, 'touchcancel', handleInteractionEnd);
      }
    };
  }, [map]);

  return <div ref={controlRef}>{children}</div>;
};

export default PreventLeafletControl;
