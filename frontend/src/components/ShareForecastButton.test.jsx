import React from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import ShareForecastButton, {
  buildForecastShareUrl,
  getForecastProbability,
} from './ShareForecastButton';
import { trackEvent } from '../analytics';

vi.mock('../analytics', () => ({
  trackEvent: vi.fn(() => Promise.resolve(null)),
}));

const date = '2026-08-03';
const predictions = [{
  date,
  values: [0.82, 0.76, 0.7, 0.64, 0.58, 0.52, 0.46, 0.4, 0.34, 0.28, 0.22],
}];

const setNavigatorProperty = (name, value) => {
  Object.defineProperty(window.navigator, name, {
    configurable: true,
    value,
  });
};

describe('ShareForecastButton', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.history.replaceState({}, '', `/details/1?date=${date}&metric=XC20&tab=resources`);
  });

  afterEach(() => {
    cleanup();
    setNavigatorProperty('share', undefined);
    setNavigatorProperty('clipboard', undefined);
  });

  it('builds a deterministic forecast URL with only date and metric state', () => {
    expect(buildForecastShareUrl({
      origin: 'https://www.parra-glideator.com/',
      siteId: 1,
      selectedDate: date,
      selectedMetric: 'XC20',
    })).toBe(`https://www.parra-glideator.com/details/1?date=${date}&metric=XC20`);
  });

  it('selects the probability for the requested metric and date', () => {
    expect(getForecastProbability({
      predictions,
      selectedDate: date,
      selectedMetric: 'XC20',
    })).toBe(0.7);
  });

  it('uses the native share sheet when available', async () => {
    const share = vi.fn().mockResolvedValue(undefined);
    setNavigatorProperty('share', share);

    render(
      <ShareForecastButton
        siteId={1}
        siteName="Raná"
        selectedDate={date}
        selectedMetric="XC20"
        predictions={predictions}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Share forecast for Raná' }));

    await waitFor(() => expect(share).toHaveBeenCalledTimes(1));
    expect(share).toHaveBeenCalledWith(expect.objectContaining({
      title: 'Raná forecast – Parra-Glideator',
      text: expect.stringContaining('70% Glideator probability for XC20'),
      url: `${window.location.origin}/details/1?date=${date}&metric=XC20`,
    }));
    expect(trackEvent).toHaveBeenCalledWith('forecast_shared', expect.objectContaining({
      site_id: 1,
      date,
      metric: 'XC20',
      probability: 0.7,
      method: 'native',
    }));
  });

  it('copies the clean link when native sharing is unavailable', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    setNavigatorProperty('share', undefined);
    setNavigatorProperty('clipboard', { writeText });

    render(
      <ShareForecastButton
        siteId={1}
        siteName="Raná"
        selectedDate={date}
        selectedMetric="XC20"
        predictions={predictions}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Share forecast for Raná' }));

    await waitFor(() => expect(writeText).toHaveBeenCalledWith(
      `${window.location.origin}/details/1?date=${date}&metric=XC20`,
    ));
    expect(await screen.findByText('Forecast link copied')).toBeInTheDocument();
    expect(trackEvent).toHaveBeenCalledWith('forecast_shared', expect.objectContaining({
      site_id: 1,
      date,
      metric: 'XC20',
      probability: 0.7,
      method: 'clipboard',
    }));
  });
});
