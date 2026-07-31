import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';

import { trackEvent } from '../analytics';
import QuickFeedback from './QuickFeedback';

jest.mock('../analytics', () => ({
  trackEvent: jest.fn(),
}));

describe('QuickFeedback', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('submits a contextual helpful rating once', () => {
    render(
      <QuickFeedback
        question="Was this forecast useful?"
        context={{ surface: 'site_forecast', site_id: 42, metric: 'XC20' }}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Helpful' }));

    expect(trackEvent).toHaveBeenCalledWith('recommendation_feedback_submitted', {
      surface: 'site_forecast',
      site_id: 42,
      metric: 'XC20',
      rating: 'helpful',
    });
    expect(
      screen.getByText("Thanks — this helps improve Glideator's recommendations."),
    ).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Helpful' })).not.toBeInTheDocument();
  });
});
