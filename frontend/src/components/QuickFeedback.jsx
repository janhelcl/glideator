import React, { useState } from 'react';
import { Box, Button, Paper, Typography } from '@mui/material';
import ThumbDownAltOutlinedIcon from '@mui/icons-material/ThumbDownAltOutlined';
import ThumbUpAltOutlinedIcon from '@mui/icons-material/ThumbUpAltOutlined';

import { trackEvent } from '../analytics';

const QuickFeedback = ({
  question,
  context,
  eventName = 'recommendation_feedback_submitted',
}) => {
  const [response, setResponse] = useState(null);

  const submit = (rating) => {
    if (response) return;
    setResponse(rating);
    trackEvent(eventName, {
      ...context,
      rating,
    });
  };

  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2,
        display: 'flex',
        flexDirection: { xs: 'column', sm: 'row' },
        alignItems: { xs: 'stretch', sm: 'center' },
        justifyContent: 'space-between',
        gap: 1.5,
      }}
    >
      {response ? (
        <Typography variant="body2" color="text.secondary">
          Thanks — this helps improve Glideator's recommendations.
        </Typography>
      ) : (
        <>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {question}
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              size="small"
              variant="outlined"
              startIcon={<ThumbUpAltOutlinedIcon />}
              onClick={() => submit('helpful')}
            >
              Helpful
            </Button>
            <Button
              size="small"
              variant="outlined"
              startIcon={<ThumbDownAltOutlinedIcon />}
              onClick={() => submit('not_helpful')}
            >
              Not helpful
            </Button>
          </Box>
        </>
      )}
    </Paper>
  );
};

export default QuickFeedback;
