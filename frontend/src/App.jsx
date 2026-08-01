import React, { Suspense } from 'react';
import { Box } from '@mui/material';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Layout from './pages/Layout';
import Home from './pages/Home';
import Declined from './pages/Declined';
import NotFound from './pages/NotFound';
import Login from './pages/Login';
import Register from './pages/Register';
import Profile from './pages/Profile';
import Favorites from './pages/Favorites';
import Notifications from './pages/Notifications';
import About from './pages/About';
import Feedback from './pages/Feedback';
import DetailsRoute from './pages/DetailsRoute';
import RequireAuth from './components/RequireAuth';
import RequireAdmin from './components/RequireAdmin';
import LoadingSpinner from './components/LoadingSpinner';
import AnalyticsRouteTracker from './components/AnalyticsRouteTracker';
import { AuthProvider } from './context/AuthContext';
import { NotificationProvider } from './context/NotificationContext';

const Admin = React.lazy(() => import('./pages/Admin'));
const TripPlannerPage = React.lazy(() => import('./pages/TripPlannerPage'));

export const RouteFallback = () => (
  <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
    <LoadingSpinner />
  </Box>
);

export const AppProviders = ({ children }) => (
  <AuthProvider>
    <NotificationProvider>{children}</NotificationProvider>
  </AuthProvider>
);

export const AppRoutes = () => (
  <Routes>
    <Route path="/declined" element={<Declined />} />
    <Route path="/login" element={<Login />} />
    <Route path="/register" element={<Register />} />
    <Route path="/" element={<Layout />}>
      <Route index element={<Home />} />
      <Route path="trip-planner" element={<TripPlannerPage />} />
      <Route path="about" element={<About />} />
      <Route path="admin" element={<RequireAdmin><Admin /></RequireAdmin>} />
      <Route path="feedback" element={<RequireAuth><Feedback /></RequireAuth>} />
      <Route path="details/:siteId" element={<DetailsRoute />} />
      <Route path="profile" element={<RequireAuth><Profile /></RequireAuth>} />
      <Route path="favorites" element={<RequireAuth><Favorites /></RequireAuth>} />
      <Route path="notifications" element={<RequireAuth><Notifications /></RequireAuth>} />
      <Route path="*" element={<NotFound />} />
    </Route>
  </Routes>
);

export const AppContent = () => (
  <>
    <AnalyticsRouteTracker />
    <Suspense fallback={<RouteFallback />}>
      <AppRoutes />
    </Suspense>
  </>
);

const App = () => (
  <Router>
    <AppProviders>
      <AppContent />
    </AppProviders>
  </Router>
);

export default App;
