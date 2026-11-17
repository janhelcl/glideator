import { renderFlightForecastChart, renderFlightQualityChart } from '../src/components/forecastCharts';
import { connectChartWidget } from './chartHost';

const site = document.querySelector('#site');
const controls = document.querySelector('#controls');
const date = document.querySelector('#date');
const metric = document.querySelector('#metric');
const charts = document.querySelector('#charts');
const qualityChart = document.querySelector('#flight-quality');
const forecastChart = document.querySelector('#flight-forecast');
const detail = document.querySelector('#detail');
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

connectChartWidget({
  appInfo: { name: 'Parra-Glideator forecast charts', version: '2.0.0' },
  onResult: renderResult,
  onTeardown: () => chartObserver.disconnect(),
});
