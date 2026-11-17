import { axisBottom, scaleBand, scaleLinear, select } from 'd3';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export function renderSeasonalityChart(element, values, metric) {
  const svgElement = select(element);
  svgElement.selectAll('*').remove();
  const containerWidth = element.parentElement.clientWidth;
  const containerHeight = element.parentElement.clientHeight;
  const baseFontSize = Math.max(8, Math.min(12, containerWidth / 60));
  const titleFontSize = Math.max(12, Math.min(16, containerWidth / 40));
  const margin = { top: 40 + titleFontSize, right: 30, bottom: 60 + baseFontSize, left: 20 };
  const width = containerWidth - margin.left - margin.right;
  const height = containerHeight - margin.top - margin.bottom;
  if (width <= 0 || height <= 0) return;

  const label = metric === 'XC0' ? 'Any Flight' : `${metric.slice(2)}+ Point Flights`;
  const title = `Days with ${label}`;
  const svg = svgElement
    .attr('role', 'img')
    .attr('aria-label', `${title}, historical monthly averages`)
    .attr('width', containerWidth)
    .attr('height', containerHeight)
    .append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`);

  const data = MONTHS.map((month, index) => ({ month, value: values[index] }));
  const x = scaleBand().domain(MONTHS).range([0, width]).padding(0.02);
  const y = scaleLinear().domain([0, 30]).range([height, 0]);

  svg.append('g')
    .attr('class', 'x-axis')
    .attr('transform', `translate(0,${height})`)
    .call(axisBottom(x))
    .selectAll('text')
    .style('font-size', `${baseFontSize}px`);

  svg.append('text')
    .attr('x', width / 2)
    .attr('y', -margin.top + titleFontSize)
    .attr('text-anchor', 'middle')
    .attr('fill', 'currentColor')
    .style('font-size', `${titleFontSize}px`)
    .style('font-weight', 'bold')
    .text(title);

  svg.selectAll('.bar')
    .data(data.filter(({ value }) => Number.isFinite(value)))
    .join('rect')
    .attr('class', 'bar')
    .attr('x', ({ month }) => x(month))
    .attr('width', x.bandwidth())
    .attr('y', ({ value }) => y(value))
    .attr('height', ({ value }) => height - y(value))
    .attr('fill', '#2196F3')
    .attr('opacity', 0.8);

  svg.selectAll('.value-label')
    .data(data)
    .join('text')
    .attr('class', 'value-label')
    .attr('x', ({ month }) => x(month) + x.bandwidth() / 2)
    .attr('y', ({ value }) => y(value ?? 0) - 5)
    .attr('text-anchor', 'middle')
    .attr('fill', 'currentColor')
    .style('font-size', `${baseFontSize}px`)
    .style('font-weight', 'bold')
    .text(({ value }) => Number.isFinite(value) ? value.toFixed(1) : '–');
}
