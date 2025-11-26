import { useEffect, useRef } from 'react';
import { useDashboardStore } from '@/store';

/**
 * Hook for auto-refreshing queries based on dashboard settings
 */
export function useAutoRefresh(refetchFn: () => void) {
  const { autoRefresh, refreshInterval } = useDashboardStore();
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (autoRefresh && refreshInterval > 0) {
      intervalRef.current = setInterval(refetchFn, refreshInterval);
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [autoRefresh, refreshInterval, refetchFn]);

  // Manual refresh function
  const manualRefresh = () => {
    refetchFn();
  };

  return { manualRefresh };
}