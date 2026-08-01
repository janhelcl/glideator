export const METRICS = [
  'XC0',
  'XC10',
  'XC20',
  'XC30',
  'XC40',
  'XC50',
  'XC60',
  'XC70',
  'XC80',
  'XC90',
  'XC100',
];

const PUBLIC_ORIGIN = process.env.REACT_APP_PUBLIC_ORIGIN || 'https://www.parra-glideator.com';

export const normalizeMetric = (metric) => (METRICS.includes(metric) ? metric : 'XC0');

export const getMetricThreshold = (metric) => {
  const normalized = normalizeMetric(metric);
  return normalized === 'XC0' ? 0 : Number.parseInt(normalized.replace('XC', ''), 10);
};

const indefiniteArticle = (threshold) => (threshold === 80 ? 'an' : 'a');

export const getFlightPhrase = (metric, { article = true } = {}) => {
  const threshold = getMetricThreshold(metric);
  if (threshold === 0) return article ? 'a flight' : 'flight';
  const noun = `${threshold}+ point flight`;
  return article ? `${indefiniteArticle(threshold)} ${noun}` : noun;
};

export const getPluralFlightPhrase = (metric) => {
  const threshold = getMetricThreshold(metric);
  return threshold === 0 ? 'flights' : `${threshold}+ point flights`;
};

export const getChanceLabel = (metric, { plural = false, capitalize = true } = {}) => {
  const prefix = plural ? 'Chances' : 'Chance';
  const label = `${prefix} of ${getFlightPhrase(metric)}`;
  return capitalize ? label : `${label.charAt(0).toLowerCase()}${label.slice(1)}`;
};

export const formatShareDate = (value, { includeYear = false } = {}) => {
  if (!value) return 'the selected date';
  const parsed = value instanceof Date ? value : new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return String(value);

  return new Intl.DateTimeFormat('en', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    ...(includeYear ? { year: 'numeric' } : {}),
    timeZone: 'UTC',
  }).format(parsed);
};

const formatRangePart = (date, options) => new Intl.DateTimeFormat('en', {
  day: 'numeric',
  month: options.month,
  ...(options.year ? { year: 'numeric' } : {}),
  timeZone: 'UTC',
}).format(date);

export const formatShareDateRange = (startValue, endValue) => {
  if (!startValue || !endValue) return 'the selected dates';
  const start = new Date(`${startValue}T00:00:00Z`);
  const end = new Date(`${endValue}T00:00:00Z`);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    return `${startValue}–${endValue}`;
  }

  if (start.getTime() === end.getTime()) return formatShareDate(startValue);

  const sameMonth = start.getUTCFullYear() === end.getUTCFullYear()
    && start.getUTCMonth() === end.getUTCMonth();
  const sameYear = start.getUTCFullYear() === end.getUTCFullYear();

  if (sameMonth) {
    const monthYear = new Intl.DateTimeFormat('en', {
      month: 'long',
      ...(start.getUTCFullYear() !== new Date().getUTCFullYear() ? { year: 'numeric' } : {}),
      timeZone: 'UTC',
    }).format(end);
    return `${start.getUTCDate()}–${end.getUTCDate()} ${monthYear}`;
  }

  return `${formatRangePart(start, { month: 'long', year: !sameYear })}–${formatRangePart(end, {
    month: 'long',
    year: !sameYear || end.getUTCFullYear() !== new Date().getUTCFullYear(),
  })}`;
};

const normalizeOrigin = (origin) => String(origin || PUBLIC_ORIGIN).replace(/\/$/, '');

const validCoordinate = (value, min, max) => Number.isFinite(value) && value >= min && value <= max;

export const buildMapShareUrl = ({ origin, search, selectedDate, selectedMetric }) => {
  const source = search instanceof URLSearchParams ? search : new URLSearchParams(search || '');
  const params = new URLSearchParams();

  if (selectedDate) params.set('date', selectedDate);
  params.set('metric', normalizeMetric(selectedMetric));

  const latitude = Number(source.get('lat'));
  const longitude = Number(source.get('lng'));
  if (validCoordinate(latitude, -90, 90) && validCoordinate(longitude, -180, 180)) {
    params.set('lat', latitude.toFixed(2));
    params.set('lng', longitude.toFixed(2));
  }

  const zoom = Number(source.get('zoom'));
  if (Number.isFinite(zoom)) params.set('zoom', String(Math.round(zoom)));

  const mapType = source.get('mapType');
  if (mapType) params.set('mapType', mapType);

  return `${normalizeOrigin(origin)}/?${params.toString()}`;
};

export const buildDetailsShareUrl = ({ origin, siteId, tab = 'forecast', selectedDate, selectedMetric }) => {
  const params = new URLSearchParams();
  const normalizedTab = ['forecast', 'season', 'map', 'resources'].includes(tab) ? tab : 'forecast';

  if (normalizedTab === 'forecast') {
    if (selectedDate) params.set('date', selectedDate);
    params.set('metric', normalizeMetric(selectedMetric));
  } else if (normalizedTab === 'season') {
    params.set('metric', normalizeMetric(selectedMetric));
    params.set('tab', 'season');
  } else {
    params.set('tab', normalizedTab);
  }

  const query = params.toString();
  return `${normalizeOrigin(origin)}/details/${encodeURIComponent(siteId)}${query ? `?${query}` : ''}`;
};

const TRIP_PARAMS = [
  'startDate',
  'endDate',
  'fqEnabled',
  'altEnabled',
  'altMin',
  'altMax',
  'view',
  'sortBy',
  'tags',
  'distEnabled',
  'distKm',
  'locSrc',
];

export const buildTripPlanShareUrl = ({
  origin,
  search,
  selectedMetric,
  approximateOrigin = null,
  includeDistance = true,
}) => {
  const source = search instanceof URLSearchParams ? search : new URLSearchParams(search || '');
  const params = new URLSearchParams();

  TRIP_PARAMS.forEach((key) => {
    const value = source.get(key);
    if (value != null && value !== '') params.set(key, value);
  });
  params.set('metric', normalizeMetric(selectedMetric));

  if (!includeDistance) {
    ['distEnabled', 'distKm', 'locSrc', 'originLat', 'originLng'].forEach((key) => params.delete(key));
    if (params.get('sortBy') === 'distance') params.delete('sortBy');
  } else if (approximateOrigin) {
    params.set('distEnabled', 'true');
    params.set('locSrc', 'current');
    params.set('originLat', Number(approximateOrigin.latitude).toFixed(2));
    params.set('originLng', Number(approximateOrigin.longitude).toFixed(2));
  }

  return `${normalizeOrigin(origin)}/trip-planner?${params.toString()}`;
};

export const buildAboutShareUrl = ({ origin, hash = '' }) => (
  `${normalizeOrigin(origin)}/about${hash && hash.startsWith('#') ? hash : ''}`
);

export const getForecastProbability = ({ predictions, selectedDate, selectedMetric }) => {
  const index = METRICS.indexOf(normalizeMetric(selectedMetric));
  if (!selectedDate || !Array.isArray(predictions)) return null;
  const prediction = predictions.find((item) => item?.date === selectedDate);
  const value = prediction?.values?.[index];
  return Number.isFinite(value) ? value : null;
};
