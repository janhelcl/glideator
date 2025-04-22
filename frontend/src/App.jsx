import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Layout from './pages/Layout';
import Home from './pages/Home';
import Details from './pages/Details';
import Declined from './pages/Declined';
import NotFound from './pages/NotFound';

const lightTheme = createTheme({
  palette: {
    mode: 'light',
  },
});

const App = () => {
  return (
    <ThemeProvider theme={lightTheme}>
      <CssBaseline />
      <Router>
        <Routes>
          <Route path="/declined" element={<Declined />} />
          <Route path="/" element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="details/:siteId" element={<Details />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </Router>
    </ThemeProvider>
  );
};

export default App;
