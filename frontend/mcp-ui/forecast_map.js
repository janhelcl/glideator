import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { createForecastMarkerIcon } from '../src/components/forecastMapMarkers';
import { OPENSTREETMAP_ATTRIBUTION, OPENSTREETMAP_TILE_URL } from '../src/utils/mapTiles';
import { connectChartWidget } from './chartHost';

const origin = 'https://www.parra-glideator.com';
const main = document.querySelector('main');
const results = document.querySelector('#results');
const date = document.querySelector('#date');
const metric = document.querySelector('#metric');
const mapContainer = document.querySelector('#map');
const expand = document.querySelector('#expand');
const webMap = document.querySelector('#web-map');
const status = document.querySelector('#status');
const tileStatus = document.querySelector('#tile-status');
const dateFormat = new Intl.DateTimeFormat(undefined, {
  weekday: 'short', month: 'short', day: 'numeric', timeZone: 'UTC',
});
const metrics = Array.from({ length: 11 }, (_, index) => `XC${index * 10}`);
const dayLabel = (day) => dateFormat.format(new Date(day));
const forecastLabel = (threshold) => threshold === 'XC0' ? 'any flight' : `${threshold.slice(2)}+ XC points`;
let map;
let markers = [];
let displayMode = 'inline';
let availableModes = [];

metric.replaceChildren(...metrics.map((threshold) =>
  new Option(threshold === 'XC0' ? 'Any flight' : forecastLabel(threshold), threshold)));

function getUrl(path, extras = {}) {
  const url = new URL(path, origin);
  url.searchParams.set('metric', metric.value);
  if (date.value) url.searchParams.set('date', date.value);
  for (const [key, value] of Object.entries(extras)) url.searchParams.set(key, value);
  return url.href;
}

function updateWebLink() {
  const { lat, lng } = map.getCenter().wrap();
  webMap.href = getUrl('/', { lat: lat.toFixed(4), lng: lng.toFixed(4), zoom: map.getZoom() });
}

function sitePopup(site, description) {
  const content = document.createElement('div');
  content.className = 'site-popup';
  const name = document.createElement('strong');
  name.textContent = site.name;
  const probability = document.createElement('p');
  probability.textContent = description;
  const link = document.createElement('a');
  link.href = getUrl(`/details/${site.site_id}`);
  link.target = '_blank';
  link.rel = 'noopener';
  link.textContent = 'View site forecast';
  content.append(name, probability, link);
  return content;
}

function updateDisplay() {
  const index = metrics.indexOf(metric.value);
  let withForecast = 0;
  for (const { site, marker } of markers) {
    const forecast = site.predictions.find((day) => day.date === date.value);
    const probability = forecast?.values[index];
    const available = Number.isFinite(probability);
    if (available) withForecast++;
    const description = available
      ? `${Math.round(probability * 100)}% chance of ${forecastLabel(metric.value)}`
      : 'No forecast available';
    marker.setIcon(createForecastMarkerIcon(available ? probability : null));
    marker.getElement().setAttribute('aria-label', `${site.name}: ${description}`);
    marker.getElement().title = site.name;
    marker.setPopupContent(sitePopup(site, description));
  }
  status.textContent = withForecast
    ? `${dayLabel(date.value)} · ${withForecast} of ${markers.length} sites with forecasts`
    : date.value ? `No forecasts available for ${dayLabel(date.value)}.` : 'No forecasts available.';
  updateWebLink();
}

function renderResult(result) {
  map?.remove();
  map = undefined;
  markers = [];
  const forecast = result.isError ? null : result.structuredContent;
  const sites = result._meta?.sites;
  results.hidden = !forecast || !sites?.length;
  if (results.hidden) {
    status.textContent = forecast?.site_count === 0 ? 'No sites to display.' : 'The forecast map could not be loaded.';
    return;
  }

  tileStatus.hidden = true;
  const dates = forecast.available_dates;
  date.replaceChildren(...dates.map((day) => new Option(dayLabel(day), day)));
  if (forecast.date && !dates.includes(forecast.date)) {
    date.prepend(new Option(`${dayLabel(forecast.date)} (no forecast)`, forecast.date));
  }
  date.value = forecast.date ?? '';
  date.disabled = dates.length === 0;
  metric.value = forecast.metric;

  map = L.map(mapContainer, {
    scrollWheelZoom: false,
    minZoom: 3,
    maxZoom: 19,
  });
  map.attributionControl.setPrefix(false);
  const tiles = L.tileLayer(OPENSTREETMAP_TILE_URL, {
    attribution: OPENSTREETMAP_ATTRIBUTION,
    referrerPolicy: 'strict-origin-when-cross-origin',
    updateWhenIdle: true,
    keepBuffer: 1,
    noWrap: true,
  });
  let tilesLoaded = false;
  tiles.on('tileerror', () => { if (!tilesLoaded) tileStatus.hidden = false; });
  tiles.on('tileload', () => {
    tilesLoaded = true;
    tileStatus.hidden = true;
  });
  const focus = sites.find((site) => site.site_id === forecast.focus_site_id);
  if (focus) map.setView([focus.latitude, focus.longitude], 8);
  else map.fitBounds(sites.map((site) => [site.latitude, site.longitude]), { padding: [16, 16], maxZoom: 9 });
  tiles.addTo(map);
  markers = sites.map((site) => ({
    site,
    marker: L.marker([site.latitude, site.longitude], {
      title: site.name,
      icon: createForecastMarkerIcon(null),
    }).addTo(map).bindPopup(''),
  }));
  map.on('moveend', updateWebLink);
  updateDisplay();
}

date.addEventListener('change', updateDisplay);
metric.addEventListener('change', updateDisplay);
const mapObserver = new ResizeObserver(() => map?.invalidateSize({ pan: false }));
mapObserver.observe(mapContainer);

const host = connectChartWidget({
  appInfo: { name: 'Parra-Glideator forecast map', version: '1.0.0' },
  onResult: renderResult,
  onTeardown: () => {
    mapObserver.disconnect();
    map?.remove();
  },
  onHostContext: (context) => {
    displayMode = context.displayMode ?? displayMode;
    availableModes = context.availableDisplayModes ?? availableModes;
    main.dataset.displayMode = displayMode;
    expand.hidden = !availableModes.includes('fullscreen');
    expand.textContent = displayMode === 'fullscreen' ? 'Exit fullscreen' : 'Expand map';
  },
});

expand.addEventListener('click', () => host.requestDisplayMode(displayMode === 'fullscreen' ? 'inline' : 'fullscreen'));
main.addEventListener('click', (event) => {
  // Leaflet stops clicks from bubbling out of popups and controls.
  const link = event.target.closest('a[href^="https://"]');
  if (!link) return;
  event.preventDefault();
  host.openLink(link.href);
}, { capture: true });
