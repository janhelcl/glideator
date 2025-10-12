const VAPID_PUBLIC_KEY = process.env.REACT_APP_VAPID_PUBLIC_KEY || '';

const urlBase64ToUint8Array = (base64String) => {
  try {
    const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; i += 1) {
      outputArray[i] = rawData.charCodeAt(i);
    }

    return outputArray;
  } catch (error) {
    throw new Error('Invalid VAPID public key. Please set REACT_APP_VAPID_PUBLIC_KEY to a valid URL-safe base64 string.');
  }
};

export const supportsPush = () =>
  'serviceWorker' in navigator &&
  'PushManager' in window &&
  'Notification' in window;

export const registerPushServiceWorker = async () => {
  if (!supportsPush()) {
    return null;
  }

  const registration = await navigator.serviceWorker.register('/push-sw.js');
  return registration;
};

export const getExistingSubscription = async () => {
  if (!supportsPush()) {
    return null;
  }
  const registration = await navigator.serviceWorker.ready;
  return registration.pushManager.getSubscription();
};

export const subscribeUserToPush = async () => {
  if (!supportsPush()) {
    throw new Error('Push notifications are not supported in this browser.');
  }

  const permission = await Notification.requestPermission();
  if (permission !== 'granted') {
    throw new Error('Push notification permission was not granted.');
  }

  const registration = await navigator.serviceWorker.ready;
  const existingSubscription = await registration.pushManager.getSubscription();
  if (existingSubscription) {
    return existingSubscription;
  }

  if (!VAPID_PUBLIC_KEY) {
    throw new Error('Missing VAPID public key configuration.');
  }

  const applicationServerKey = urlBase64ToUint8Array(VAPID_PUBLIC_KEY);
  return registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey,
  });
};

export const unsubscribeFromPush = async () => {
  const subscription = await getExistingSubscription();
  if (!subscription) {
    return false;
  }
  return subscription.unsubscribe();
};

export const extractSubscriptionPayload = (subscription) => {
  if (!subscription) {
    return null;
  }
  const json = subscription.toJSON();
  return {
    endpoint: json.endpoint,
    p256dh: json.keys?.p256dh,
    auth: json.keys?.auth,
  };
};
