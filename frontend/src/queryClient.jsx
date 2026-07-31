import { QueryClient } from '@tanstack/react-query';

const shouldRetry = (failureCount, error) => {
  const status = error?.response?.status;

  if (status && status >= 400 && status < 500) {
    return false;
  }

  return failureCount < 1;
};

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      gcTime: 30 * 60 * 1000,
      retry: shouldRetry,
      refetchOnWindowFocus: false,
    },
  },
});
