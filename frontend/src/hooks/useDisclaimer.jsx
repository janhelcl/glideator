import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const useDisclaimer = () => {
  const [showDisclaimer, setShowDisclaimer] = useState(false);
  const navigate = useNavigate();
  
  useEffect(() => {
    // Check if user has previously accepted the disclaimer
    const hasAccepted = localStorage.getItem('disclaimerAccepted');
    
    if (!hasAccepted) {
      setShowDisclaimer(true);
    }
  }, []);
  
  const handleAccept = () => {
    localStorage.setItem('disclaimerAccepted', 'true');
    setShowDisclaimer(false);
  };
  
  const handleDecline = () => {
    // Navigate to declined page
    navigate('/declined');
  };
  
  return {
    showDisclaimer,
    handleAccept,
    handleDecline
  };
};

export default useDisclaimer; 