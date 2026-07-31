import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { HelmetProvider } from 'react-helmet-async';
import About from './pages/About';

test('renders the About page', () => {
  render(
    <HelmetProvider>
      <MemoryRouter>
        <About />
      </MemoryRouter>
    </HelmetProvider>,
  );

  expect(
    screen.getByRole('heading', {
      name: /find the promising days\. verify the details\. make the call yourself\./i,
    }),
  ).toBeInTheDocument();
});
