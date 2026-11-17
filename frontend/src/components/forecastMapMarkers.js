import L from 'leaflet';
import { getColor, getColorWithAlpha } from '../utils/colorUtils';
import './forecastMapMarkers.css';

export function createForecastMarkerIcon(probability, lightweight = false) {
  const marker = document.createElement('div');
  const color = getColor(probability);
  if (lightweight) {
    marker.className = 'simple-marker';
    marker.style.backgroundColor = color;
    return L.divIcon({ className: '', html: marker, iconSize: [4, 4], iconAnchor: [2, 2] });
  }

  marker.className = 'glowing-marker';
  marker.style.setProperty('--marker-color', color);
  marker.style.setProperty('--marker-glow-color', getColorWithAlpha(probability, 0.7));
  marker.style.setProperty('--marker-glow-hover-color', getColorWithAlpha(probability, 1));
  for (const name of ['glow', 'point']) {
    const part = document.createElement('div');
    part.className = name;
    marker.append(part);
  }
  return L.divIcon({
    className: '', html: marker, iconSize: [12, 12], iconAnchor: [6, 6], popupAnchor: [0, -6],
  });
}
