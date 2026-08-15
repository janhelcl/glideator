import { writeFile } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const DEFAULT_BASE_URL = 'https://www.parra-glideator.com';
const DEFAULT_API_URL = 'https://glideator-web.onrender.com';

export const STATIC_ROUTES = ['/', '/about', '/privacy', '/terms', '/support'];

const stripTrailingSlash = (value) => value.replace(/\/$/, '');

async function fetchJson(url) {
  const response = await fetch(url, { headers: { Accept: 'application/json' } });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} fetching ${url}`);
  }
  return response.json();
}

function escapeXml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

export function buildUrl(loc, changefreq = 'weekly', priority = '0.7') {
  return `  <url>\n    <loc>${escapeXml(loc)}</loc>\n    <changefreq>${changefreq}</changefreq>\n    <priority>${priority}</priority>\n  </url>`;
}

export function buildSitemapXml(siteList, baseUrl = DEFAULT_BASE_URL) {
  if (!Array.isArray(siteList) || siteList.length === 0) {
    throw new Error('Cannot generate a site sitemap without site records');
  }

  const origin = stripTrailingSlash(baseUrl);
  const siteIds = [...new Set(siteList
    .map((site) => site?.site_id || site?.id)
    .filter(Boolean))];

  const staticEntries = [
    buildUrl(`${origin}/`, 'daily', '1.0'),
    buildUrl(`${origin}/about`, 'monthly', '0.6'),
    buildUrl(`${origin}/privacy`, 'monthly', '0.3'),
    buildUrl(`${origin}/terms`, 'monthly', '0.3'),
    buildUrl(`${origin}/support`, 'monthly', '0.4'),
  ];

  const entries = [
    ...staticEntries,
    ...siteIds.map((id) => buildUrl(`${origin}/details/${encodeURIComponent(id)}`, 'daily', '0.8')),
  ];

  return `<?xml version="1.0" encoding="UTF-8"?>\n` +
    `<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n` +
    entries.join('\n') +
    `\n</urlset>\n`;
}

export async function main() {
  const baseUrl = stripTrailingSlash(process.env.SITEMAP_BASE_URL || DEFAULT_BASE_URL);
  const apiUrl = stripTrailingSlash(
    process.env.SITEMAP_API_URL || process.env.BACKEND_API_URL || DEFAULT_API_URL,
  );
  const siteList = await fetchJson(`${apiUrl}/sites/list`);
  const xml = buildSitemapXml(siteList, baseUrl);
  const outputPath = resolve(__dirname, '../public/sitemap.xml');

  await writeFile(outputPath, xml, 'utf8');
  console.log(`Sitemap written to ${outputPath} with ${siteList.length + STATIC_ROUTES.length} URLs.`);
}

const invokedPath = process.argv[1] ? pathToFileURL(resolve(process.argv[1])).href : null;
if (invokedPath === import.meta.url) {
  main().catch((error) => {
    console.error(error);
    process.exit(1);
  });
}
