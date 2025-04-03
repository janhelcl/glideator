import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
  Typography,
  Box
} from '@mui/material';

const DisclaimerModal = ({ open, onAccept, onDecline }) => {
  return (
    <Dialog
      open={open}
      disableEscapeKeyDown
      onClose={(event, reason) => {
        // Prevent closing the dialog by clicking outside
        if (reason !== 'backdropClick') {
          return;
        }
      }}
      aria-labelledby="disclaimer-dialog-title"
      aria-describedby="disclaimer-dialog-description"
    >
      <DialogTitle id="disclaimer-dialog-title">
        <Typography variant="h5" component="div" align="center" fontWeight="bold">
          Important Disclaimer
        </Typography>
      </DialogTitle>
      <DialogContent>
        <DialogContentText id="disclaimer-dialog-description">
          <Typography paragraph>
            Welcome to Glideator! Before you proceed, please read and acknowledge the following disclaimer:
          </Typography>
          <Typography paragraph>
            The information provided by this application is for general informational purposes only. All data and forecasts 
            should be used at your own risk and discretion.
          </Typography>
          <Typography paragraph>
            Weather conditions can change rapidly and unpredictably. Always check official weather sources and consult with 
            qualified professionals before making any decisions based on the information provided here.
          </Typography>
          <Typography paragraph>
            It is up to a properly <Box component="span" fontWeight="bold">trained and licensed pilot</Box> to make the decision to fly or not.
          </Typography>
          <Typography paragraph>
            By accepting this disclaimer, you acknowledge that you understand and accept these terms.
          </Typography>
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={onDecline} color="error" variant="contained">
          Decline
        </Button>
        <Button onClick={onAccept} color="primary" variant="contained" autoFocus>
          Accept
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default DisclaimerModal; 