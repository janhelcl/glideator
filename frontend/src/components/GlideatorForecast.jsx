import React, { useEffect, useRef, useCallback } from 'react';
import * as d3 from 'd3';
import { Box, useMediaQuery, useTheme } from '@mui/material';
import { debounce } from 'lodash';

const GlideatorForecast = ({ siteData, selectedDate, selectedMetric, metrics }) => {
  const barChartRef = useRef(null);
  const lineChartRef = useRef(null);
  const barContainerRef = useRef(null);
  const lineContainerRef = useRef(null);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  // Create the bar chart showing all metrics for the selected date
  const createBarChart = useCallback(() => {
    if (!siteData || !selectedDate || !barChartRef.current || !barContainerRef.current) return;

    // Clear previous chart
    d3.select(barChartRef.current).selectAll('*').remove();

    // Find prediction for selected date
    const prediction = siteData.predictions?.find(p => p.date === selectedDate);
    if (!prediction || !prediction.values) return;

    // Prepare data for the chart
    const data = metrics.map((metric, index) => ({
      metric,
      value: prediction.values[index] || 0
    }));

    // Get container dimensions
    const containerWidth = barContainerRef.current.clientWidth;
    const containerHeight = barContainerRef.current.clientHeight;

    // Set margins and dimensions
    const margin = { top: 30, right: 30, bottom: 60, left: 60 };
    const width = containerWidth - margin.left - margin.right;
    const height = containerHeight - margin.top - margin.bottom;

    // Create SVG
    const svg = d3.select(barChartRef.current)
      .attr('width', containerWidth)
      .attr('height', containerHeight)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Create scales
    const x = d3.scaleBand()
      .domain(data.map(d => d.metric))
      .range([0, width])
      .padding(0); // Remove padding between bars

    const y = d3.scaleLinear()
      .domain([0, 1])
      .range([height, 0]);

    // Create and add x-axis
    svg.append('g')
      .attr('transform', `translate(0,${height})`)
      .call(d3.axisBottom(x))
      .selectAll('text')
      .attr('transform', 'translate(-10,0)rotate(-45)')
      .style('text-anchor', 'end')
      .style('font-size', '12px')
      .text(d => d.replace('XC', '')); // Remove 'XC' prefix from axis labels

    // Create and add y-axis
    svg.append('g')
      .call(d3.axisLeft(y).ticks(5).tickFormat(d => `${d * 100}%`))
      .selectAll('text')
      .style('font-size', '12px');

    // Add y-axis label
    svg.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('y', -margin.left + 15)
      .attr('x', -height / 2)
      .attr('dy', '1em')
      .style('text-anchor', 'middle')
      .style('font-size', '14px')

    // Add x-axis label
    svg.append('text')
      .attr('transform', `translate(${width / 2}, ${height + margin.bottom - 10})`)
      .style('text-anchor', 'middle')
      .style('font-size', '14px')
      .text('Minimum Flight Quality (XC Points)');

    // Use a single color for all bars
    const barColor = '#4CAF50'; // Green color for all bars

    // Add bars
    svg.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', d => x(d.metric))
      .attr('width', x.bandwidth())
      .attr('y', d => y(d.value))
      .attr('height', d => height - y(d.value))
      .attr('fill', barColor) // Use the same color for all bars
      .attr('rx', 0) // Remove rounded corners
      .attr('ry', 0);

    // Add value labels on top of bars
    svg.selectAll('.label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'label')
      .attr('x', d => x(d.metric) + x.bandwidth() / 2)
      .attr('y', d => y(d.value) - 5)
      .attr('text-anchor', 'middle')
      .style('font-size', '12px')
      .style('font-weight', 'bold')
      .text(d => `${Math.round(d.value * 100)}%`);

    // Highlight the selected metric
    svg.selectAll('.bar')
      .filter(d => d.metric === selectedMetric)
      .attr('stroke', '#2196F3')
      .attr('stroke-width', 3);

    // Add title
    svg.append('text')
      .attr('x', width / 2)
      .attr('y', -10)
      .attr('text-anchor', 'middle')
      .style('font-size', '16px')
      .style('font-weight', 'bold')
      .text(`Will There Be a Flight on ${selectedDate}? How Far Might It Go?`);

  }, [siteData, selectedDate, selectedMetric, metrics]);

  // Create the line chart showing selected metric over time
  const createLineChart = useCallback(() => {
    if (!siteData || !selectedMetric || !lineChartRef.current || !lineContainerRef.current) return;

    // Clear previous chart
    d3.select(lineChartRef.current).selectAll('*').remove();

    // Get the index of the selected metric
    const metricIndex = metrics.indexOf(selectedMetric);
    if (metricIndex === -1) return;

    // Prepare data for the chart - all predictions for the selected metric
    const data = siteData.predictions
      ?.filter(p => p.values && p.values[metricIndex] !== undefined)
      .map(p => ({
        date: new Date(p.date),
        value: p.values[metricIndex]
      }))
      .sort((a, b) => a.date - b.date);

    if (!data || data.length === 0) return;

    // Get container dimensions
    const containerWidth = lineContainerRef.current.clientWidth;
    const containerHeight = lineContainerRef.current.clientHeight;

    // Set margins and dimensions
    const margin = { top: 30, right: 30, bottom: 60, left: 60 };
    const width = containerWidth - margin.left - margin.right;
    const height = containerHeight - margin.top - margin.bottom;

    // Create SVG
    const svg = d3.select(lineChartRef.current)
      .attr('width', containerWidth)
      .attr('height', containerHeight)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Create scales
    const x = d3.scaleTime()
      .domain(d3.extent(data, d => d.date))
      .range([0, width]);

    const y = d3.scaleLinear()
      .domain([0, 1])
      .range([height, 0]);

    // Create and add x-axis
    svg.append('g')
      .attr('transform', `translate(0,${height})`)
      .call(d3.axisBottom(x).ticks(Math.min(data.length, 7)).tickFormat(d3.timeFormat('%b %d')))
      .selectAll('text')
      .style('font-size', '12px');

    // Create and add y-axis
    svg.append('g')
      .call(d3.axisLeft(y).ticks(5).tickFormat(d => `${d * 100}%`))
      .selectAll('text')
      .style('font-size', '12px');

    // Add y-axis label
    svg.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('y', -margin.left + 15)
      .attr('x', -height / 2)
      .attr('dy', '1em')
      .style('text-anchor', 'middle')
      .style('font-size', '14px')
      .text('Probability');

    // Add x-axis label
    svg.append('text')
      .attr('transform', `translate(${width / 2}, ${height + margin.bottom - 10})`)
      .style('text-anchor', 'middle')
      .style('font-size', '14px')
      .text('Date');

    // Add grid lines
    svg.append('g')
      .attr('class', 'grid')
      .call(d3.axisLeft(y)
        .ticks(5)
        .tickSize(-width)
        .tickFormat('')
      )
      .attr('stroke-opacity', 0.1);

    // Create line generator
    const line = d3.line()
      .x(d => x(d.date))
      .y(d => y(d.value))
      .curve(d3.curveMonotoneX);

    // Add the line path
    svg.append('path')
      .datum(data)
      .attr('fill', 'none')
      .attr('stroke', '#2196F3')
      .attr('stroke-width', 3)
      .attr('d', line);

    // Add dots for each data point
    svg.selectAll('.dot')
      .data(data)
      .enter()
      .append('circle')
      .attr('class', 'dot')
      .attr('cx', d => x(d.date))
      .attr('cy', d => y(d.value))
      .attr('r', 5)
      .attr('fill', '#2196F3')
      .attr('stroke', 'white')
      .attr('stroke-width', 2);

    // Add value labels above dots
    svg.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', d => x(d.date))
      .attr('y', d => y(d.value) - 10)
      .attr('text-anchor', 'middle')
      .style('font-size', '12px')
      .style('font-weight', 'bold')
      .text(d => `${Math.round(d.value * 100)}%`);

    // Highlight the selected date
    const selectedDateObj = new Date(selectedDate);
    const closestPoint = data.reduce((prev, curr) => {
      const prevDiff = Math.abs(prev.date - selectedDateObj);
      const currDiff = Math.abs(curr.date - selectedDateObj);
      return currDiff < prevDiff ? curr : prev;
    }, data[0]);

    svg.selectAll('.dot')
      .filter(d => d.date.getTime() === closestPoint.date.getTime())
      .attr('r', 8)
      .attr('fill', '#FFC107')
      .attr('stroke', '#FF5722')
      .attr('stroke-width', 2);

    // Add title
    svg.append('text')
      .attr('x', width / 2)
      .attr('y', -10)
      .attr('text-anchor', 'middle')
      .style('font-size', '16px')
      .style('font-weight', 'bold')
      .text(selectedMetric === 'XC0' 
        ? 'Chances of a Flight'
        : `Chances of a ${selectedMetric.replace('XC', '')} Point Flight`);

    // Add tooltip
    const tooltip = d3.select(lineContainerRef.current)
      .append('div')
      .attr('class', 'd3-tooltip')
      .style('position', 'absolute')
      .style('visibility', 'hidden')
      .style('background-color', 'rgba(255, 255, 255, 0.9)')
      .style('border', '1px solid #ddd')
      .style('border-radius', '4px')
      .style('padding', '8px')
      .style('box-shadow', '0 2px 4px rgba(0,0,0,0.1)')
      .style('pointer-events', 'none')
      .style('font-size', '12px');

    // Add hover interaction
    svg.selectAll('.dot')
      .on('mouseover', function(event, d) {
        d3.select(this)
          .attr('r', 8)
          .attr('stroke-width', 3);
        
        tooltip
          .style('visibility', 'visible')
          .html(`
            <strong>Date:</strong> ${d.date.toLocaleDateString()}<br>
            <strong>${selectedMetric}:</strong> ${Math.round(d.value * 100)}%
          `);
      })
      .on('mousemove', function(event) {
        tooltip
          .style('top', (event.pageY - 10) + 'px')
          .style('left', (event.pageX + 10) + 'px');
      })
      .on('mouseout', function() {
        d3.select(this)
          .attr('r', d => {
            const isSelected = d.date.getTime() === closestPoint.date.getTime();
            return isSelected ? 8 : 5;
          })
          .attr('stroke-width', d => {
            const isSelected = d.date.getTime() === closestPoint.date.getTime();
            return isSelected ? 2 : 2;
          });
        
        tooltip.style('visibility', 'hidden');
      });

  }, [siteData, selectedDate, selectedMetric, metrics]);

  // Create charts on initial render and when dependencies change
  useEffect(() => {
    createBarChart();
    createLineChart();
  }, [createBarChart, createLineChart]);

  // Handle window resize
  useEffect(() => {
    const handleResize = debounce(() => {
      createBarChart();
      createLineChart();
    }, 300);

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      handleResize.cancel();
    };
  }, [createBarChart, createLineChart]);

  return (
    <Box sx={{ width: '100%' }}>
      <Box sx={{ 
        display: 'flex', 
        flexDirection: isMobile ? 'column' : 'row',
        gap: 3,
        width: '100%'
      }}>
        {/* Bar Chart */}
        <Box 
          ref={barContainerRef}
          sx={{ 
            flex: 1, 
            height: isMobile ? '300px' : '400px',
            position: 'relative',
            minWidth: 0 // Prevents flex items from overflowing
          }}
        >
          <svg 
            ref={barChartRef}
            style={{ 
              width: '100%', 
              height: '100%',
              overflow: 'visible'
            }}
          />
        </Box>

        {/* Line Chart */}
        <Box 
          ref={lineContainerRef}
          sx={{ 
            flex: 1, 
            height: isMobile ? '300px' : '400px',
            position: 'relative',
            minWidth: 0 // Prevents flex items from overflowing
          }}
        >
          <svg 
            ref={lineChartRef}
            style={{ 
              width: '100%', 
              height: '100%',
              overflow: 'visible'
            }}
          />
        </Box>
      </Box>
    </Box>
  );
};

export default GlideatorForecast; 