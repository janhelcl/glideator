import React, { useEffect, useRef, useCallback } from 'react';
import * as d3 from 'd3';
import { debounce } from 'lodash';

const D3Forecast = ({ forecast, selectedHour }) => {
  const svgRef = useRef();
  const tooltipRef = useRef();
  const containerRef = useRef();

  // Move createChart to useCallback to fix dependency warning
  const createChart = useCallback(() => {
    if (!forecast) return;

    // Clear previous content
    d3.select(svgRef.current).selectAll("*").remove();

    // Get container dimensions
    const container = containerRef.current;
    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;
    
    // Use the smaller dimension to maintain square aspect ratio
    const size = Math.min(containerWidth, containerHeight);
    
    // Calculate base font size based on container size
    const baseFontSize = Math.max(8, Math.min(12, size / 40));

    // Calculate margins based on container size
    const margin = {
      top: size * 0.1,
      right: size * 0.15,
      bottom: size * 0.15,
      left: size * 0.15
    };

    const width = size - margin.left - margin.right;
    const height = size - margin.top - margin.bottom;

    // Update SVG size
    const svg = d3.select(svgRef.current)
      .attr('width', size)
      .attr('height', size)
      .attr('viewBox', `0 0 ${size} ${size}`)
      .attr('preserveAspectRatio', 'xMidYMid meet')
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Calculate x-axis ranges with padding
    const maxTemp = Math.max(...forecast.temperature_iso_c);
    const minTemp = Math.min(...forecast.temperature_iso_c);
    const maxWind = Math.max(...forecast.wind_speed_iso_ms);
    const minWind = Math.min(...forecast.wind_speed_iso_ms);
    
    // Find overall min and max for temperature and wind only
    const minX = Math.min(minTemp, minWind);
    const maxX = Math.max(maxTemp, maxWind);
    
    // Add padding to domain
    const xPadding = (maxX - minX) * 0.1;
    const domainMin = Math.floor(minX - xPadding);
    const domainMax = Math.ceil(maxX + xPadding);
    
    // Calculate positions for RH and wind arrows
    const rhPosition = domainMax + (domainMax - domainMin) * 0.2;
    const windPosition = domainMax + (domainMax - domainMin) * 0.1;

    // Separate domains for temperature and wind
    const tempPadding = (maxTemp - minTemp) * 0.1;
    const windPadding = (maxWind - minWind) * 0.1;
    const tempDomainMin = Math.floor(minTemp - tempPadding);
    const tempDomainMax = Math.ceil(maxTemp + tempPadding);
    const windDomainMin = Math.floor(minWind - windPadding);
    const windDomainMax = Math.ceil(maxWind + windPadding);

    // Calculate positions for RH and wind arrows relative to temperature domain
    const rhPositionTemp = tempDomainMax + (tempDomainMax - tempDomainMin) * 0.25;
    const windPositionTemp = rhPositionTemp - (tempDomainMax - tempDomainMin) * 0.15;

    // Create separate scales for temperature and wind
    const tempScale = d3.scaleLinear()
      .domain([tempDomainMin, rhPositionTemp])
      .range([0, width]);

    const windScale = d3.scaleLinear()
      .domain([windDomainMin, windDomainMax])
      .range([0, width]);

    // Create scales
    const yScale = d3.scaleLinear()
      .domain([d3.min(forecast.hpa_lvls), d3.max(forecast.hpa_lvls)])
      .range([0, height]);

    // Create tooltip with initial styles
    const tooltip = d3.select(tooltipRef.current)
      .style('position', 'absolute')
      .style('visibility', 'hidden')
      .style('background-color', 'rgba(255, 255, 255, 0.9)')
      .style('padding', '12px')
      .style('border', '1px solid #666')
      .style('border-radius', '6px')
      .style('font-family', 'Arial')
      .style('font-size', `${baseFontSize}px`)
      .style('box-shadow', '0 2px 4px rgba(0,0,0,0.1)')
      .style('pointer-events', 'none');

    // Add this function to handle tooltip positioning
    const positionTooltip = (event) => {
      const tooltipNode = tooltipRef.current;
      const containerNode = containerRef.current;
      const containerRect = containerNode.getBoundingClientRect();
      
      // Get mouse position relative to container
      const mouseX = event.clientX - containerRect.left;
      const mouseY = event.clientY - containerRect.top;
      
      // Get tooltip dimensions
      const tooltipRect = tooltipNode.getBoundingClientRect();
      const tooltipWidth = tooltipRect.width;
      const tooltipHeight = tooltipRect.height;
      
      // Calculate position
      let left = mouseX + 20; // 20px offset from cursor
      let top = mouseY - tooltipHeight / 2; // Center vertically with cursor
      
      // Adjust if tooltip would overflow right edge
      if (left + tooltipWidth > containerRect.width) {
        left = mouseX - tooltipWidth - 20;
      }
      
      // Adjust if tooltip would overflow top/bottom edges
      if (top < 0) {
        top = 0;
      } else if (top + tooltipHeight > containerRect.height) {
        top = containerRect.height - tooltipHeight;
      }
      
      // Apply position
      tooltip
        .style('left', `${left}px`)
        .style('top', `${top}px`);
    };

    // Add grid
    svg.append('g')
      .attr('class', 'grid')
      .attr('opacity', 0.1)
      .call(d3.axisBottom(tempScale)
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
      .x(d => tempScale(d))
      .y((d, i) => yScale(forecast.hpa_lvls[i]));

    // Draw temperature line
    svg.append('path')
      .datum(forecast.temperature_iso_c)
      .attr('fill', 'none')
      .attr('stroke', 'red')
      .attr('stroke-width', 2)
      .attr('d', tempLine);

    // Draw dewpoint line with clipping
    svg.append('path')
      .datum(forecast.dewpoint_iso_c)
      .attr('fill', 'none')
      .attr('stroke', 'blue')
      .attr('stroke-width', 2)
      .attr('stroke-dasharray', '4')
      .attr('d', tempLine)
      .attr('clip-path', 'url(#clip)');

    // Define the clipping path
    svg.append('defs')
      .append('clipPath')
      .attr('id', 'clip')
      .append('rect')
      .attr('width', width)  // Use the full width of the chart
      .attr('height', height);

    // Draw wind speed line
    const windLine = d3.line()
      .x(d => windScale(d))
      .y((d, i) => yScale(forecast.hpa_lvls[i]));

    svg.append('path')
      .datum(forecast.wind_speed_iso_ms)
      .attr('fill', 'none')
      .attr('stroke', 'green')
      .attr('stroke-width', 2)
      .attr('d', windLine);

    // Add the new function to convert meteorological degrees to D3 angle
    const metToD3Angle = (metDegrees) => ((90 - metDegrees) * Math.PI) / 180;

    // Update the createWindArrow function to use the new angle calculation
    const createWindArrow = (direction) => {
      const arrowLength = 15;
      const headLength = 6;
      
      // Use the new function to calculate the angle
      const angle = metToD3Angle(direction);
      const adjustedAngle = angle + Math.PI; // Rotate by 180 degrees
      const dx = Math.cos(adjustedAngle);
      const dy = Math.sin(adjustedAngle);
      
      const x0 = 0;
      const y0 = 0;
      const x1 = x0 + dx * arrowLength;
      const y1 = y0 - dy * arrowLength;
      
      const headAngle1 = adjustedAngle + Math.PI * 0.8;
      const headAngle2 = adjustedAngle - Math.PI * 0.8;
      const xHead1 = x1 + Math.cos(headAngle1) * headLength;
      const yHead1 = y1 - Math.sin(headAngle1) * headLength;
      const xHead2 = x1 + Math.cos(headAngle2) * headLength;
      const yHead2 = y1 - Math.sin(headAngle2) * headLength;
      
      return `M ${x0} ${y0} 
              L ${x1} ${y1}
              L ${xHead1} ${yHead1}
              M ${x1} ${y1}
              L ${xHead2} ${yHead2}`;
    };

    // Update the wind arrows positioning
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
        // Use fixed position for wind arrows instead of wind scale
        const x = tempScale(windPositionTemp);  // Use the fixed position
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
        const x = tempScale(rhPositionTemp);
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
      .call(d3.axisBottom(tempScale))
      .append('text')
      .attr('x', width / 2)
      .attr('y', margin.bottom * 0.7)
      .attr('fill', 'black')
      .attr('text-anchor', 'middle')
      .style('font-size', `${baseFontSize}px`)
      .text('Temperature (°C)');

    svg.append('g')
      .call(d3.axisLeft(yScale))
      .append('text')
      .attr('transform', 'rotate(-90)')
      .attr('y', -margin.left * 0.7)
      .attr('x', -height / 2)
      .attr('fill', 'black')
      .style('text-anchor', 'middle')
      .style('font-size', `${baseFontSize}px`)
      .text('Pressure (hPa)');

    // Add wind axis (top)
    svg.append('g')
      .call(d3.axisTop(windScale))
      .append('text')
      .attr('x', width / 2)
      .attr('y', -margin.top * 0.4)
      .attr('fill', 'black')
      .attr('text-anchor', 'middle')
      .style('font-size', `${baseFontSize}px`)
      .text('Wind Speed (m/s)');

    // Add title
    svg.append('text')
      .attr('x', width / 2)
      .attr('y', -margin.top * 0.3)
      .attr('text-anchor', 'middle')
      .style('font-size', `${baseFontSize * 1.2}px`)
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
        const [, mouseY] = d3.pointer(event);
        const closestY = yScale.invert(mouseY);
        
        const bisector = d3.bisector(d => d).left;
        let yIndex = bisector(forecast.hpa_lvls, closestY);
        yIndex = Math.max(0, Math.min(yIndex, forecast.hpa_lvls.length - 1));

        if (yIndex >= 0 && yIndex < forecast.hpa_lvls.length) {
          hoverLine
            .style('visibility', 'visible')
            .attr('x1', 0)
            .attr('x2', width)
            .attr('y1', yScale(forecast.hpa_lvls[yIndex]))
            .attr('y2', yScale(forecast.hpa_lvls[yIndex]));

          // Update tooltip content
          const pressure = Math.round(forecast.hpa_lvls[yIndex]);
          const temp = forecast.temperature_iso_c[yIndex]?.toFixed(1) ?? 'N/A';
          const dewpoint = forecast.dewpoint_iso_c[yIndex]?.toFixed(1) ?? 'N/A';
          const windSpeed = forecast.wind_speed_iso_ms[yIndex]?.toFixed(1) ?? 'N/A';
          const windDir = Math.round(forecast.wind_direction_iso_dgr[yIndex] ?? 0);
          const rh = Math.round(forecast.relative_humidity_iso_pct[yIndex] ?? 0);

          tooltip
            .style('visibility', 'visible')
            .html(`
              <div style="
                display: grid;
                grid-template-columns: auto auto;
                gap: 4px;
                white-space: nowrap;
              ">
                <span style="color: #666">Pressure:</span> <span>${pressure} hPa</span>
                <span style="color: #666">Temp:</span> <span style="color: red">${temp}°C</span>
                <span style="color: #666">Dewpoint:</span> <span style="color: blue">${dewpoint}°C</span>
                <span style="color: #666">Wind:</span> <span style="color: green">${windSpeed} m/s @ ${windDir}°</span>
                <span style="color: #666">RH:</span> <span>${rh}%</span>
              </div>
            `);
          
          // Position the tooltip
          positionTooltip(event);
        }
      })
      .on('mouseleave', function() {
        hoverLine.style('visibility', 'hidden');
        tooltip.style('visibility', 'hidden');
      });

    // Update text elements with responsive font sizes
    svg.selectAll('text')
      .style('font-size', `${baseFontSize}px`);

    svg.selectAll('.rh-group text')
      .style('font-size', `${baseFontSize * 0.8}px`);

    // Update title with larger font
    svg.select('text')
      .style('font-size', `${baseFontSize * 1.2}px`);
  }, [forecast, selectedHour]); // Add dependencies for useCallback

  // Initial render
  useEffect(() => {
    createChart();
  }, [createChart]); // Update dependency

  // Handle resize
  useEffect(() => {
    const handleResize = debounce(() => {
      createChart();
    }, 250);

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      handleResize.cancel();
    };
  }, [createChart]); // Update dependency

  return (
    <div 
      ref={containerRef} 
      style={{ 
        width: '100%',
        height: '100%',
        position: 'relative'
      }}
    >
      <svg 
        ref={svgRef}
        style={{
          width: '100%',
          height: '100%',
          display: 'block'
        }}
      />
      <div 
        ref={tooltipRef}
        style={{
          position: 'absolute',
          pointerEvents: 'none'
        }}
      />
    </div>
  );
};

export default D3Forecast; 