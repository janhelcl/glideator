import { render, screen } from '@testing-library/react';
import { HelmetProvider } from 'react-helmet-async';
import App from './App';

test('renders the About page through the application router', () => {
  window.history.pushState({}, '', '/about');

  render(
    <HelmetProvider>
      <App />
    </HelmetProvider>,
  );

  expect(
    screen.getByRole('heading', {
      name: /find the promising days\. verify the details\. make the call yourself\./i,
    }),
  ).toBeInTheDocument();
});
