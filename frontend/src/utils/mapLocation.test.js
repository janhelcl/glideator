import { parseMapCenter } from './mapLocation';

describe('parseMapCenter', () => {
  it('does not turn missing coordinates into zeroes', () => {
    expect(parseMapCenter('')).toBeNull();
    expect(parseMapCenter('?date=2026-08-01&metric=XC0')).toBeNull();
    expect(parseMapCenter('?lat=50.0755')).toBeNull();
    expect(parseMapCenter('?lng=14.4378')).toBeNull();
  });

  it('returns valid URL coordinates, including zero', () => {
    expect(parseMapCenter('?lat=50.0755&lng=14.4378')).toEqual([50.0755, 14.4378]);
    expect(parseMapCenter('?lat=0&lng=0')).toEqual([0, 0]);
  });

  it('rejects invalid and out-of-range coordinates', () => {
    expect(parseMapCenter('?lat=nope&lng=14')).toBeNull();
    expect(parseMapCenter('?lat=91&lng=14')).toBeNull();
    expect(parseMapCenter('?lat=50&lng=181')).toBeNull();
  });
});
