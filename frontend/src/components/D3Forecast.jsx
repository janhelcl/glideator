import React, { useEffect, useRef, useCallback } from 'react';
import * as d3 from 'd3';
import { debounce } from 'lodash';

const D3Forecast = ({ forecast, selectedHour, date, gfs_forecast_at, computed_at }) => {
  const svgRef = useRef();
  const tooltipRef = useRef();
  const containerRef = useRef();
  const clipIdRef = useRef(`clip-${Math.random().toString(36).substr(2, 9)}`);

  const createChart = useCallback(() => {
    if (!forecast) return;

    d3.select(svgRef.current).selectAll("*").remove();

    const container = containerRef.current;
    const containerWidth = container.clientWidth;
    const containerHeight = container.clientHeight;
    const size = Math.min(containerWidth, containerHeight);
    const baseFontSize = Math.max(8, Math.min(12, size / 40));

    const margin = {
      top: size < 400 ? size * 0.2 : size * 0.15,
      right: size * 0.15,
      bottom: size * 0.15,
      left: size * 0.15
    };

    const width = size - margin.left - margin.right;
    const height = size - margin.top - margin.bottom;

    const svg = d3.select(svgRef.current)
      .attr('width', size)
      .attr('height', size)
      .attr('viewBox', `0 0 ${size} ${size}`)
      .attr('preserveAspectRatio', 'xMidYMid meet')
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // --- Filter to only above-surface levels ---
    const sfcHeight = forecast.geopotential_height_sfc_m ?? 0;
    const geoHeights = forecast.geopotential_height_iso_m;
    const aboveIndices = [];
    for (let i = 0; i < geoHeights.length; i++) {
      if (geoHeights[i] != null && geoHeights[i] > sfcHeight) {
        aboveIndices.push(i);
      }
    }
    if (aboveIndices.length === 0) return;

    const filteredHeights = aboveIndices.map(i => geoHeights[i]);
    const filteredTemp = aboveIndices.map(i => forecast.temperature_iso_c[i]);
    const filteredDewpoint = aboveIndices.map(i => forecast.dewpoint_iso_c[i]);
    const filteredWindSpeed = aboveIndices.map(i => forecast.wind_speed_iso_ms[i]);
    const filteredWindDir = aboveIndices.map(i => forecast.wind_direction_iso_dgr[i]);
    const filteredRH = aboveIndices.map(i => forecast.relative_humidity_iso_pct[i]);
    const filteredPressure = aboveIndices.map(i => forecast.hpa_lvls[i]);

    // --- Y-axis: height in meters AMSL ---
    const minHeight = sfcHeight;
    const maxHeight = d3.max(filteredHeights);

    const yScale = d3.scaleLinear()
      .domain([minHeight, maxHeight])
      .range([height, 0]);

    // --- X-axis: temperature ---
    const temp2m = forecast.temperature_2m_c;
    const dewpoint2m = forecast.dewpoint_2m_c;
    const allTemps = [...filteredTemp.filter(v => v != null), temp2m];
    const allDewpoints = [...filteredDewpoint.filter(v => v != null), dewpoint2m];
    const dalrAtTop = temp2m - 9.8 * ((maxHeight - sfcHeight) / 1000);
    const smrAtTop = dewpoint2m - 2.0 * ((maxHeight - sfcHeight) / 1000);
    const minTemp = Math.min(...allTemps, ...allDewpoints, dalrAtTop, smrAtTop);
    const maxTemp = Math.max(...allTemps, ...allDewpoints);

    const tempPadding = (maxTemp - minTemp) * 0.1;
    const tempDomainMin = Math.floor(minTemp - tempPadding);
    const tempDomainMax = Math.ceil(maxTemp + tempPadding);

    const rhPositionTemp = tempDomainMax + (tempDomainMax - tempDomainMin) * 0.25;
    const windPositionTemp = rhPositionTemp - (tempDomainMax - tempDomainMin) * 0.15;

    const tempScale = d3.scaleLinear()
      .domain([tempDomainMin, rhPositionTemp])
      .range([0, width]);

    // --- Surface wind ---
    const windSpeed10m = forecast.wind_speed_10m_ms;
    const windDir10m = forecast.wind_direction_10m_dgr;
    const windSpeedWithSfc = [...filteredWindSpeed, windSpeed10m];
    const windDirWithSfc = [...filteredWindDir, windDir10m];
    const windHeightsWithSfc = [...filteredHeights, sfcHeight];

    // --- Wind scale (top axis) ---
    const allWindSpeeds = windSpeedWithSfc.filter(v => v != null);
    const maxWind = Math.max(...allWindSpeeds);
    const minWind = Math.min(...allWindSpeeds);
    const windPadding = (maxWind - minWind) * 0.1 || 1;
    const windDomainMin = Math.floor(minWind - windPadding);
    const windDomainMax = Math.ceil(maxWind + windPadding);

    const windScale = d3.scaleLinear()
      .domain([windDomainMin, windDomainMax])
      .range([0, width]);

    // --- Tooltip ---
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

    const positionTooltip = (event) => {
      const tooltipNode = tooltipRef.current;
      const containerNode = containerRef.current;
      const containerRect = containerNode.getBoundingClientRect();
      const mouseX = event.clientX - containerRect.left;
      const mouseY = event.clientY - containerRect.top;
      const tooltipRect = tooltipNode.getBoundingClientRect();
      const tooltipWidth = tooltipRect.width;
      const tooltipHeight = tooltipRect.height;

      let left = mouseX + 20;
      let top = mouseY - tooltipHeight / 2;
      if (left + tooltipWidth > containerRect.width) {
        left = mouseX - tooltipWidth - 20;
      }
      if (top < 0) top = 0;
      else if (top + tooltipHeight > containerRect.height) {
        top = containerRect.height - tooltipHeight;
      }
      tooltip.style('left', `${left}px`).style('top', `${top}px`);
    };

    // --- Grid ---
    svg.append('g')
      .attr('class', 'grid')
      .attr('opacity', 0.1)
      .call(d3.axisBottom(tempScale).tickSize(height).tickFormat(''));

    svg.append('g')
      .attr('class', 'grid')
      .attr('opacity', 0.1)
      .call(d3.axisLeft(yScale).tickSize(-width).tickFormat(''));

    // --- Clipping path ---
    svg.append('defs')
      .append('clipPath')
      .attr('id', clipIdRef.current)
      .append('rect')
      .attr('width', width)
      .attr('height', height);

    // --- Build temp/dewpoint arrays ending at surface values ---
    // filteredHeights are in decreasing order (highest altitude first),
    // so surface values go at the end for a continuous line from top to surface.
    const tempWithSfc = [...filteredTemp, temp2m];
    const dewpointWithSfc = [...filteredDewpoint, dewpoint2m];
    const heightsWithSfc = [...filteredHeights, sfcHeight];

    const tempLine = d3.line()
      .defined((d) => d != null)
      .x(d => tempScale(d))
      .y((d, i) => yScale(heightsWithSfc[i]));

    const windLine = d3.line()
      .defined((d) => d != null)
      .x(d => windScale(d))
      .y((d, i) => yScale(windHeightsWithSfc[i]));

    // --- DALR line (from surface temp) ---
    const xyLine = d3.line()
      .x(d => tempScale(d.temp))
      .y(d => yScale(d.height));

    const dalrPoints = heightsWithSfc.map(h => ({
      temp: temp2m - 9.8 * ((h - sfcHeight) / 1000),
      height: h
    }));

    svg.append('path')
      .datum(dalrPoints)
      .attr('fill', 'none')
      .attr('stroke', 'orange')
      .attr('stroke-width', 1.5)
      .attr('stroke-dasharray', '6,3')
      .attr('d', xyLine)
      .attr('clip-path', `url(#${clipIdRef.current})`);

    // --- Mixing ratio line (from surface dewpoint, ~2 C/km lapse) ---
    const smrPoints = heightsWithSfc.map(h => ({
      temp: dewpoint2m - 2.0 * ((h - sfcHeight) / 1000),
      height: h
    }));

    svg.append('path')
      .datum(smrPoints)
      .attr('fill', 'none')
      .attr('stroke', 'lightblue')
      .attr('stroke-width', 1.5)
      .attr('stroke-dasharray', '6,3')
      .attr('d', xyLine)
      .attr('clip-path', `url(#${clipIdRef.current})`);

    // --- Temperature line (starts from surface) ---
    svg.append('path')
      .datum(tempWithSfc)
      .attr('fill', 'none')
      .attr('stroke', 'red')
      .attr('stroke-width', 2)
      .attr('d', tempLine)
      .attr('clip-path', `url(#${clipIdRef.current})`);

    // --- Dewpoint line (starts from surface) ---
    svg.append('path')
      .datum(dewpointWithSfc)
      .attr('fill', 'none')
      .attr('stroke', 'blue')
      .attr('stroke-width', 2)
      .attr('stroke-dasharray', '4')
      .attr('d', tempLine)
      .attr('clip-path', `url(#${clipIdRef.current})`);

    // --- Wind speed line (includes surface) ---
    svg.append('path')
      .datum(windSpeedWithSfc)
      .attr('fill', 'none')
      .attr('stroke', 'green')
      .attr('stroke-width', 2)
      .attr('d', windLine);

    // --- Wind arrows ---
    const metToD3Angle = (metDegrees) => ((90 - metDegrees) * Math.PI) / 180;

    const createWindArrow = (direction) => {
      const arrowLength = 15;
      const headLength = 6;
      const angle = metToD3Angle(direction);
      const adjustedAngle = angle + Math.PI;
      const dx = Math.cos(adjustedAngle);
      const dy = Math.sin(adjustedAngle);
      const x0 = 0, y0 = 0;
      const x1 = x0 + dx * arrowLength;
      const y1 = y0 - dy * arrowLength;
      const headAngle1 = adjustedAngle + Math.PI * 0.8;
      const headAngle2 = adjustedAngle - Math.PI * 0.8;
      const xHead1 = x1 + Math.cos(headAngle1) * headLength;
      const yHead1 = y1 - Math.sin(headAngle1) * headLength;
      const xHead2 = x1 + Math.cos(headAngle2) * headLength;
      const yHead2 = y1 - Math.sin(headAngle2) * headLength;
      return `M ${x0} ${y0} L ${x1} ${y1} L ${xHead1} ${yHead1} M ${x1} ${y1} L ${xHead2} ${yHead2}`;
    };

    svg.selectAll('.wind-arrow')
      .data(windDirWithSfc)
      .enter()
      .append('path')
      .attr('class', 'wind-arrow')
      .attr('d', d => d != null ? createWindArrow(d) : '')
      .attr('fill', 'none')
      .attr('stroke', 'green')
      .attr('stroke-width', 1.5)
      .attr('transform', (d, i) => {
        const x = tempScale(windPositionTemp);
        const y = yScale(windHeightsWithSfc[i]);
        return `translate(${x},${y})`;
      })
      .on('mouseover', function() {
        d3.select(this).attr('stroke-width', 2.5).attr('stroke', '#006400');
      })
      .on('mouseout', function() {
        d3.select(this).attr('stroke-width', 1.5).attr('stroke', 'green');
      });

    // --- RH circles ---
    const rhGroup = svg.selectAll('.rh-group')
      .data(filteredRH)
      .enter()
      .append('g')
      .attr('class', 'rh-group')
      .attr('transform', (d, i) => {
        const x = tempScale(rhPositionTemp);
        const y = yScale(filteredHeights[i]);
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

    // --- Axes ---
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
      .call(d3.axisLeft(yScale).tickFormat(d => `${d}`))
      .append('text')
      .attr('transform', 'rotate(-90)')
      .attr('y', -margin.left * 0.7)
      .attr('x', -height / 2)
      .attr('fill', 'black')
      .style('text-anchor', 'middle')
      .style('font-size', `${baseFontSize}px`)
      .text('Altitude (m AMSL)');

    const isSmallScreen = size < 400;

    svg.append('g')
      .call(d3.axisTop(windScale).ticks(isSmallScreen ? 4 : undefined))
      .append('text')
      .attr('x', width / 2)
      .attr('y', isSmallScreen ? -margin.top * 0.4 : -margin.top * 0.25)
      .attr('fill', 'black')
      .attr('text-anchor', 'middle')
      .style('font-size', isSmallScreen ? `${baseFontSize * 0.9}px` : `${baseFontSize}px`)
      .text(size < 300 ? 'Wind (m/s)' : 'Wind Speed (m/s)');

    // --- Legend ---
    const legendData = [
      { label: 'Temp', color: 'red', dash: null },
      { label: 'Dewpoint', color: 'blue', dash: '4' },
      { label: 'Wind', color: 'green', dash: null },
    ];
    const legendX = 6;
    const legendY = 6;
    const legendSpacing = baseFontSize * 1.6;

    legendData.forEach((item, i) => {
      const g = svg.append('g')
        .attr('transform', `translate(${legendX}, ${legendY + i * legendSpacing})`);
      g.append('line')
        .attr('x1', 0).attr('x2', 18)
        .attr('y1', 0).attr('y2', 0)
        .attr('stroke', item.color)
        .attr('stroke-width', 2)
        .attr('stroke-dasharray', item.dash);
      g.append('text')
        .attr('x', 22)
        .attr('dy', '0.35em')
        .style('font-size', `${baseFontSize * 0.85}px`)
        .attr('fill', '#333')
        .text(item.label);
    });

    // --- Title ---
    const formatDate = (dateStr) => {
      return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric', month: 'short', day: 'numeric'
      });
    };
    const formatDateTime = (dateTimeStr) => {
      return new Date(dateTimeStr).toLocaleString('en-US', {
        month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false
      });
    };

    const titleGroup = svg.append('g')
      .attr('class', 'title-group')
      .attr('transform', `translate(${width / 2}, ${-margin.top * 0.85})`);

    titleGroup.append('text')
      .attr('class', 'main-title')
      .attr('text-anchor', 'middle')
      .attr('dy', '0em')
      .style('font-size', `${baseFontSize * 1.2}px`)
      .style('font-weight', 'bold')
      .text(`Atmospheric Profile - ${formatDate(date)} ${selectedHour}:00`);

    const isValidDate = (dateStr) => {
      if (!dateStr) return false;
      const d = new Date(dateStr);
      return d instanceof Date && !isNaN(d);
    };

    if (isValidDate(gfs_forecast_at) && isValidDate(computed_at)) {
      titleGroup.append('text')
        .attr('class', 'subtitle')
        .attr('text-anchor', 'middle')
        .attr('dy', `${baseFontSize * 1.4}px`)
        .style('font-size', `${baseFontSize * 0.8}px`)
        .style('fill', '#666')
        .text(`GFS: ${formatDateTime(gfs_forecast_at)} | Processed: ${formatDateTime(computed_at)}`);
    }

    // --- Hover ---
    const hoverLine = svg.append('line')
      .attr('stroke', '#666')
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '5,5')
      .style('visibility', 'hidden');

    // Tooltip data: isobaric levels + surface level at the end
    const tooltipHeights = [...filteredHeights, sfcHeight];
    const tooltipTemp = [...filteredTemp, temp2m];
    const tooltipDewpoint = [...filteredDewpoint, dewpoint2m];
    const tooltipWindSpeed = [...filteredWindSpeed, windSpeed10m];
    const tooltipWindDir = [...filteredWindDir, windDir10m];
    const tooltipRH = [...filteredRH, null];
    const tooltipPressure = [...filteredPressure, forecast.pressure_sfc_pa != null ? Math.round(forecast.pressure_sfc_pa / 100) : null];

    svg.append('rect')
      .attr('width', width)
      .attr('height', height)
      .attr('fill', 'none')
      .attr('pointer-events', 'all')
      .on('mousemove', function(event) {
        const [, mouseY] = d3.pointer(event);
        const hoveredHeight = yScale.invert(mouseY);

        let closestIdx = 0;
        let closestDist = Infinity;
        for (let i = 0; i < tooltipHeights.length; i++) {
          const dist = Math.abs(tooltipHeights[i] - hoveredHeight);
          if (dist < closestDist) {
            closestDist = dist;
            closestIdx = i;
          }
        }

        const h = tooltipHeights[closestIdx];
        hoverLine
          .style('visibility', 'visible')
          .attr('x1', 0).attr('x2', width)
          .attr('y1', yScale(h)).attr('y2', yScale(h));

        const heightVal = Math.round(h);
        const pressure = tooltipPressure[closestIdx];
        const temp = tooltipTemp[closestIdx]?.toFixed(1) ?? 'N/A';
        const dewpoint = tooltipDewpoint[closestIdx]?.toFixed(1) ?? 'N/A';
        const windSpeed = tooltipWindSpeed[closestIdx]?.toFixed(1) ?? 'N/A';
        const windDir = Math.round(tooltipWindDir[closestIdx] ?? 0);
        const rh = tooltipRH[closestIdx];
        const isSurface = closestIdx === tooltipHeights.length - 1;
        const label = isSurface ? 'Surface' : `${heightVal} m AMSL`;

        tooltip
          .style('visibility', 'visible')
          .html(`
            <div style="
              display: grid;
              grid-template-columns: auto auto;
              gap: 4px;
              white-space: nowrap;
            ">
              <span style="color: #666">Altitude:</span> <span>${label}</span>
              ${pressure != null ? `<span style="color: #666">Pressure:</span> <span>${pressure} hPa</span>` : ''}
              <span style="color: #666">Temp:</span> <span style="color: red">${temp}°C</span>
              <span style="color: #666">Dewpoint:</span> <span style="color: blue">${dewpoint}°C</span>
              <span style="color: #666">Wind:</span> <span style="color: green">${windSpeed} m/s @ ${windDir}°</span>
              ${rh != null ? `<span style="color: #666">RH:</span> <span>${Math.round(rh)}%</span>` : ''}
            </div>
          `);
        positionTooltip(event);
      })
      .on('mouseleave', function() {
        hoverLine.style('visibility', 'hidden');
        tooltip.style('visibility', 'hidden');
      });

    // --- Responsive font sizes ---
    svg.selectAll('text').style('font-size', `${baseFontSize}px`);
    svg.selectAll('.rh-group text').style('font-size', `${baseFontSize * 0.8}px`);
    svg.select('.main-title').style('font-size', `${baseFontSize * 1.2}px`);
  }, [forecast, selectedHour, date, gfs_forecast_at, computed_at]);

  useEffect(() => {
    createChart();
  }, [createChart]);

  useEffect(() => {
    const handleResize = debounce(() => {
      createChart();
    }, 250);
    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      handleResize.cancel();
    };
  }, [createChart]);

  return (
    <div
      ref={containerRef}
      style={{ width: '100%', height: '100%', position: 'relative' }}
    >
      <svg
        ref={svgRef}
        style={{ width: '100%', height: '100%', display: 'block' }}
      />
      <div
        ref={tooltipRef}
        style={{ position: 'absolute', pointerEvents: 'none' }}
      />
    </div>
  );
};

export default D3Forecast;
