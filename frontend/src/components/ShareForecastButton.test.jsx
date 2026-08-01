import React from 'react';
import { cleanup, render, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';

import ShareForecastButton, {
  buildForecastShareUrl,
  getForecastProbability,
} from './ShareForecastButton';

const date = '2026-08-03';
const predictions = [{
  date,
  values: [0.82, 0.76, 0.7, 0.64, 0.58, 0.52, 0.46, 0.4, 0.34, 0.28, 0.22],
}];

describe('ShareForecastButton compatibility helpers', () => {
  afterEach(() => cleanup());

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

  it('collapses the obsolete inline share row', async () => {
    const { container } = render(
      <div style={{ display: 'flex', minHeight: '32px' }}>
        <ShareForecastButton />
      </div>,
    );

    await waitFor(() => expect(container.firstChild.style.display).toBe('none'));
    expect(container.firstChild.style.minHeight).toBe('0px');
  });
});
