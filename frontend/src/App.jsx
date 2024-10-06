import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import Home from './pages/Home';
import Details from './components/SiteDetails';

const App = () => {
  return (
    <Router>
      <Routes>
        <Route path="/sites/:siteName" element={<Details />} />
        <Route path="/" element={<Home />} />
      </Routes>
    </Router>
  );
};

export default App;