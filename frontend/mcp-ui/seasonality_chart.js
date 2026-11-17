import { renderSeasonalityChart } from '../src/components/seasonalityChart';
import { connectChartWidget } from './chartHost';

const site = document.querySelector('#site');
const context = document.querySelector('#context');
const control = document.querySelector('#control');
const metric = document.querySelector('#metric');
const svg = document.querySelector('#seasonality');
const chart = svg.parentElement;
const metrics = Array.from({ length: 11 }, (_, index) => `XC${index * 10}`);
let monthlyStats = [];

metric.replaceChildren(...metrics.map((threshold) =>
  new Option(threshold === 'XC0' ? 'Any flight' : `${threshold.slice(2)}+ XC points`, threshold)));

function drawChart() {
  if (chart.hidden) return;
  const values = Array(12).fill(null);
  for (const { month, average_days } of monthlyStats) {
    values[month - 1] = average_days[metric.value];
  }
  renderSeasonalityChart(svg, values, metric.value);
}

function renderResult(result) {
  const seasonality = result.isError ? null : result.structuredContent;
  monthlyStats = seasonality?.months ?? [];
  const hasStats = monthlyStats.length > 0;
  control.hidden = !hasStats;
  chart.hidden = !hasStats;
  if (!seasonality) {
    context.textContent = 'The seasonality chart could not be loaded.';
    return;
  }
  site.textContent = seasonality.site_name;
  context.textContent = hasStats
    ? 'Historical average flight days per month'
    : 'No historical flight statistics are available.';
  metric.value = seasonality.metric;
  drawChart();
}

metric.addEventListener('change', drawChart);
const chartObserver = new ResizeObserver(drawChart);
chartObserver.observe(chart);

connectChartWidget({
  appInfo: { name: 'Parra-Glideator seasonality chart', version: '1.0.0' },
  onResult: renderResult,
  onTeardown: () => chartObserver.disconnect(),
});
