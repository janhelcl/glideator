import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './pages/Layout';
import Home from './pages/Home';
import Details from './pages/Details';
import Declined from './pages/Declined';
import NotFound from './pages/NotFound';
import TripPlannerPage from './pages/TripPlannerPage';
import { AuthProvider } from './context/AuthContext';

const App = () => {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/declined" element={<Declined />} />
          <Route path="/" element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="trip-planner" element={<TripPlannerPage />} />
            <Route path="details/:siteId" element={<Details />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </Router>
    </AuthProvider>
  );
};

export default App;
