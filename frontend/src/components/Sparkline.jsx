import React from 'react';
import { getColor } from '../utils/colorUtils';

const Sparkline = ({ dailyProbabilities, maxDots = 7 }) => {
  if (!dailyProbabilities || dailyProbabilities.length === 0) {
    return (
      <div style={{ 
        display: 'flex', 
        gap: '2px', 
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '8px',
        padding: '2px 0'
      }}>
        <div
          style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            backgroundColor: '#ccc',
            flexShrink: 0
          }}
        />
      </div>
    );
  }

  // Take up to maxDots from the data, use actual length if less than maxDots
  const actualDots = Math.min(maxDots, dailyProbabilities.length);
  const step = dailyProbabilities.length > maxDots ? 
    Math.floor(dailyProbabilities.length / maxDots) : 1;
  
  const sampledData = [];
  for (let i = 0; i < actualDots; i++) {
    const index = Math.min(i * step, dailyProbabilities.length - 1);
    sampledData.push(dailyProbabilities[index]);
  }

  return (
    <div 
      style={{ 
        display: 'flex', 
        gap: '2px', 
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '8px',
        padding: '2px 0',
        flexWrap: 'nowrap'
      }}
      title={`${dailyProbabilities.length} days of data`}
    >
      {sampledData.map((day, index) => {
        const color = getColor(day.probability);
        const isForecast = day.source === 'forecast';
        
        return (
          <div
            key={index}
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              backgroundColor: isForecast ? color : 'transparent',
              border: `1px solid ${color}`,
              flexShrink: 0,
              display: 'block'
            }}
            title={`${day.date}: ${Math.round(day.probability * 100)}% (${day.source})`}
          />
        );
      })}
    </div>
  );
};

export default Sparkline; 