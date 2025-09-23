// Minimal sitemap generator for CRA
// Usage:
//   SITEMAP_BASE_URL=https://parra-glideator.com \
//   SITEMAP_API_URL=https://parra-glideator.com/api \
//   node scripts/generate-sitemap.mjs

import { writeFile } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const BASE_URL = (process.env.SITEMAP_BASE_URL || 'http://localhost:3000').replace(/\/$/, '');
const API_URL = (process.env.SITEMAP_API_URL || `${BASE_URL}/api`).replace(/\/$/, '');

async function fetchJson(url) {
  const res = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} fetching ${url}`);
  }
  return res.json();
}

function escapeXml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

function buildUrl(loc, changefreq = 'weekly', priority = '0.7') {
  return `  <url>\n    <loc>${escapeXml(loc)}</loc>\n    <changefreq>${changefreq}</changefreq>\n    <priority>${priority}</priority>\n  </url>`;
}

async function main() {
  const staticRoutes = ['/', '/trip-planner'];

  let siteList = [];
  try {
    const list = await fetchJson(`${API_URL}/sites/list`);
    // Expecting array of { site_id, name, ... } or { id, name }
    siteList = Array.isArray(list) ? list : [];
  } catch (err) {
    console.error('Failed to fetch site list for sitemap:', err.message);
  }

  const detailRoutes = siteList
    .map((s) => s?.site_id || s?.id)
    .filter(Boolean)
    .map((id) => `/details/${encodeURIComponent(id)}`);

  const urls = [
    ...staticRoutes.map((p) => `${BASE_URL}${p}`),
    ...detailRoutes.map((p) => `${BASE_URL}${p}`),
  ];

  const xml = `<?xml version="1.0" encoding="UTF-8"?>\n` +
    `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n` +
    urls.map((u) => buildUrl(u, 'daily', '0.8')).join('\n') +
    `\n</urlset>\n`;

  const outPath = resolve(__dirname, '../public/sitemap.xml');
  await writeFile(outPath, xml, 'utf8');
  console.log(`Sitemap written to ${outPath} with ${urls.length} URLs.`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});


