import apiClient from './api';

const ANONYMOUS_ID_KEY = 'glideator.analytics.anonymous_id';
const SESSION_ID_KEY = 'glideator.analytics.session_id';
const MAX_STRING_LENGTH = 250;
const MAX_ARRAY_LENGTH = 20;
const MAX_DEPTH = 3;
const BLOCKED_PROPERTY_KEY = /^(email|user_?agent|ip(_address)?|lat(itude)?|lon(gitude)?|lng|coordinates|coords)$/i;

let inMemoryAnonymousId = null;
let inMemorySessionId = null;

const createId = (prefix) => {
  const randomValue = globalThis.crypto?.randomUUID?.()
    || `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
  return `${prefix}-${randomValue}`;
};

const getStoredId = (storage, key, prefix) => {
  try {
    const existing = storage?.getItem(key);
    if (existing) return existing;

    const created = createId(prefix);
    storage?.setItem(key, created);
    return created;
  } catch {
    return createId(prefix);
  }
};

const getAnonymousId = () => {
  if (!inMemoryAnonymousId) {
    inMemoryAnonymousId = getStoredId(globalThis.localStorage, ANONYMOUS_ID_KEY, 'anon');
  }
  return inMemoryAnonymousId;
};

const getSessionId = () => {
  if (!inMemorySessionId) {
    inMemorySessionId = getStoredId(globalThis.sessionStorage, SESSION_ID_KEY, 'session');
  }
  return inMemorySessionId;
};

const sanitizeValue = (value, depth = 0) => {
  if (depth >= MAX_DEPTH || value == null) return value;

  if (typeof value === 'string') return value.slice(0, MAX_STRING_LENGTH);
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value === 'boolean') return value;

  if (Array.isArray(value)) {
    return value
      .slice(0, MAX_ARRAY_LENGTH)
      .map((item) => sanitizeValue(item, depth + 1));
  }

  if (typeof value === 'object') {
    return Object.entries(value).reduce((sanitized, [key, item]) => {
      if (!BLOCKED_PROPERTY_KEY.test(key) && item !== undefined) {
        sanitized[key] = sanitizeValue(item, depth + 1);
      }
      return sanitized;
    }, {});
  }

  return String(value).slice(0, MAX_STRING_LENGTH);
};

export const analyticsEnabled = () => {
  if (process.env.REACT_APP_ANALYTICS_ENABLED === 'false') return false;
  if (globalThis.navigator?.globalPrivacyControl === true) return false;

  const doNotTrack = globalThis.navigator?.doNotTrack || globalThis.doNotTrack;
  return doNotTrack !== '1' && doNotTrack !== 'yes';
};

export const trackEvent = (eventName, properties = {}) => {
  if (!analyticsEnabled()) return Promise.resolve(null);

  const payload = {
    event_name: eventName,
    anonymous_id: getAnonymousId(),
    session_id: getSessionId(),
    path: globalThis.location?.pathname || null,
    properties: sanitizeValue(properties),
  };

  return apiClient.post('/analytics/events', payload, { timeout: 3000 }).catch(() => null);
};

export const resetAnalyticsIdsForTests = () => {
  inMemoryAnonymousId = null;
  inMemorySessionId = null;
};
