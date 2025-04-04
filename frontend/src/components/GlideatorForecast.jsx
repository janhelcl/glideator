import React, { useEffect, useRef, useCallback } from 'react';
import * as d3 from 'd3';
import { Box, useMediaQuery, useTheme } from '@mui/material';
import { debounce } from 'lodash';
import StandaloneMetricControl from './StandaloneMetricControl';
import DateBoxesControl from './DateBoxesControl';

const GlideatorForecast = ({ 
  siteData, 
  selectedDate, 
  selectedMetric, 
  metrics, 
  onMetricChange,
  onDateChange,
  allDates,
  mapState,
  allSites
}) => {
  const barChartRef = useRef(null);
  const lineChartRef = useRef(null);
  const barContainerRef = useRef(null);
  const lineContainerRef = useRef(null);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  // Create the bar chart showing all metrics for the selected date
  const createBarChart = useCallback(() => {
    if (!siteData || !selectedDate || !barChartRef.current || !barContainerRef.current) return;

    // Clear previous chart more thoroughly
    const svgElement = d3.select(barChartRef.current);
    svgElement.selectAll('*').remove();

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

    // Calculate responsive font sizes based on container dimensions
    // More aggressive scaling for small screens
    const axisFontSize = Math.max(8, Math.min(12, containerWidth / 60));
    const labelFontSize = Math.max(8, Math.min(12, containerWidth / 60));
    const titleFontSize = Math.max(10, Math.min(16, containerWidth / 45));
    
    // Set margins and dimensions - adjust based on font sizes
    const margin = { 
      top: 20 + titleFontSize * 2, 
      right: 20, 
      bottom: 50 + axisFontSize, 
      left: 50 + axisFontSize 
    };
    
    // For very small screens, reduce margins further
    if (containerWidth < 400) {
      margin.left = 40 + axisFontSize;
      margin.right = 15;
      margin.bottom = 40 + axisFontSize;
    }
    
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

    // Create and add x-axis with responsive font size
    svg.append('g')
      .attr('transform', `translate(0,${height})`)
      .call(d3.axisBottom(x))
      .selectAll('text')
      .attr('transform', 'translate(-10,0)rotate(-45)')
      .style('text-anchor', 'end')
      .style('font-size', `${axisFontSize}px`)
      .text(d => d.replace('XC', '')); // Remove 'XC' prefix from axis labels

    // For the bar chart - remove y-axis
    svg.append('g')
      .call(d3.axisLeft(y).tickSize(0).tickFormat(''))
      .selectAll('path, line')
      .style('stroke', 'transparent');

    // Add x-axis label with responsive font size
    svg.append('text')
      .attr('transform', `translate(${width / 2}, ${height + margin.bottom - 10})`)
      .style('text-anchor', 'middle')
      .style('font-size', `${axisFontSize + 2}px`)
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

    // Add value labels on top of bars with responsive font size
    svg.selectAll('.label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'label')
      .attr('x', d => x(d.metric) + x.bandwidth() / 2)
      .attr('y', d => y(d.value) - 5)
      .attr('text-anchor', 'middle')
      .style('font-size', `${labelFontSize}px`)
      .style('font-weight', 'bold')
      .text(d => `${Math.round(d.value * 100)}%`);

    // Highlight the selected metric
    svg.selectAll('.bar')
      .filter(d => d.metric === selectedMetric)
      .attr('stroke', '#2196F3')
      .attr('stroke-width', 3);

    // Bar Chart Title - with adjusted positioning and responsive font size
    const titleLine1 = `Will There Be a Flight on ${selectedDate}?`;
    const titleLine2 = 'How Far Might It Go?';
    
    svg.append('text')
      .attr('x', width / 2)
      .attr('y', -margin.top + titleFontSize)
      .attr('text-anchor', 'middle')
      .style('font-size', `${titleFontSize}px`)
      .style('font-weight', 'bold')
      .text(titleLine1);

    svg.append('text')
      .attr('x', width / 2)
      .attr('y', -margin.top + titleFontSize * 2.5)
      .attr('text-anchor', 'middle')
      .style('font-size', `${titleFontSize}px`)
      .style('font-weight', 'bold')
      .text(titleLine2);

  }, [siteData, selectedDate, selectedMetric, metrics]);

  // Create the line chart showing selected metric over time
  const createLineChart = useCallback(() => {
    if (!siteData || !selectedMetric || !lineChartRef.current || !lineContainerRef.current) return;

    // Clear previous chart more thoroughly
    const svgElement = d3.select(lineChartRef.current);
    svgElement.selectAll('*').remove();
    
    // Remove any tooltips that might have been appended to the container
    d3.select(lineContainerRef.current).selectAll('.d3-tooltip').remove();

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

    // Calculate responsive font sizes based on container dimensions
    // More aggressive scaling for small screens
    const axisFontSize = Math.max(8, Math.min(12, containerWidth / 60));
    const labelFontSize = Math.max(8, Math.min(12, containerWidth / 60));
    const titleFontSize = Math.max(10, Math.min(16, containerWidth / 45));
    
    // Set margins and dimensions - adjust based on font sizes
    const margin = { 
      top: 20 + titleFontSize * 2, 
      right: 20, 
      bottom: 50 + axisFontSize, 
      left: 50 + axisFontSize 
    };
    
    // For very small screens, reduce margins further
    if (containerWidth < 400) {
      margin.left = 40 + axisFontSize;
      margin.right = 15;
      margin.bottom = 40 + axisFontSize;
    }
    
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

    // Create and add x-axis with responsive font size and ensure all dates are visible
    svg.append('g')
      .attr('transform', `translate(0,${height})`)
      .call(d3.axisBottom(x)
        // Use all data points as ticks to ensure all dates are shown
        .tickValues(data.map(d => d.date))
        .tickFormat((d, i) => {
          // Format dates based on available space
          if (containerWidth < 400) {
            // For very small screens, use day number only but show all dates
            return d3.timeFormat('%d')(d);
          } else if (isMobile) {
            // For mobile, show day number only
            return d3.timeFormat('%d')(d);
          } else {
            // For larger screens, show month and day
            return d3.timeFormat('%b %d')(d);
          }
        }))
      .selectAll('text')
      .style('font-size', `${axisFontSize}px`)
      .attr('transform', containerWidth < 500 ? 'translate(-5,2)rotate(-45)' : 'translate(0,0)')
      .style('text-anchor', containerWidth < 500 ? 'end' : 'middle');

    // For the line chart - remove y-axis
    svg.append('g')
      .call(d3.axisLeft(y).tickSize(0).tickFormat(''))
      .selectAll('path, line')
      .style('stroke', 'transparent');

    // Add x-axis label with responsive font size
    svg.append('text')
      .attr('transform', `translate(${width / 2}, ${height + margin.bottom - 10})`)
      .style('text-anchor', 'middle')
      .style('font-size', `${axisFontSize + 2}px`)
      .text('Date');

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

    // Calculate dot size based on chart dimensions - smaller for small screens
    const dotRadius = Math.max(2, Math.min(4, width / 120));
    const selectedDotRadius = dotRadius * 1.6;

    // Add dots for each data point with responsive size
    svg.selectAll('.dot')
      .data(data)
      .enter()
      .append('circle')
      .attr('class', 'dot')
      .attr('cx', d => x(d.date))
      .attr('cy', d => y(d.value))
      .attr('r', dotRadius)
      .attr('fill', '#2196F3')
      .attr('stroke', 'white')
      .attr('stroke-width', 2);

    // Highlight the selected date
    const selectedDateObj = new Date(selectedDate);
    const closestPoint = data.reduce((prev, curr) => {
      const prevDiff = Math.abs(prev.date - selectedDateObj);
      const currDiff = Math.abs(curr.date - selectedDateObj);
      return currDiff < prevDiff ? curr : prev;
    }, data[0]);

    // Add value labels above dots with responsive font size
    svg.selectAll('.value-label')
      .data(data)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', d => x(d.date))
      .attr('y', d => y(d.value) - dotRadius - 5)
      .attr('text-anchor', 'middle')
      .style('font-size', `${labelFontSize}px`)
      .style('font-weight', 'bold')
      .text(d => `${Math.round(d.value * 100)}%`);

    svg.selectAll('.dot')
      .filter(d => d.date.getTime() === closestPoint.date.getTime())
      .attr('r', selectedDotRadius)
      .attr('fill', '#FFC107')
      .attr('stroke', '#FF5722')
      .attr('stroke-width', 2);

    // Line Chart Title with responsive font size
    svg.append('text')
      .attr('x', width / 2)
      .attr('y', -margin.top + titleFontSize)
      .attr('text-anchor', 'middle')
      .style('font-size', `${titleFontSize}px`)
      .style('font-weight', 'bold')
      .text(selectedMetric === 'XC0' 
        ? 'Chances of a Flight'
        : `Chances of a ${selectedMetric.replace('XC', '')}+ Point Flight`);

    // Add tooltip with responsive styling
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
      .style('font-size', `${labelFontSize}px`);

    // Add hover interaction with responsive dot sizing
    svg.selectAll('.dot')
      .on('mouseover', function(event, d) {
        d3.select(this)
          .attr('r', selectedDotRadius)
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
      .on('mouseout', function(d) {
        const isSelected = d3.select(this).datum().date.getTime() === closestPoint.date.getTime();
        d3.select(this)
          .attr('r', isSelected ? selectedDotRadius : dotRadius)
          .attr('stroke-width', 2);
        
        tooltip.style('visibility', 'hidden');
      });

  }, [siteData, selectedDate, selectedMetric, metrics, isMobile]);

  // Create charts on initial render and when dependencies change
  useEffect(() => {
    if (barChartRef.current && lineChartRef.current) {
      // Reset SVG content completely
      d3.select(barChartRef.current).selectAll('*').remove();
      d3.select(lineChartRef.current).selectAll('*').remove();
      
      // Also remove any tooltips or other elements added outside the SVG
      if (barContainerRef.current) {
        d3.select(barContainerRef.current).selectAll('.d3-tooltip').remove();
      }
      if (lineContainerRef.current) {
        d3.select(lineContainerRef.current).selectAll('.d3-tooltip').remove();
      }
      
      // Then create the charts
      createBarChart();
      createLineChart();
    }
  }, [createBarChart, createLineChart]);

  // Handle window resize with more thorough cleanup
  useEffect(() => {
    const handleResize = debounce(() => {
      // Ensure we clear everything before redrawing
      if (barChartRef.current) d3.select(barChartRef.current).selectAll('*').remove();
      if (lineChartRef.current) d3.select(lineChartRef.current).selectAll('*').remove();
      if (barContainerRef.current) d3.select(barContainerRef.current).selectAll('.d3-tooltip').remove();
      if (lineContainerRef.current) d3.select(lineContainerRef.current).selectAll('.d3-tooltip').remove();
      
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
        {/* Bar Chart with Date Control */}
        <Box 
          ref={barContainerRef}
          sx={{ 
            flex: 1, 
            height: isMobile ? '280px' : '400px',
            position: 'relative',
            minWidth: 0,
            overflow: 'visible',
            marginTop: '30px'
          }}
        >
          {/* Date control positioned above the chart */}
          <Box sx={{ 
            position: 'absolute', 
            top: '-30px',
            right: '10px'
          }}>
            {allDates && allDates.length > 0 && (
              <DateBoxesControl
                dates={allDates}
                selectedDate={selectedDate}
                setSelectedDate={onDateChange}
                center={mapState?.center}
                zoom={mapState?.zoom}
                bounds={mapState?.bounds}
                allSites={allSites || [siteData]}
                selectedMetric={selectedMetric}
                metrics={metrics}
              />
            )}
          </Box>
          
          <svg 
            ref={barChartRef}
            style={{ 
              width: '100%', 
              height: '100%',
              overflow: 'visible',
              display: 'block'
            }}
          />
        </Box>

        {/* Line Chart with Metric Control */}
        <Box 
          ref={lineContainerRef}
          sx={{ 
            flex: 1, 
            height: isMobile ? '280px' : '400px',
            position: 'relative',
            minWidth: 0,
            overflow: 'visible',
            marginTop: '30px'
          }}
        >
          {/* Metric control positioned above the chart */}
          <Box sx={{ 
            position: 'absolute', 
            top: '-30px',
            right: '10px'
          }}>
            <StandaloneMetricControl
              metrics={metrics}
              selectedMetric={selectedMetric}
              onMetricChange={onMetricChange}
            />
          </Box>
          
          <svg 
            ref={lineChartRef}
            style={{ 
              width: '100%', 
              height: '100%',
              overflow: 'visible',
              display: 'block'
            }}
          />
        </Box>
      </Box>
    </Box>
  );
};

export default GlideatorForecast; 