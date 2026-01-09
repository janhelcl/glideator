import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';

import {
  fetchPushSubscriptions,
  registerPushSubscriptionApi,
  deactivatePushSubscriptionApi,
  fetchNotifications,
  createNotification as createNotificationApi,
  updateNotification as updateNotificationApi,
  deleteNotification as deleteNotificationApi,
  fetchNotificationEvents,
  fetchRecentNotificationEvents,
} from '../api';
import {
  supportsPush,
  registerPushServiceWorker,
  subscribeUserToPush,
  extractSubscriptionPayload,
  unsubscribeFromPush,
} from '../utils/push';
import { useAuth } from './AuthContext';

const LAST_CHECK_KEY = 'glideator_notification_last_check';

export const NotificationContext = createContext({
  pushSupported: false,
  permission: 'default',
  isLoading: false,
  error: null,
  subscriptions: [],
  notifications: [],
  eventsByNotification: {},
  missedEvents: [],
  refresh: async () => {},
  clearError: () => {},
  registerCurrentDevice: async () => {},
  deactivateSubscription: async () => {},
  createRule: async () => {},
  updateRule: async () => {},
  deleteRule: async () => {},
  loadNotificationEvents: async () => {},
  checkForMissedEvents: async () => {},
  dismissMissedEvents: () => {},
});

export const NotificationProvider = ({ children }) => {
  const { isAuthenticated } = useAuth();

  const [pushSupported, setPushSupported] = useState(() => supportsPush());
  const [permission, setPermission] = useState(() => {
    if (typeof Notification === 'undefined') {
      return 'denied';
    }
    return Notification.permission;
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [subscriptions, setSubscriptions] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [eventsByNotification, setEventsByNotification] = useState({});
  const [missedEvents, setMissedEvents] = useState([]);

  const clearState = useCallback(() => {
    setSubscriptions([]);
    setNotifications([]);
    setEventsByNotification({});
    setMissedEvents([]);
    setError(null);
  }, []);

  const refresh = useCallback(async () => {
    if (!isAuthenticated) {
      clearState();
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const [subs, notifRules] = await Promise.all([
        fetchPushSubscriptions(),
        fetchNotifications(),
      ]);
      setSubscriptions(subs);
      setNotifications(notifRules);
    } catch (err) {
      setError(err);
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated, clearState]);

  useEffect(() => {
    if (!supportsPush()) {
      setPushSupported(false);
      return;
    }
    setPushSupported(true);
    registerPushServiceWorker().catch(() => {
      // Failing to register should not crash the app, but we mark as unsupported.
      setPushSupported(false);
    });
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      refresh();
    } else {
      clearState();
    }
  }, [isAuthenticated, refresh, clearState]);

  useEffect(() => {
    if (!supportsPush()) {
      return () => {};
    }
    const handler = (event) => {
      if (event.data?.type === 'push-subscription-changed') {
        refresh();
      }
    };
    navigator.serviceWorker.addEventListener('message', handler);
    return () => {
      navigator.serviceWorker.removeEventListener('message', handler);
    };
  }, [refresh]);

  const registerCurrentDevice = useCallback(
    async (clientInfo = {}) => {
      if (!supportsPush()) {
        throw new Error('Push notifications are not supported in this browser.');
      }
      setError(null);
      try {
        await registerPushServiceWorker();
        const subscription = await subscribeUserToPush();
        setPermission(Notification.permission);
        const payload = extractSubscriptionPayload(subscription);
        if (!payload?.endpoint || !payload?.p256dh || !payload?.auth) {
          throw new Error('Failed to extract push subscription payload.');
        }
        await registerPushSubscriptionApi({
          ...payload,
          client_info: {
            userAgent: navigator.userAgent,
            platform: navigator.platform,
            ...clientInfo,
          },
        });
        await refresh();
      } catch (err) {
        setPermission(typeof Notification !== 'undefined' ? Notification.permission : 'denied');
        setError(err);
        throw err;
      }
    },
    [refresh],
  );

  const deactivateSubscription = useCallback(
    async (subscriptionId, { unsubscribeDevice = false } = {}) => {
      setError(null);
      try {
        await deactivatePushSubscriptionApi(subscriptionId);
        if (unsubscribeDevice) {
          await unsubscribeFromPush();
        }
        await refresh();
      } catch (err) {
        setError(err);
        throw err;
      }
    },
    [refresh],
  );

  const createRule = useCallback(
    async (payload) => {
      setError(null);
      try {
        const newRule = await createNotificationApi(payload);
        setNotifications((prev) => [...prev, newRule]);
        return newRule;
      } catch (err) {
        setError(err);
        throw err;
      }
    },
    [],
  );

  const updateRule = useCallback(
    async (notificationId, payload) => {
      setError(null);
      try {
        const updated = await updateNotificationApi(notificationId, payload);
        setNotifications((prev) =>
          prev.map((rule) => (rule.notification_id === notificationId ? updated : rule)),
        );
        return updated;
      } catch (err) {
        setError(err);
        throw err;
      }
    },
    [],
  );

  const deleteRule = useCallback(
    async (notificationId) => {
      setError(null);
      try {
        await deleteNotificationApi(notificationId);
        setNotifications((prev) =>
          prev.filter((rule) => rule.notification_id !== notificationId),
        );
        setEventsByNotification((prev) => {
          const next = { ...prev };
          delete next[notificationId];
          return next;
        });
      } catch (err) {
        setError(err);
        throw err;
      }
    },
    [],
  );

  const loadNotificationEvents = useCallback(async (notificationId, limit = 20) => {
    try {
      const events = await fetchNotificationEvents(notificationId, limit);
      setEventsByNotification((prev) => ({
        ...prev,
        [notificationId]: events,
      }));
      return events;
    } catch (err) {
      setError(err);
      throw err;
    }
  }, []);

  const checkForMissedEvents = useCallback(async () => {
    if (!isAuthenticated) return [];

    try {
      const lastCheck = localStorage.getItem(LAST_CHECK_KEY);
      const events = await fetchRecentNotificationEvents(lastCheck, 50);

      // Update last check time to now
      localStorage.setItem(LAST_CHECK_KEY, new Date().toISOString());

      if (events.length > 0) {
        setMissedEvents(events);
      }
      return events;
    } catch (err) {
      console.error('Failed to check for missed notifications:', err);
      return [];
    }
  }, [isAuthenticated]);

  const dismissMissedEvents = useCallback(() => {
    setMissedEvents([]);
  }, []);

  // Check for missed events on app load and when app comes to foreground
  useEffect(() => {
    if (!isAuthenticated) return;

    // Check on initial load
    checkForMissedEvents();

    // Check when app becomes visible (e.g., PWA opened after being backgrounded)
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        checkForMissedEvents();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [isAuthenticated, checkForMissedEvents]);

  const value = useMemo(
    () => ({
      pushSupported,
      permission,
      isLoading,
      error,
      subscriptions,
      notifications,
      eventsByNotification,
      missedEvents,
      refresh,
      clearError: () => setError(null),
      registerCurrentDevice,
      deactivateSubscription,
      createRule,
      updateRule,
      deleteRule,
      loadNotificationEvents,
      checkForMissedEvents,
      dismissMissedEvents,
    }),
    [
      pushSupported,
      permission,
      isLoading,
      error,
      subscriptions,
      notifications,
      eventsByNotification,
      missedEvents,
      refresh,
      registerCurrentDevice,
      deactivateSubscription,
      createRule,
      updateRule,
      deleteRule,
      loadNotificationEvents,
      checkForMissedEvents,
      dismissMissedEvents,
    ],
  );

  return <NotificationContext.Provider value={value}>{children}</NotificationContext.Provider>;
};

export const useNotifications = () => useContext(NotificationContext);
