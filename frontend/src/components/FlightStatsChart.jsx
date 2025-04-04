import React, { useEffect, useRef, useCallback } from 'react';
import * as d3 from 'd3';
import { debounce } from 'lodash';
import { Box, Typography } from '@mui/material';
import StandaloneMetricControl from './StandaloneMetricControl';

const FlightStatsChart = ({ data, metrics, selectedMetric, onMetricChange }) => {
  const svgRef = useRef(null);
  const containerRef = useRef(null);

  // Transform the data for D3
  const prepareData = useCallback(() => {
    if (!data) return [];

    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    
    // Create an array of objects, each for a month - but only for the selected metric
    const transformedData = months.map((month, i) => {
      const monthData = { month };
      
      // Add data only for the selected metric
      const metricKey = selectedMetric.replace('XC', '');
      if (data[metricKey] && data[metricKey][i] !== undefined) {
        monthData[selectedMetric] = data[metricKey][i];
      } else {
        monthData[selectedMetric] = 0;
      }
      
      return monthData;
    });
    
    return transformedData;
  }, [data, selectedMetric]);

  const createChart = useCallback(() => {
    if (!data || !svgRef.current || !containerRef.current) return;

    // Clear previous chart
    d3.select(svgRef.current).selectAll('*').remove();
    d3.select(containerRef.current).selectAll('.d3-tooltip').remove();

    const transformedData = prepareData();
    if (transformedData.length === 0) return;

    // Get container dimensions
    const containerWidth = containerRef.current.clientWidth;
    const containerHeight = containerRef.current.clientHeight;

    // Calculate responsive font sizes
    const baseFontSize = Math.max(8, Math.min(12, containerWidth / 60));
    const titleFontSize = Math.max(12, Math.min(16, containerWidth / 40));

    // Set chart dimensions - reduce left margin since we don't need y-axis
    const margin = {
      top: 40 + titleFontSize,
      right: 30,
      bottom: 60 + baseFontSize,
      left: 20 // Reduced significantly as we don't need y-axis
    };
    
    const width = containerWidth - margin.left - margin.right;
    const height = containerHeight - margin.top - margin.bottom;

    // Create SVG element
    const svg = d3.select(svgRef.current)
      .attr('width', containerWidth)
      .attr('height', containerHeight)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Create scales - tight padding for the bars
    const xScale = d3.scaleBand()
      .domain(transformedData.map(d => d.month))
      .range([0, width])
      .padding(0.02); // Very small padding for tight bars

    // Set a fixed y-scale to 30 days
    const yScale = d3.scaleLinear()
      .domain([0, 30]) // Fixed to 30 days maximum
      .range([height, 0]);

    // Create and add only x-axis
    const xAxis = d3.axisBottom(xScale);

    // Add x axis
    svg.append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(0,${height})`)
      .call(xAxis)
      .selectAll('text')
      .style('font-size', `${baseFontSize}px`);

    // Add chart title
    const pointsLabel = selectedMetric === 'XC0' ? 'Any Flight' : `${selectedMetric.replace('XC', '')}+ Point Flights`;
    svg.append('text')
      .attr('x', width / 2)
      .attr('y', -margin.top + titleFontSize)
      .attr('text-anchor', 'middle')
      .style('font-size', `${titleFontSize}px`)
      .style('font-weight', 'bold')
      .text(`Days with ${pointsLabel}`);

    // Define the color for the bars
    const barColor = '#2196F3'; // Blue color

    // Create bars - without interactive elements
    svg.selectAll('.bar')
      .data(transformedData)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', d => xScale(d.month))
      .attr('width', xScale.bandwidth())
      .attr('y', d => yScale(d[selectedMetric] || 0))
      .attr('height', d => height - yScale(d[selectedMetric] || 0))
      .attr('fill', barColor)
      .attr('opacity', 0.8);

    // Add value labels on top of bars
    svg.selectAll('.value-label')
      .data(transformedData)
      .enter()
      .append('text')
      .attr('class', 'value-label')
      .attr('x', d => xScale(d.month) + xScale.bandwidth() / 2)
      .attr('y', d => {
        const value = d[selectedMetric] || 0;
        return yScale(value) - 5;
      })
      .attr('text-anchor', 'middle')
      .style('font-size', `${baseFontSize}px`)
      .style('font-weight', 'bold')
      .text(d => (d[selectedMetric] || 0).toFixed(1));

  }, [data, selectedMetric, prepareData]);

  // Initial render
  useEffect(() => {
    createChart();
  }, [createChart]);

  // Handle resize
  useEffect(() => {
    const handleResize = debounce(() => {
      createChart();
    }, 300);

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
      handleResize.cancel();
    };
  }, [createChart]);

  if (!data) {
    return (
      <Box sx={{ textAlign: 'center', py: 2 }}>
        <Typography variant="body1">No flight statistics available</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ 
      position: 'relative', 
      width: '100%',
      display: 'flex',
      justifyContent: 'center' // Center the chart in the container
    }}>
      {/* Metric control positioned in the top-right corner */}
      <Box sx={{ 
        position: 'absolute', 
        top: '2px', // Move closer to the top
        right: '2px', // Move closer to the right
        zIndex: 10 
      }}>
        <StandaloneMetricControl
          metrics={metrics}
          selectedMetric={selectedMetric}
          onMetricChange={onMetricChange}
        />
      </Box>
      
      <Box 
        ref={containerRef}
        sx={{ 
          width: '100%', 
          maxWidth: '750px', // Reduced from 900px to 750px
          height: '350px',
          maxHeight: 'calc(100vh - 400px)',
          position: 'relative'
        }}
      >
        <svg 
          ref={svgRef}
          style={{
            width: '100%',
            height: '100%'
          }}
        />
      </Box>
    </Box>
  );
};

export default FlightStatsChart; 