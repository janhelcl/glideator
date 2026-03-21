import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './pages/Layout';
import Home from './pages/Home';
import Details from './pages/Details';
import Declined from './pages/Declined';
import NotFound from './pages/NotFound';
import TripPlannerPage from './pages/TripPlannerPage';
import Login from './pages/Login';
import Register from './pages/Register';
import Profile from './pages/Profile';
import Favorites from './pages/Favorites';
import Notifications from './pages/Notifications';
import About from './pages/About';
import RequireAuth from './components/RequireAuth';
import { AuthProvider } from './context/AuthContext';
import { NotificationProvider } from './context/NotificationContext';

const App = () => {
  return (
    <AuthProvider>
      <NotificationProvider>
        <Router>
          <Routes>
            <Route path="/declined" element={<Declined />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/" element={<Layout />}>
              <Route index element={<Home />} />
              <Route path="trip-planner" element={<TripPlannerPage />} />
              <Route path="about" element={<About />} />
              <Route path="details/:siteId" element={<Details />} />
              <Route
                path="profile"
                element={(
                  <RequireAuth>
                    <Profile />
                  </RequireAuth>
                )}
              />
              <Route
                path="favorites"
                element={(
                  <RequireAuth>
                    <Favorites />
                  </RequireAuth>
                )}
              />
              <Route
                path="notifications"
                element={(
                  <RequireAuth>
                    <Notifications />
                  </RequireAuth>
                )}
              />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </Router>
      </NotificationProvider>
    </AuthProvider>
  );
};

export default App;
