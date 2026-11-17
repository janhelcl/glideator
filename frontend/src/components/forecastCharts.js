import {
  axisBottom,
  curveMonotoneX,
  extent,
  line,
  pointer,
  scaleBand,
  scaleLinear,
  scaleUtc,
  select,
  utcFormat,
} from 'd3';

const BLUE = '#2196F3';
const percentage = (value) => `${Math.round(value * 100)}%`;

function setupChart(element, label) {
  const container = element.parentElement;
  const containerWidth = container.clientWidth;
  const containerHeight = container.clientHeight;
  const svgElement = select(element).attr('role', 'img').attr('aria-label', label);
  svgElement.selectAll('*').remove();
  select(container).selectAll('.d3-tooltip').remove();

  const axisFontSize = Math.max(8, Math.min(12, containerWidth / 60));
  const titleFontSize = Math.max(10, Math.min(16, containerWidth / 45));
  const narrow = containerWidth < 400;
  const margin = {
    top: 20 + titleFontSize * 2,
    right: narrow ? 15 : 20,
    bottom: (narrow ? 40 : 50) + axisFontSize,
    left: (narrow ? 40 : 50) + axisFontSize,
  };
  const width = containerWidth - margin.left - margin.right;
  const height = containerHeight - margin.top - margin.bottom;
  if (width <= 0 || height <= 0) return null;

  const svg = svgElement
    .attr('width', containerWidth)
    .attr('height', containerHeight)
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);
  const y = scaleLinear().domain([0, 1]).range([height, 0]);
  return { svg, margin, width, height, y, containerWidth, axisFontSize, titleFontSize };
}

function drawTitle(chart, title, lineNumber = 1) {
  const { svg, width, margin, titleFontSize } = chart;
  svg.append('text')
    .attr('x', width / 2)
    .attr('y', -margin.top + titleFontSize * lineNumber)
    .attr('text-anchor', 'middle')
    .attr('fill', 'currentColor')
    .style('font-size', `${titleFontSize}px`)
    .style('font-weight', 'bold')
    .text(title);
}

function drawXAxisLabel(chart, label) {
  const { svg, width, height, margin, axisFontSize } = chart;
  svg.append('text')
    .attr('transform', `translate(${width / 2}, ${height + margin.bottom - 10})`)
    .attr('text-anchor', 'middle')
    .attr('fill', 'currentColor')
    .style('font-size', `${axisFontSize + 2}px`)
    .text(label);
}

export function renderFlightQualityChart(element, { predictions, metrics, selectedDate, selectedMetric }) {
  const title = selectedDate ? `Chances of a Flight on ${selectedDate}` : 'Chances of a Flight';
  const chart = setupChart(element, title);
  if (!chart) return;
  const { svg, width, height, y, axisFontSize } = chart;
  drawTitle(chart, title);
  drawTitle(chart, 'How Far Might It Go?', 2.5);

  const prediction = predictions.find(({ date }) => date === selectedDate);
  if (!prediction) return;

  const data = metrics.map((metric, index) => ({ metric, value: prediction.values[index] }));
  const x = scaleBand().domain(metrics).range([0, width]);
  const xAxis = svg.append('g')
    .attr('transform', `translate(0,${height})`)
    .call(axisBottom(x).tickSizeOuter(0));
  const tickOffset = -x.bandwidth() / 2;
  xAxis.selectAll('.tick line').attr('transform', `translate(${tickOffset},0)`);
  xAxis.selectAll('text')
    .attr('transform', `translate(${tickOffset},0)rotate(-45)`)
    .style('text-anchor', 'end')
    .style('font-size', `${axisFontSize}px`)
    .text((metric) => metric.replace('XC', ''));
  drawXAxisLabel(chart, 'Flight Quality (XC Points)');

  svg.selectAll('.bar')
    .data(data.filter(({ value }) => Number.isFinite(value)))
    .join('rect')
    .attr('class', 'bar')
    .attr('x', ({ metric }) => x(metric))
    .attr('width', x.bandwidth())
    .attr('y', ({ value }) => y(value))
    .attr('height', ({ value }) => height - y(value))
    .attr('fill', '#4CAF50')
    .filter(({ metric }) => metric === selectedMetric)
    .attr('stroke', BLUE)
    .attr('stroke-width', 3);

  svg.selectAll('.label')
    .data(data)
    .join('text')
    .attr('class', 'label')
    .attr('x', ({ metric }) => x(metric) + x.bandwidth() / 2)
    .attr('y', ({ value }) => y(value ?? 0) - 5)
    .attr('text-anchor', 'middle')
    .attr('fill', 'currentColor')
    .style('font-size', `${axisFontSize}px`)
    .style('font-weight', 'bold')
    .text(({ value }) => Number.isFinite(value) ? percentage(value) : '–');
}

export function renderFlightForecastChart(element, { predictions, metrics, selectedDate, selectedMetric, isMobile }) {
  const title = selectedMetric === 'XC0'
    ? 'Chances of a Flight'
    : `Chances of a ${selectedMetric.replace('XC', '')}+ Point Flight`;
  const chart = setupChart(element, title);
  if (!chart) return;
  const { svg, width, height, y, containerWidth, axisFontSize } = chart;
  drawTitle(chart, title);

  const metricIndex = metrics.indexOf(selectedMetric);
  const data = predictions.map(({ date, values }) => ({
    date: new Date(date),
    value: values[metricIndex],
  })).sort((a, b) => a.date - b.date);
  if (data.length === 0) return;
  const points = data.filter(({ value }) => Number.isFinite(value));
  const x = scaleUtc().domain(extent(data, ({ date }) => date)).range([0, width]);

  svg.append('g')
    .attr('transform', `translate(0,${height})`)
    .call(axisBottom(x)
      .tickValues(data.map(({ date }) => date))
      .tickFormat(utcFormat(containerWidth < 400 || isMobile ? '%d' : '%b %d')))
    .selectAll('text')
    .style('font-size', `${axisFontSize}px`)
    .attr('transform', containerWidth < 500 ? 'translate(-5,2)rotate(-45)' : 'translate(0,0)')
    .style('text-anchor', containerWidth < 500 ? 'end' : 'middle');
  drawXAxisLabel(chart, 'Date');

  const curve = line()
    .defined(({ value }) => Number.isFinite(value))
    .x(({ date }) => x(date))
    .y(({ value }) => y(value))
    .curve(curveMonotoneX);
  svg.append('path')
    .datum(data)
    .attr('class', 'forecast-line')
    .attr('fill', 'none')
    .attr('stroke', BLUE)
    .attr('stroke-width', 3)
    .attr('d', curve);

  const dotRadius = Math.max(2, Math.min(4, width / 120));
  const selectedDotRadius = dotRadius * 1.6;
  const selectedTime = Date.parse(selectedDate);
  const isSelected = ({ date }) => date.getTime() === selectedTime;
  const dots = svg.selectAll('.dot')
    .data(points)
    .join('circle')
    .attr('class', 'dot')
    .attr('cx', ({ date }) => x(date))
    .attr('cy', ({ value }) => y(value))
    .attr('r', (point) => isSelected(point) ? selectedDotRadius : dotRadius)
    .attr('fill', (point) => isSelected(point) ? '#FFC107' : BLUE)
    .attr('stroke', (point) => isSelected(point) ? '#FF5722' : 'white')
    .attr('stroke-width', 2);

  svg.selectAll('.value-label')
    .data(points)
    .join('text')
    .attr('class', 'value-label')
    .attr('x', ({ date }) => x(date))
    .attr('y', ({ value }) => y(value) - dotRadius - 5)
    .attr('text-anchor', 'middle')
    .attr('fill', 'currentColor')
    .style('font-size', `${axisFontSize}px`)
    .style('font-weight', 'bold')
    .text(({ value }) => percentage(value));

  const container = element.parentElement;
  const tooltip = select(container).append('div')
    .attr('class', 'd3-tooltip')
    .style('position', 'absolute')
    .style('visibility', 'hidden')
    .style('background-color', 'rgba(255, 255, 255, 0.9)')
    .style('color', '#222')
    .style('border', '1px solid #ddd')
    .style('border-radius', '4px')
    .style('padding', '8px')
    .style('box-shadow', '0 2px 4px rgba(0,0,0,0.1)')
    .style('pointer-events', 'none')
    .style('font-size', `${axisFontSize}px`);
  const tooltipDate = tooltip.append('div');
  const tooltipValue = tooltip.append('div');
  dots
    .on('mouseover', function (_, { date, value }) {
      select(this).attr('r', selectedDotRadius).attr('stroke-width', 3);
      tooltipDate.text(`Date: ${date.toLocaleDateString(undefined, { timeZone: 'UTC' })}`);
      tooltipValue.text(`${selectedMetric}: ${percentage(value)}`);
      tooltip.style('visibility', 'visible');
    })
    .on('mousemove', (event) => {
      const [left, top] = pointer(event, container);
      tooltip.style('left', `${left + 10}px`).style('top', `${top - 10}px`);
    })
    .on('mouseout', function (_, point) {
      select(this).attr('r', isSelected(point) ? selectedDotRadius : dotRadius).attr('stroke-width', 2);
      tooltip.style('visibility', 'hidden');
    });
}
