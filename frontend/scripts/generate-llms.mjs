// Generate llms.txt at build time by fetching from backend API
import { writeFile, mkdir } from 'node:fs/promises';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const API_URL = process.env.REACT_APP_API_BASE_URL || process.env.SITEMAP_API_URL || 'https://glideator-web.onrender.com';

async function fetchText(url) {
  console.log(`Fetching: ${url}`);
  const res = await fetch(url, { 
    headers: { Accept: 'text/plain' }
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} fetching ${url}`);
  }
  return res.text();
}

async function generateLlmsTxt() {
  try {
    // Fetch the dynamic llms.txt from backend
    const llmsContent = await fetchText(`${API_URL}/llms.txt`);
    
    // Write to public directory
    const outputPath = resolve(__dirname, '../public/llms.txt');
    await writeFile(outputPath, llmsContent, 'utf-8');
    
    console.log('✓ Generated llms.txt');
    console.log(`  Size: ${llmsContent.length} bytes`);
    
    // Count number of sites
    const siteCount = (llmsContent.match(/\/llms\/sites\/\d+\.txt/g) || []).length;
    console.log(`  Sites: ${siteCount}`);
    
  } catch (error) {
    console.error('Error generating llms.txt:', error);
    
    // Create a fallback file if the API is unavailable during build
    const fallback = `# Parra-Glideator

> AI-powered paragliding site recommendations

For the latest site information, visit: https://www.parra-glideator.com

## Note
This file will be updated after the backend API is available.
`;
    const outputPath = resolve(__dirname, '../public/llms.txt');
    await writeFile(outputPath, fallback, 'utf-8');
    console.log('⚠ Created fallback llms.txt (API unavailable during build)');
  }
}

generateLlmsTxt();

