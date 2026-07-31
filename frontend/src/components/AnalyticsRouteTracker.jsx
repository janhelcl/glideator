import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

import { trackEvent } from '../analytics';

const classifyRoute = (pathname) => {
  if (/^\/details\/[^/]+$/.test(pathname)) return '/details/:siteId';
  return pathname || '/';
};

const AnalyticsRouteTracker = () => {
  const location = useLocation();

  useEffect(() => {
    trackEvent('page_view', {
      route: classifyRoute(location.pathname),
    });
  }, [location.pathname]);

  return null;
};

export default AnalyticsRouteTracker;
