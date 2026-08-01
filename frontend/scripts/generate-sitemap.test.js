import { describe, expect, it } from 'vitest';

import { buildSitemapXml } from './generate-sitemap.mjs';

describe('buildSitemapXml', () => {
  it('uses the canonical host and includes only crawlable public routes', () => {
    const xml = buildSitemapXml([
      { site_id: 1, name: 'Raná' },
      { id: 3, name: 'Kozákov' },
      { site_id: 1, name: 'Raná duplicate' },
    ]);

    expect(xml).toContain('<loc>https://www.parra-glideator.com/</loc>');
    expect(xml).toContain('<loc>https://www.parra-glideator.com/about</loc>');
    expect(xml).toContain('<loc>https://www.parra-glideator.com/details/1</loc>');
    expect(xml).toContain('<loc>https://www.parra-glideator.com/details/3</loc>');
    expect(xml).not.toContain('/trip-planner');
    expect(xml.match(/\/details\/1<\/loc>/g)).toHaveLength(1);
  });

  it('fails instead of publishing an incomplete sitemap without sites', () => {
    expect(() => buildSitemapXml([])).toThrow('without site records');
  });
});
