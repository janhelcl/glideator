export function connectChartWidget({ appInfo, onResult, onTeardown }) {
  const main = document.querySelector('main');
  const send = (message) => window.parent.postMessage({ jsonrpc: '2.0', ...message }, '*');
  const applyTheme = (theme) => {
    if (theme === 'light' || theme === 'dark') document.documentElement.dataset.theme = theme;
  };
  applyTheme(matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');

  const resizeObserver = new ResizeObserver(() => send({
    method: 'ui/notifications/size-changed',
    params: { height: Math.ceil(main.getBoundingClientRect().height) },
  }));

  window.addEventListener('message', ({ source, data }) => {
    if (source !== window.parent || data?.jsonrpc !== '2.0') return;
    if (data.id === 'initialize' && data.result) {
      applyTheme(data.result.hostContext?.theme);
      send({ method: 'ui/notifications/initialized' });
      resizeObserver.observe(main);
    }
    if (data.method === 'ui/notifications/tool-result') onResult(data.params);
    if (data.method === 'ui/notifications/host-context-changed') applyTheme(data.params.theme);
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
}
