import React, { useEffect, useRef } from 'react';
import { DomEvent } from 'leaflet';
import { useMap } from 'react-leaflet';

const PreventLeafletControl = ({ children }) => {
  const controlRef = useRef();
  const map = useMap();

  useEffect(() => {
    const handleMouseOver = () => {
      // Disable map interactions
      map.doubleClickZoom.disable();
      map.dragging.disable();
      map.scrollWheelZoom.disable();
      map.boxZoom.disable();
      map.keyboard.disable();
      if (map.tap) map.tap.disable();
    };

    const handleMouseOut = () => {
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
      DomEvent.on(current, 'mouseover', handleMouseOver);
      DomEvent.on(current, 'mouseout', handleMouseOut);
    }

    // Cleanup event listeners on unmount
    return () => {
      if (current) {
        DomEvent.off(current, 'mouseover', handleMouseOver);
        DomEvent.off(current, 'mouseout', handleMouseOut);
      }
    };
  }, [map]);

  return <div ref={controlRef}>{children}</div>;
};

export default PreventLeafletControl;
