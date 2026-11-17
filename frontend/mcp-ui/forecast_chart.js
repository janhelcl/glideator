import { renderFlightForecastChart, renderFlightQualityChart } from '../src/components/forecastCharts';

const site = document.querySelector('#site');
const controls = document.querySelector('#controls');
const date = document.querySelector('#date');
const metric = document.querySelector('#metric');
const charts = document.querySelector('#charts');
const qualityChart = document.querySelector('#flight-quality');
const forecastChart = document.querySelector('#flight-forecast');
const detail = document.querySelector('#detail');
const main = document.querySelector('main');
const dateFormat = new Intl.DateTimeFormat(undefined, {
  weekday: 'short', month: 'short', day: 'numeric', timeZone: 'UTC',
});
const percentages = new Intl.NumberFormat(undefined, { style: 'percent', maximumFractionDigits: 0 });
const metrics = Array.from({ length: 11 }, (_, index) => `XC${index * 10}`);
const isMobile = matchMedia('(max-width: 899px)');
let predictions = [];

const metricLabel = (threshold) => threshold === 'XC0' ? 'any flight' : `${threshold.slice(2)}+ XC points`;
const dayLabel = (day) => dateFormat.format(new Date(day));
metric.replaceChildren(...metrics.map((threshold) =>
  new Option(threshold === 'XC0' ? 'Any flight' : metricLabel(threshold), threshold)));

function drawCharts() {
  if (charts.hidden) return;
  const options = {
    predictions,
    metrics,
    selectedDate: date.value,
    selectedMetric: metric.value,
    isMobile: isMobile.matches,
  };
  renderFlightQualityChart(qualityChart, options);
  renderFlightForecastChart(forecastChart, options);
}

function updateSelection() {
  drawCharts();
  const day = predictions.find((day) => day.date === date.value);
  const value = day?.values[metrics.indexOf(metric.value)];
  const label = dayLabel(date.value);
  detail.textContent = value == null
    ? `${label} · No data for ${metricLabel(metric.value)}`
    : `${label} · ${percentages.format(value)} chance of ${metricLabel(metric.value)}`;
}

function renderResult(result) {
  const forecast = result.structuredContent;
  const hasDays = !result.isError && Boolean(forecast?.days.length);
  controls.hidden = !hasDays;
  charts.hidden = !hasDays;
  if (!forecast || result.isError) {
    detail.textContent = 'The forecast could not be loaded.';
    return;
  }
  site.textContent = forecast.site_name;
  if (!hasDays) {
    detail.textContent = 'No flight activity forecast is currently available.';
    return;
  }

  predictions = forecast.days.map(({ date, probabilities }) => ({
    date,
    values: metrics.map((threshold) => probabilities[threshold]),
  }));
  const dates = predictions.map((day) => day.date);
  const selectedDate = forecast.selected_date ?? dates[0];
  date.replaceChildren(...dates.map((day) => new Option(dayLabel(day), day)));
  if (!dates.includes(selectedDate)) {
    date.prepend(new Option(`${dayLabel(selectedDate)} (no forecast)`, selectedDate));
  }
  date.value = selectedDate;
  metric.value = forecast.metric;
  updateSelection();
}

date.addEventListener('change', updateSelection);
metric.addEventListener('change', updateSelection);
const chartObserver = new ResizeObserver(drawCharts);
chartObserver.observe(qualityChart.parentElement);
chartObserver.observe(forecastChart.parentElement);

// View-only MCP Apps bridge. All chart data arrives in the initial tool result.
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
  if (data.method === 'ui/notifications/tool-result') renderResult(data.params);
  if (data.method === 'ui/notifications/host-context-changed') applyTheme(data.params.theme);
  if (data.method === 'ui/resource-teardown') {
    resizeObserver.disconnect();
    chartObserver.disconnect();
  }
  if (data.method === 'ui/resource-teardown' || data.method === 'ping') {
    send({ id: data.id, result: {} });
  }
});

send({
  id: 'initialize',
  method: 'ui/initialize',
  params: {
    protocolVersion: '2026-01-26',
    appInfo: { name: 'Parra-Glideator forecast charts', version: '2.0.0' },
    appCapabilities: {},
  },
});
