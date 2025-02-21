import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

const D3Forecast = ({ forecast, selectedHour }) => {
  const svgRef = useRef();
  const tooltipRef = useRef();
  const containerRef = useRef();

  useEffect(() => {
    if (!forecast) return;

    // Clear previous content
    d3.select(svgRef.current).selectAll("*").remove();

    // Calculate dimensions
    const margin = { top: 40, right: 80, bottom: 60, left: 60 };
    const container = containerRef.current;
    const width = container.clientWidth - margin.left - margin.right;
    const height = 500 - margin.top - margin.bottom;

    // Calculate x-axis ranges
    const maxTemp = Math.max(...forecast.temperature_iso_c);
    const maxWind = Math.max(...forecast.wind_speed_iso_ms);
    const maxX = Math.max(maxTemp, maxWind);
    const rhPosition = maxX + (maxX * 0.3);
    const windPosition = rhPosition - (maxX * 0.15);

    // Create scales
    const xScale = d3.scaleLinear()
      .domain([-20, rhPosition + (maxX * 0.1)])
      .range([0, width]);

    const yScale = d3.scaleLinear()
      .domain([d3.min(forecast.hpa_lvls), d3.max(forecast.hpa_lvls)])
      .range([0, height]);

    // Create SVG
    const svg = d3.select(svgRef.current)
      .attr('width', width + margin.left + margin.right)
      .attr('height', height + margin.top + margin.bottom)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Create tooltip
    const tooltip = d3.select(tooltipRef.current)
      .style('position', 'absolute')
      .style('visibility', 'hidden')
      .style('background-color', 'white')
      .style('padding', '10px')
      .style('border', '1px solid #666')
      .style('border-radius', '4px')
      .style('font-family', 'Arial')
      .style('font-size', '12px');

    // Add grid
    svg.append('g')
      .attr('class', 'grid')
      .attr('opacity', 0.1)
      .call(d3.axisBottom(xScale)
        .tickSize(height)
        .tickFormat('')
      );

    svg.append('g')
      .attr('class', 'grid')
      .attr('opacity', 0.1)
      .call(d3.axisLeft(yScale)
        .tickSize(-width)
        .tickFormat('')
      );

    // Create line generators
    const tempLine = d3.line()
      .x(d => xScale(d))
      .y((d, i) => yScale(forecast.hpa_lvls[i]));

    // Draw temperature line
    svg.append('path')
      .datum(forecast.temperature_iso_c)
      .attr('fill', 'none')
      .attr('stroke', 'red')
      .attr('stroke-width', 2)
      .attr('d', tempLine);

    // Draw dewpoint line
    svg.append('path')
      .datum(forecast.dewpoint_iso_c)
      .attr('fill', 'none')
      .attr('stroke', 'blue')
      .attr('stroke-width', 2)
      .attr('stroke-dasharray', '4')
      .attr('d', tempLine);

    // Draw wind speed line
    svg.append('path')
      .datum(forecast.wind_speed_iso_ms)
      .attr('fill', 'none')
      .attr('stroke', 'green')
      .attr('stroke-width', 2)
      .attr('d', tempLine);

    // Add wind direction arrows
    svg.selectAll('.wind-arrow')
      .data(forecast.wind_direction_iso_dgr)
      .enter()
      .append('path')
      .attr('class', 'wind-arrow')
      .attr('d', d3.symbol().type(d3.symbolTriangle).size(100))
      .attr('fill', 'green')
      .attr('transform', (d, i) => {
        const x = xScale(windPosition);
        const y = yScale(forecast.hpa_lvls[i]);
        return `translate(${x},${y}) rotate(${(d + 180) % 360})`;
      });

    // Add RH circles with text
    const rhGroup = svg.selectAll('.rh-group')
      .data(forecast.relative_humidity_iso_pct)
      .enter()
      .append('g')
      .attr('class', 'rh-group')
      .attr('transform', (d, i) => {
        const x = xScale(rhPosition);
        const y = yScale(forecast.hpa_lvls[i]);
        return `translate(${x},${y})`;
      });

    rhGroup.append('circle')
      .attr('r', 10)
      .attr('fill', d => d3.interpolateBlues(d / 100));

    rhGroup.append('text')
      .text(d => `${Math.round(d)}%`)
      .attr('text-anchor', 'middle')
      .attr('dy', '0.35em')
      .attr('fill', d => d > 50 ? 'white' : 'black')
      .style('font-size', '10px');

    // Add axes
    svg.append('g')
      .attr('transform', `translate(0,${height})`)
      .call(d3.axisBottom(xScale))
      .append('text')
      .attr('x', width / 2)
      .attr('y', 40)
      .attr('fill', 'black')
      .text('Temperature (°C) / Wind Speed (m/s)');

    svg.append('g')
      .call(d3.axisLeft(yScale))
      .append('text')
      .attr('transform', 'rotate(-90)')
      .attr('y', -40)
      .attr('x', -height / 2)
      .attr('fill', 'black')
      .style('text-anchor', 'middle')
      .text('Pressure (hPa)');

    // Add title
    svg.append('text')
      .attr('x', width / 2)
      .attr('y', -10)
      .attr('text-anchor', 'middle')
      .style('font-size', '16px')
      .text(`Atmospheric Profile - ${selectedHour}:00`);

    // Add hover functionality
    const hoverLine = svg.append('line')
      .attr('stroke', '#666')
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '5,5')
      .style('visibility', 'hidden');

    svg.append('rect')
      .attr('width', width)
      .attr('height', height)
      .attr('fill', 'none')
      .attr('pointer-events', 'all')
      .on('mousemove', function(event) {
        const [mouseX, mouseY] = d3.pointer(event);
        const closestY = yScale.invert(mouseY);
        
        // Find the closest index while ensuring it's within bounds
        const bisector = d3.bisector(d => d).left;
        let yIndex = bisector(forecast.hpa_lvls, closestY);
        
        // Ensure index is within bounds
        yIndex = Math.max(0, Math.min(yIndex, forecast.hpa_lvls.length - 1));

        // Only show tooltip if we have valid data
        if (yIndex >= 0 && yIndex < forecast.hpa_lvls.length) {
          hoverLine
            .style('visibility', 'visible')
            .attr('x1', 0)
            .attr('x2', width)
            .attr('y1', yScale(forecast.hpa_lvls[yIndex]))
            .attr('y2', yScale(forecast.hpa_lvls[yIndex]));

          // Safely access data values
          const pressure = Math.round(forecast.hpa_lvls[yIndex]);
          const temp = forecast.temperature_iso_c[yIndex]?.toFixed(1) ?? 'N/A';
          const dewpoint = forecast.dewpoint_iso_c[yIndex]?.toFixed(1) ?? 'N/A';
          const windSpeed = forecast.wind_speed_iso_ms[yIndex]?.toFixed(1) ?? 'N/A';
          const windDir = Math.round(forecast.wind_direction_iso_dgr[yIndex] ?? 0);
          const rh = Math.round(forecast.relative_humidity_iso_pct[yIndex] ?? 0);

          tooltip
            .style('visibility', 'visible')
            .style('left', `${event.pageX + 10}px`)
            .style('top', `${event.pageY - 10}px`)
            .html(`
              Pressure: ${pressure} hPa<br>
              Temperature: ${temp}°C<br>
              Dewpoint: ${dewpoint}°C<br>
              Wind: ${windSpeed} m/s @ ${windDir}°<br>
              RH: ${rh}%
            `);
        }
      })
      .on('mouseleave', function() {
        hoverLine.style('visibility', 'hidden');
        tooltip.style('visibility', 'hidden');
      });

    // Handle window resize
    const handleResize = () => {
      // Recalculate dimensions and update chart
      // This would need to re-render the entire chart
      // For better performance, you might want to debounce this function
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [forecast, selectedHour]);

  return (
    <div ref={containerRef} style={{ width: '100%', height: '100%' }}>
      <svg ref={svgRef}></svg>
      <div ref={tooltipRef}></div>
    </div>
  );
};

export default D3Forecast; 