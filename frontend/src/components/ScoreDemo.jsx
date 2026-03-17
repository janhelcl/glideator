import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Box, ToggleButtonGroup, ToggleButton, Typography, useTheme, useMediaQuery } from '@mui/material';
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import * as d3 from 'd3';
import { getColor } from '../utils/colorUtils';
import StandaloneMetricControl from './StandaloneMetricControl';
import './MapView.css';

const METRICS = ['XC0', 'XC10', 'XC20', 'XC30', 'XC40', 'XC50', 'XC60', 'XC70', 'XC80', 'XC90', 'XC100'];

const SCENARIOS = {
  terrible: {
    label: 'Terrible Day',
    values: [0.08, 0.04, 0.02, 0.01, 0.01, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
    comment: 'Almost no chance of anyone flying. Red dot, flat bars — today is for hiking.',
  },
  average: {
    label: 'Average Day',
    values: [0.92, 0.75, 0.55, 0.35, 0.20, 0.10, 0.05, 0.02, 0.01, 0.00, 0.00],
    comment: 'High chance someone gets airborne, but long XC flights are unlikely. Good for local soaring.',
  },
  epic: {
    label: 'Epic Day',
    values: [0.99, 0.97, 0.95, 0.92, 0.88, 0.82, 0.75, 0.69, 0.62, 0.53, 0.44],
    comment: 'Strong probabilities across the board. Even 100+ point XC flights are plausible. Call in sick.',
  },
};

const BASSANO = [45.7658, 11.7341];

function rgbToRgba(rgb, alpha) {
  const [r, g, b] = rgb.match(/\d+/g);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function createGlowingIcon(color) {
  const rgbaGlow = rgbToRgba(color, 0.7);
  const rgbaGlowHover = rgbToRgba(color, 1);
  const uniqueId = `demo-marker-${Math.random().toString(36).substr(2, 9)}`;

  return L.divIcon({
    className: '',
    html: `
      <style>
        #${uniqueId} {
          --marker-color: ${color};
          --marker-glow-color: ${rgbaGlow};
          --marker-glow-hover-color: ${rgbaGlowHover};
        }
      </style>
      <div class="glowing-marker" id="${uniqueId}">
        <div class="glow"></div>
        <div class="point"></div>
      </div>
    `,
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });
}

const DemoMarker = ({ probability }) => {
  const markerRef = useRef(null);
  const color = getColor(probability);
  const pct = `${Math.round(probability * 100)}%`;

  useEffect(() => {
    if (markerRef.current) {
      markerRef.current.setIcon(createGlowingIcon(color));
      markerRef.current.openPopup();
    }
  }, [color]);

  return (
    <Marker
      ref={markerRef}
      position={BASSANO}
      icon={createGlowingIcon(color)}
    >
      <Popup closeButton={false} closeOnClick={false} autoClose={false} className="custom-popup">
        <div className="popup-content">
          <div className="popup-header">
            <h3>Bassano</h3>
          </div>
          <div className="popup-metric-bar">
            <span
              className="popup-metric-value"
              style={{ backgroundColor: color }}
            >
              {pct}
            </span>
          </div>
          <div className="popup-footer">
            <button
              className="popup-details-button"
              onClick={(e) => e.preventDefault()}
            >
              View Details
            </button>
          </div>
        </div>
      </Popup>
    </Marker>
  );
};

const DemoBarChart = ({ values, selectedMetric }) => {
  const svgRef = useRef(null);
  const containerRef = useRef(null);

  const draw = useCallback(() => {
    if (!svgRef.current || !containerRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const containerWidth = containerRef.current.clientWidth;
    const containerHeight = containerRef.current.clientHeight;

    const axisFontSize = Math.max(7, Math.min(11, containerWidth / 55));
    const labelFontSize = Math.max(7, Math.min(11, containerWidth / 55));
    const titleFontSize = Math.max(9, Math.min(14, containerWidth / 40));

    const margin = {
      top: 14 + titleFontSize * 2.5,
      right: 12,
      bottom: 38 + axisFontSize,
      left: 8,
    };

    if (containerWidth < 400) {
      margin.bottom = 32 + axisFontSize;
    }

    const width = containerWidth - margin.left - margin.right;
    const height = containerHeight - margin.top - margin.bottom;

    const data = METRICS.map((metric, i) => ({ metric, value: values[i] || 0 }));

    const g = svg
      .attr('width', containerWidth)
      .attr('height', containerHeight)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    const x = d3.scaleBand().domain(data.map(d => d.metric)).range([0, width]).padding(0);
    const y = d3.scaleLinear().domain([0, 1]).range([height, 0]);

    const xAxis = g.append('g')
      .attr('transform', `translate(0,${height})`)
      .call(d3.axisBottom(x).tickSizeOuter(0));

    xAxis.selectAll('.tick line').attr('transform', `translate(${-x.bandwidth() / 2},0)`);
    xAxis.selectAll('text')
      .attr('transform', `translate(${-x.bandwidth() / 2},0)rotate(-45)`)
      .style('text-anchor', 'end')
      .style('font-size', `${axisFontSize}px`)
      .text(d => d.replace('XC', ''));

    xAxis.selectAll('.tick').each(function () {
      const t = d3.select(this).select('text').node();
      if (!t || !t.textContent.trim()) d3.select(this).remove();
    });

    g.append('g')
      .call(d3.axisLeft(y).tickSize(0).tickFormat(''))
      .selectAll('path, line').style('stroke', 'transparent');

    g.append('text')
      .attr('transform', `translate(${width / 2}, ${height + margin.bottom - 6})`)
      .style('text-anchor', 'middle')
      .style('font-size', `${axisFontSize + 1}px`)
      .text('Flight Quality (XC Points)');

    const barColor = '#4CAF50';

    g.selectAll('.bar')
      .data(data)
      .enter()
      .append('rect')
      .attr('class', 'bar')
      .attr('x', d => x(d.metric))
      .attr('width', x.bandwidth())
      .attr('y', d => y(d.value))
      .attr('height', d => height - y(d.value))
      .attr('fill', barColor)
      .attr('rx', 0)
      .attr('ry', 0);

    g.selectAll('.bar')
      .filter(d => d.metric === selectedMetric)
      .attr('stroke', '#2196F3')
      .attr('stroke-width', 3);

    g.selectAll('.label')
      .data(data)
      .enter()
      .append('text')
      .attr('x', d => x(d.metric) + x.bandwidth() / 2)
      .attr('y', d => y(d.value) - 4)
      .attr('text-anchor', 'middle')
      .style('font-size', `${labelFontSize}px`)
      .style('font-weight', 'bold')
      .text(d => `${Math.round(d.value * 100)}%`);

    g.append('text')
      .attr('x', width / 2)
      .attr('y', -margin.top + titleFontSize + 2)
      .attr('text-anchor', 'middle')
      .style('font-size', `${titleFontSize}px`)
      .style('font-weight', 'bold')
      .text('Will There Be a Flight?');

    g.append('text')
      .attr('x', width / 2)
      .attr('y', -margin.top + titleFontSize * 2.2 + 2)
      .attr('text-anchor', 'middle')
      .style('font-size', `${titleFontSize}px`)
      .style('font-weight', 'bold')
      .text('How Far Might It Go?');
  }, [values, selectedMetric]);

  useEffect(() => { draw(); }, [draw]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => draw());
    ro.observe(el);
    return () => ro.disconnect();
  }, [draw]);

  return (
    <Box ref={containerRef} sx={{ width: '100%', height: '100%', minHeight: 200 }}>
      <svg ref={svgRef} style={{ display: 'block', width: '100%', height: '100%', overflow: 'visible', colorScheme: 'light' }} />
    </Box>
  );
};

const ScoreDemo = () => {
  const theme = useTheme();
  const isSmall = useMediaQuery(theme.breakpoints.down('sm'));
  const [scenario, setScenario] = useState('average');
  const [selectedMetric, setSelectedMetric] = useState('XC0');

  const sc = SCENARIOS[scenario];
  const metricIndex = METRICS.indexOf(selectedMetric);
  const probability = sc.values[metricIndex];

  const handleMetricChange = useCallback((metric) => {
    setSelectedMetric(metric);
  }, []);

  return (
    <Box>
      {/* Scenario toggle */}
      <ToggleButtonGroup
        value={scenario}
        exclusive
        onChange={(_, v) => { if (v) setScenario(v); }}
        size="small"
        sx={{
          display: 'flex',
          mb: 2,
          '& .MuiToggleButton-root': {
            flex: 1,
            textTransform: 'none',
            fontWeight: 'bold',
            fontSize: { xs: '0.75rem', sm: '0.85rem' },
            py: 0.75,
          },
        }}
      >
        <ToggleButton value="terrible">Terrible Day</ToggleButton>
        <ToggleButton value="average">Average Day</ToggleButton>
        <ToggleButton value="epic">Epic Day</ToggleButton>
      </ToggleButtonGroup>

      {/* Comment */}
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2, fontStyle: 'italic' }}>
        {sc.comment}
      </Typography>

      {/* Map + Chart side by side */}
      <Box sx={{ position: 'relative', mb: 1 }}>
        <Box sx={{
          display: 'flex',
          flexDirection: { xs: 'column', sm: 'row' },
          gap: 2,
        }}>
          {/* Map panel */}
          <Box sx={{
            flex: { xs: 'none', sm: 1 },
            height: { xs: 220, sm: 280 },
            borderRadius: 2,
            overflow: 'hidden',
            border: 1,
            borderColor: 'divider',
            position: 'relative',
          }}>
            <MapContainer
              center={BASSANO}
              zoom={11}
              style={{ width: '100%', height: '100%' }}
              dragging={false}
              zoomControl={false}
              scrollWheelZoom={false}
              doubleClickZoom={false}
              touchZoom={false}
              attributionControl={false}
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
            <DemoMarker probability={probability} />
          </MapContainer>
        </Box>

          {/* Chart panel */}
          <Box sx={{
            flex: { xs: 'none', sm: 1 },
            height: { xs: 240, sm: 280 },
            borderRadius: 2,
            overflow: 'visible',
            border: 1,
            borderColor: 'divider',
          }}>
            <DemoBarChart values={sc.values} selectedMetric={selectedMetric} />
          </Box>
        </Box>

        {/* Metric control sits outside overflow:hidden panels so overlay renders cleanly */}
        <Box sx={{ position: 'absolute', top: 8, right: 8, zIndex: 1100 }}>
          <StandaloneMetricControl
            metrics={METRICS}
            selectedMetric={selectedMetric}
            onMetricChange={handleMetricChange}
          />
        </Box>
      </Box>

      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', textAlign: 'center' }}>
        Use the <strong>slider button</strong> on the chart to change the flight quality threshold
        and watch the map dot change color.
      </Typography>
    </Box>
  );
};

export default ScoreDemo;
