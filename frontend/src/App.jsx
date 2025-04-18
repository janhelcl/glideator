import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './pages/Layout';
import Home from './pages/Home';
import Details from './pages/Details';
import Declined from './pages/Declined';
import NotFound from './pages/NotFound';

const App = () => {
  return (
    <Router>
      <Routes>
        <Route path="/declined" element={<Declined />} />
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="details/:siteId" element={<Details />} />
          {/* Redirect old format URLs to new format */}
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </Router>
  );
};

export default App;
