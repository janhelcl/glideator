import React from 'react';
import { getColor } from '../utils/colorUtils';

const Sparkline = ({ dailyProbabilities, maxDots = 5 }) => {
  if (!dailyProbabilities || dailyProbabilities.length === 0) {
    return (
      <div style={{ display: 'flex', gap: '2px', alignItems: 'center' }}>
        {[...Array(maxDots)].map((_, i) => (
          <div
            key={i}
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              backgroundColor: '#ccc',
            }}
          />
        ))}
      </div>
    );
  }

  // Take up to maxDots evenly spaced samples from the data
  const step = Math.max(1, Math.floor(dailyProbabilities.length / maxDots));
  const sampledData = [];
  for (let i = 0; i < Math.min(maxDots, dailyProbabilities.length); i++) {
    const index = Math.min(i * step, dailyProbabilities.length - 1);
    sampledData.push(dailyProbabilities[index]);
  }

  return (
    <div 
      style={{ 
        display: 'flex', 
        gap: '2px', 
        alignItems: 'center',
        minWidth: `${maxDots * 8}px` // Ensure consistent width
      }}
      title={`${dailyProbabilities.length} days of data`}
    >
      {sampledData.map((day, index) => (
        <div
          key={index}
          style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            backgroundColor: getColor(day.probability),
            border: '1px solid rgba(0,0,0,0.1)',
          }}
          title={`${day.date}: ${Math.round(day.probability * 100)}%`}
        />
      ))}
      {/* Fill remaining dots if we have fewer than maxDots */}
      {sampledData.length < maxDots && [...Array(maxDots - sampledData.length)].map((_, i) => (
        <div
          key={`empty-${i}`}
          style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            backgroundColor: '#eee',
          }}
        />
      ))}
    </div>
  );
};

export default Sparkline; 