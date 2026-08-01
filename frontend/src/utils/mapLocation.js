export const parseMapCenter = (search) => {
  const params = search instanceof URLSearchParams
    ? search
    : new URLSearchParams(search || '');

  if (!params.has('lat') || !params.has('lng')) {
    return null;
  }

  const latitude = Number(params.get('lat'));
  const longitude = Number(params.get('lng'));

  if (
    !Number.isFinite(latitude) ||
    !Number.isFinite(longitude) ||
    latitude < -90 ||
    latitude > 90 ||
    longitude < -180 ||
    longitude > 180
  ) {
    return null;
  }

  return [latitude, longitude];
};
