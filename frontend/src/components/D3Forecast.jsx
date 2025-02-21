import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { debounce } from 'lodash';

const D3Forecast = ({ forecast, selectedHour }) => {
  const svgRef = useRef();
  const tooltipRef = useRef();
  const containerRef = useRef();

  // Create chart function to reuse for initial render and resize
  const createChart = () => {
    if (!forecast) return;

    // Clear previous content
    d3.select(svgRef.current).selectAll("*").remove();

    // Get container width
    const container = containerRef.current;
    const containerWidth = container.clientWidth;
    
    // Calculate dimensions with minimum sizes
    const margin = { 
      top: 40,
      right: Math.max(80, containerWidth * 0.1), // Responsive margin
      bottom: 60,
      left: Math.max(60, containerWidth * 0.08) // Responsive margin
    };
    
    // Set minimum width and height
    const minWidth = 400;
    const minHeight = 400;
    
    // Calculate actual width and height
    const width = Math.max(minWidth, containerWidth - margin.left - margin.right);
    const height = Math.max(minHeight, (width * 0.8)); // Maintain aspect ratio

    // Update SVG size
    const svg = d3.select(svgRef.current)
      .attr('width', width + margin.left + margin.right)
      .attr('height', height + margin.top + margin.bottom)
      .attr('viewBox', `0 0 ${width + margin.left + margin.right} ${height + margin.top + margin.bottom}`)
      .attr('preserveAspectRatio', 'xMidYMid meet')
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

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

    // Create a custom arrow path
    const createWindArrow = (direction) => {
      // Arrow dimensions
      const arrowLength = 15;
      const headLength = 6;
      const headWidth = 6;
      
      // Calculate arrow points
      const angle = (direction + 180) % 360 * (Math.PI / 180);
      const dx = Math.cos(angle);
      const dy = Math.sin(angle);
      
      // Calculate arrow coordinates
      const x0 = 0;
      const y0 = 0;
      const x1 = x0 + dx * arrowLength;
      const y1 = y0 + dy * arrowLength;
      
      // Calculate arrowhead points
      const headAngle1 = angle + Math.PI * 0.8; // 144 degrees
      const headAngle2 = angle - Math.PI * 0.8; // -144 degrees
      const xHead1 = x1 + Math.cos(headAngle1) * headLength;
      const yHead1 = y1 + Math.sin(headAngle1) * headLength;
      const xHead2 = x1 + Math.cos(headAngle2) * headLength;
      const yHead2 = y1 + Math.sin(headAngle2) * headLength;
      
      return `M ${x0} ${y0} 
              L ${x1} ${y1}
              L ${xHead1} ${yHead1}
              M ${x1} ${y1}
              L ${xHead2} ${yHead2}`;
    };

    // Replace the existing wind arrows section with this:
    svg.selectAll('.wind-arrow')
      .data(forecast.wind_direction_iso_dgr)
      .enter()
      .append('path')
      .attr('class', 'wind-arrow')
      .attr('d', d => createWindArrow(d))
      .attr('fill', 'none')
      .attr('stroke', 'green')
      .attr('stroke-width', 1.5)
      .attr('transform', (d, i) => {
        const x = xScale(windPosition);
        const y = yScale(forecast.hpa_lvls[i]);
        return `translate(${x},${y})`;
      })
      // Add hover effect
      .on('mouseover', function(event, d) {
        d3.select(this)
          .attr('stroke-width', 2.5)
          .attr('stroke', '#006400');
      })
      .on('mouseout', function() {
        d3.select(this)
          .attr('stroke-width', 1.5)
          .attr('stroke', 'green');
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

    // Update font sizes based on container width
    const baseFontSize = Math.max(10, Math.min(16, containerWidth / 50));
    
    // Update text elements with responsive font sizes
    svg.selectAll('text')
      .style('font-size', `${baseFontSize}px`);

    svg.selectAll('.rh-group text')
      .style('font-size', `${baseFontSize * 0.8}px`);

    // Update title with larger font
    svg.select('text')
      .style('font-size', `${baseFontSize * 1.2}px`);
  };

  // Initial render
  useEffect(() => {
    createChart();
  }, [forecast, selectedHour]);

  // Handle resize
  useEffect(() => {
    const handleResize = debounce(() => {
      createChart();
    }, 250); // Debounce resize events

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      handleResize.cancel(); // Cancel any pending debounced calls
    };
  }, [forecast, selectedHour]);

  return (
    <div 
      ref={containerRef} 
      style={{ 
        width: '100%',
        height: '100%',
        minWidth: '400px', // Minimum width
        position: 'relative',
        overflow: 'hidden' // Prevent overflow
      }}
    >
      <svg 
        ref={svgRef}
        style={{
          maxWidth: '100%',
          height: 'auto',
          display: 'block' // Remove extra space below SVG
        }}
      />
      <div 
        ref={tooltipRef}
        style={{
          position: 'absolute',
          pointerEvents: 'none' // Prevent tooltip from interfering with hover
        }}
      />
    </div>
  );
};

export default D3Forecast; 