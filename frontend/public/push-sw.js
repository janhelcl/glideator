/* eslint-disable no-restricted-globals */

const DEFAULT_NOTIFICATION_OPTIONS = {
  icon: '/logo192.png',
  badge: '/logo192.png',
  data: {},
};

self.addEventListener('push', (event) => {
  if (!event.data) {
    return;
  }

  let payload;
  try {
    payload = event.data.json();
  } catch (err) {
    payload = { title: 'Glideator Notification', body: event.data.text() };
  }

  const {
    title = 'Glideator Notification',
    body = '',
    data = {},
    actions = [],
  } = payload;

  const options = {
    ...DEFAULT_NOTIFICATION_OPTIONS,
    body,
    data,
    actions,
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  const targetUrl =
    (event.notification.data && event.notification.data.url) ||
    '/notifications';

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      const matchingClient = clientList.find((client) => {
        return client.url.includes(targetUrl) && 'focus' in client;
      });

      if (matchingClient) {
        return matchingClient.focus();
      }

      if (self.clients.openWindow) {
        return self.clients.openWindow(targetUrl);
      }

      return null;
    }),
  );
});

self.addEventListener('pushsubscriptionchange', (event) => {
  // This event fires if the browser invalidates the subscription.
  // The frontend listens for postMessages to refresh its local state.
  event.waitUntil(
    (async () => {
      const clients = await self.clients.matchAll({ includeUncontrolled: true });
      clients.forEach((client) => {
        client.postMessage({ type: 'push-subscription-changed' });
      });
    })(),
  );
});
