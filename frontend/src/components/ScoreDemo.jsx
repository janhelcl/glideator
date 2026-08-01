import React, { Suspense, useEffect, useState } from 'react';
import { Box } from '@mui/material';

const ScoreDemoClient = React.lazy(() => import('./ScoreDemoClient'));

const ScoreDemo = () => {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <Box sx={{ minHeight: { xs: 500, sm: 340 } }} aria-hidden="true" />;
  }

  return (
    <Suspense fallback={<Box sx={{ minHeight: { xs: 500, sm: 340 } }} aria-hidden="true" />}>
      <ScoreDemoClient />
    </Suspense>
  );
};

export default ScoreDemo;
