export function connectChartWidget({ appInfo, onResult, onTeardown, onHostContext }) {
  const main = document.querySelector('main');
  const send = (message) => window.parent.postMessage({ jsonrpc: '2.0', ...message }, '*');
  const applyTheme = (theme) => {
    if (theme === 'light' || theme === 'dark') document.documentElement.dataset.theme = theme;
  };
  const applyHostContext = (context = {}) => {
    applyTheme(context.theme);
    onHostContext?.(context);
  };
  applyTheme(matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');

  const resizeObserver = new ResizeObserver(() => send({
    method: 'ui/notifications/size-changed',
    params: { height: Math.ceil(main.getBoundingClientRect().height) },
  }));

  window.addEventListener('message', ({ source, data }) => {
    if (source !== window.parent || data?.jsonrpc !== '2.0') return;
    if (data.id === 'initialize' && data.result) {
      applyHostContext(data.result.hostContext);
      send({ method: 'ui/notifications/initialized' });
      resizeObserver.observe(main);
    }
    if (data.method === 'ui/notifications/tool-result') onResult(data.params);
    if (data.method === 'ui/notifications/host-context-changed') applyHostContext(data.params);
    if (data.id === 'display-mode' && data.result?.mode) {
      applyHostContext({ displayMode: data.result.mode });
    }
    if (data.method === 'ui/resource-teardown') {
      resizeObserver.disconnect();
      onTeardown();
    }
    if (data.method === 'ui/resource-teardown' || data.method === 'ping') {
      send({ id: data.id, result: {} });
    }
  });

  send({
    id: 'initialize',
    method: 'ui/initialize',
    params: { protocolVersion: '2026-01-26', appInfo, appCapabilities: {} },
  });
  let linkRequest = 0;
  return {
    openLink: (url) => send({ id: `open-link-${++linkRequest}`, method: 'ui/open-link', params: { url } }),
    requestDisplayMode: (mode) => send({
      id: 'display-mode', method: 'ui/request-display-mode', params: { mode },
    }),
  };
}
