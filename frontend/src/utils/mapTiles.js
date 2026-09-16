const CARTO_TILE_URL = 'https://{s}.basemaps.cartocdn.com/rastertiles/light_nolabels/{z}/{x}/{y}.png';
const OPENSTREETMAP_TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';

const OPENSTREETMAP_ATTRIBUTION =
  'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
const CARTO_ATTRIBUTION =
  `${OPENSTREETMAP_ATTRIBUTION} | Map style: &copy; <a href="https://carto.com/attributions">CARTO</a>`;

export const getLightweightTileConfig = (
  apiKey = process.env.REACT_APP_CARTO_API_KEY || '',
) => {
  const normalizedApiKey = apiKey.trim();

  if (!normalizedApiKey) {
    return {
      url: OPENSTREETMAP_TILE_URL,
      attribution: OPENSTREETMAP_ATTRIBUTION,
      provider: 'openstreetmap',
    };
  }

  return {
    url: `${CARTO_TILE_URL}?key=${encodeURIComponent(normalizedApiKey)}`,
    attribution: CARTO_ATTRIBUTION,
    provider: 'carto',
  };
};
