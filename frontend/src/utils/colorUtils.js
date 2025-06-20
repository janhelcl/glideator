// Color utility functions for probability visualization

export const getColor = (probability) => {
  if (probability === 'N/A' || probability === null || probability === undefined) return 'gray';
  const p = Math.max(0, Math.min(1, probability));
  const r = Math.round(255 * (1 - p));
  const g = Math.round(255 * p);
  return `rgb(${r}, ${g}, 0)`;
};

export const getColorWithAlpha = (probability, alpha = 0.15) => {
  if (probability === 'N/A' || probability === null || probability === undefined) return `rgba(128, 128, 128, ${alpha})`;
  const p = Math.max(0, Math.min(1, probability));
  const r = Math.round(255 * (1 - p));
  const g = Math.round(255 * p);
  return `rgba(${r}, ${g}, 0, ${alpha})`;
}; 