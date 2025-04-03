import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './pages/Layout';
import Home from './pages/Home';
import Details from './pages/Details';
import Declined from './pages/Declined';

const App = () => {
  return (
    <Router>
      <Routes>
        <Route path="/declined" element={<Declined />} />
        <Route path="/" element={<Layout />}>
          <Route index element={<Home />} />
          <Route path="sites/:siteId" element={<Details />} />
          {/* Redirect old format URLs to new format */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Router>
  );
};

export default App;
