import { describe, expect, it } from 'vitest';

import {
  buildDetailsShareUrl,
  buildMapShareUrl,
  buildTripPlanShareUrl,
  formatShareDateRange,
  getChanceLabel,
  getFlightPhrase,
} from './shareUtils';

describe('shareUtils', () => {
  it('turns internal metric keys into pilot-facing language', () => {
    expect(getChanceLabel('XC0')).toBe('Chance of a flight');
    expect(getChanceLabel('XC20')).toBe('Chance of a 20+ point flight');
    expect(getFlightPhrase('XC80')).toBe('an 80+ point flight');
  });

  it('creates clean links for each details section', () => {
    expect(buildDetailsShareUrl({
      origin: 'https://example.test/',
      siteId: 1,
      tab: 'forecast',
      selectedDate: '2026-08-03',
      selectedMetric: 'XC20',
    })).toBe('https://example.test/details/1?date=2026-08-03&metric=XC20');

    expect(buildDetailsShareUrl({
      origin: 'https://example.test',
      siteId: 1,
      tab: 'season',
      selectedMetric: 'XC20',
    })).toBe('https://example.test/details/1?metric=XC20&tab=season');

    expect(buildDetailsShareUrl({
      origin: 'https://example.test',
      siteId: 1,
      tab: 'resources',
    })).toBe('https://example.test/details/1?tab=resources');
  });

  it('rounds map coordinates and strips unrelated state', () => {
    expect(buildMapShareUrl({
      origin: 'https://example.test',
      search: '?date=2026-08-03&metric=XC20&lat=50.12345&lng=14.98765&zoom=7.8&mapType=topographic&campaign=pilot',
      selectedDate: '2026-08-03',
      selectedMetric: 'XC20',
    })).toBe('https://example.test/?date=2026-08-03&metric=XC20&lat=50.12&lng=14.99&zoom=8&mapType=topographic');
  });

  it('shares a coarse trip origin or removes the location-dependent filters', () => {
    const search = '?startDate=2026-08-03&endDate=2026-08-05&distEnabled=true&distKm=200&locSrc=current&sortBy=distance&tags=ridge';

    expect(buildTripPlanShareUrl({
      origin: 'https://example.test',
      search,
      selectedMetric: 'XC20',
      includeDistance: true,
      approximateOrigin: { latitude: 50.0875, longitude: 14.4213 },
    })).toBe('https://example.test/trip-planner?startDate=2026-08-03&endDate=2026-08-05&sortBy=distance&tags=ridge&distEnabled=true&distKm=200&locSrc=current&metric=XC20&originLat=50.1&originLng=14.4');

    expect(buildTripPlanShareUrl({
      origin: 'https://example.test',
      search,
      selectedMetric: 'XC20',
      includeDistance: false,
    })).toBe('https://example.test/trip-planner?startDate=2026-08-03&endDate=2026-08-05&tags=ridge&metric=XC20');
  });

  it('formats compact ranges for share copy', () => {
    expect(formatShareDateRange('2030-08-03', '2030-08-05')).toBe('3–5 August 2030');
  });
});
