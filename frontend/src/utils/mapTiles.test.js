import { describe, expect, it } from 'vitest';
import { getLightweightTileConfig } from './mapTiles';

describe('getLightweightTileConfig', () => {
  it('falls back to OpenStreetMap when no CARTO key is configured', () => {
    const config = getLightweightTileConfig('   ');

    expect(config.provider).toBe('openstreetmap');
    expect(config.url).toBe('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png');
    expect(config.url).not.toContain('cartocdn.com');
  });

  it('uses the keyed CARTO raster endpoint when a key is configured', () => {
    const config = getLightweightTileConfig('carto key/with symbols');

    expect(config.provider).toBe('carto');
    expect(config.url).toBe(
      'https://{s}.basemaps.cartocdn.com/rastertiles/light_nolabels/{z}/{x}/{y}.png?key=carto%20key%2Fwith%20symbols',
    );
    expect(config.attribution).toContain('OpenStreetMap');
    expect(config.attribution).toContain('CARTO');
  });
});
