import { useAuth } from '../context/AuthContext';

/**
 * Custom hook for getting the user's preferred metric with proper fallbacks
 *
 * Returns:
 * - preferredMetric: The user's preferred metric or 'XC0' as fallback
 * - isLoading: Boolean indicating if profile is still loading
 *
 * Priority:
 * 1. User's preferred_metric from profile (if authenticated and set)
 * 2. 'XC0' as fallback (not authenticated or not set)
 */
export const useDefaultMetric = () => {
  const { profile, isAuthenticated, isLoading } = useAuth();

  // While loading, return default but indicate loading state
  if (isLoading) {
    return {
      preferredMetric: 'XC0',
      isLoading: true
    };
  }

  // If authenticated and has preferred_metric, use it
  if (isAuthenticated && profile?.preferred_metric) {
    return {
      preferredMetric: profile.preferred_metric,
      isLoading: false
    };
  }

  // Fallback to XC0
  return {
    preferredMetric: 'XC0',
    isLoading: false
  };
};
