import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import Home from './pages/Home';
import Details from './pages/Details'; // This will now correctly import from Details.jsx

const App = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/sites/:siteName" element={<Details />} />
      </Routes>
    </Router>
  );
};

export default App;
