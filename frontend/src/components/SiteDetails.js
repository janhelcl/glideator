import React from 'react';
import { useParams } from 'react-router-dom';

const SiteDetails = () => {
  const { siteName } = useParams();

  return (
    <div>
      <h2>Details for {siteName}</h2>
      <p>Details page is under construction.</p>
    </div>
  );
};

export default SiteDetails;