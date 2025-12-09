/**
 * Hook for managing orchestration operations and real-time updates
 * Provides easy access to orchestration services with proper state management
 */

import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { orchestrationService } from '../services/orchestrationService';
import { useWebSocket } from './useWebSocket';
import type {
  OrchestrationStatus,
  LaunchProjectRequest,
  StopProjectRequest,
  SwitchEnvironmentRequest,
  ResourceAllocation,
  ResourceAllocationRequest,
  OrchestrationWebSocketMessage,
} from '../types/api';

export function useOrchestrationStatus(projectId?: string) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: projectId ? ['orchestration', 'status', projectId] : ['orchestration', 'status'],
    queryFn: () => 
      projectId 
        ? orchestrationService.getProjectStatus(projectId)
        : orchestrationService.getAllProjectStatuses(),
    refetchInterval: 30000, // Refetch every 30 seconds
    staleTime: 10000, // Data is fresh for 10 seconds
  });

  return {
    status: data as OrchestrationStatus | OrchestrationStatus[],
    isLoading,
    error,
    refresh: refetch,
  };
}

export function useProjectLauncher() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ 
      projectId, 
      options = {} 
    }: { 
      projectId: string; 
      options?: LaunchProjectRequest 
    }) => {
      return orchestrationService.launchProject(projectId, options);
    },
    onSuccess: (data, variables) => {
      // Invalidate and refetch status queries
      queryClient.invalidateQueries({ queryKey: ['orchestration', 'status'] });
      queryClient.invalidateQueries({ queryKey: ['orchestration', 'status', variables.projectId] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

export function useProjectStopper() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ 
      projectId, 
      options = {} 
    }: { 
      projectId: string; 
      options?: StopProjectRequest 
    }) => {
      return orchestrationService.stopProject(projectId, options);
    },
    onSuccess: (data, variables) => {
      // Invalidate and refetch status queries
      queryClient.invalidateQueries({ queryKey: ['orchestration', 'status'] });
      queryClient.invalidateQueries({ queryKey: ['orchestration', 'status', variables.projectId] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}

export function useEnvironmentSwitcher() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ 
      projectId, 
      request 
    }: { 
      projectId: string; 
      request: SwitchEnvironmentRequest 
    }) => {
      return orchestrationService.switchEnvironment(projectId, request);
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['orchestration', 'status'] });
      queryClient.invalidateQueries({ queryKey: ['orchestration', 'status', variables.projectId] });
      queryClient.invalidateQueries({ queryKey: ['orchestration', 'environment', variables.projectId] });
    },
  });
}

export function useResourceManager() {
  const queryClient = useQueryClient();
  
  const allocateMutation = useMutation({
    mutationFn: ({ 
      projectId, 
      allocation 
    }: { 
      projectId: string; 
      allocation: ResourceAllocationRequest 
    }) => {
      return orchestrationService.allocateResources(projectId, allocation);
    },
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['orchestration', 'resources'] });
      queryClient.invalidateQueries({ queryKey: ['orchestration', 'resources', variables.projectId] });
    },
  });

  const { data: resourceUsage, isLoading, error, refetch } = useQuery({
    queryKey: ['orchestration', 'resources'],
    queryFn: () => orchestrationService.getAllResourceUsage(),
    refetchInterval: 10000, // Refetch every 10 seconds for resource data
  });

  const { data: systemSummary } = useQuery({
    queryKey: ['orchestration', 'resources', 'summary'],
    queryFn: () => orchestrationService.getSystemResourceSummary(),
    refetchInterval: 15000,
  });

  return {
    resourceUsage: resourceUsage as ResourceAllocation[],
    systemSummary,
    isLoading,
    error,
    refresh: refetch,
    allocateResources: allocateMutation.mutateAsync,
    isAllocating: allocateMutation.isPending,
  };
}

export function useProjectResourceUsage(projectId: string) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['orchestration', 'resources', projectId],
    queryFn: () => orchestrationService.getResourceUsage(projectId),
    refetchInterval: 10000,
    enabled: !!projectId,
  });

  return {
    resources: data as ResourceAllocation,
    isLoading,
    error,
    refresh: refetch,
  };
}

export function useOrchestrationWebSocket() {
  const queryClient = useQueryClient();
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');

  const handleMessage = useCallback((message: OrchestrationWebSocketMessage) => {
    console.log('Orchestration WebSocket message:', message);

    switch (message.type) {
      case 'project_status_change':
        if (message.project_id) {
          queryClient.invalidateQueries({ 
            queryKey: ['orchestration', 'status', message.project_id] 
          });
          queryClient.invalidateQueries({ 
            queryKey: ['orchestration', 'status'] 
          });
        }
        break;

      case 'resource_update':
        if (message.project_id) {
          queryClient.invalidateQueries({ 
            queryKey: ['orchestration', 'resources', message.project_id] 
          });
        }
        queryClient.invalidateQueries({ 
          queryKey: ['orchestration', 'resources'] 
        });
        break;

      case 'deployment_progress':
        if (message.project_id) {
          queryClient.invalidateQueries({ 
            queryKey: ['deployment', message.project_id] 
          });
        }
        break;

      case 'backup_progress':
        if (message.project_id) {
          queryClient.invalidateQueries({ 
            queryKey: ['backup', message.project_id] 
          });
        }
        break;

      case 'environment_switch':
        if (message.project_id) {
          queryClient.invalidateQueries({ 
            queryKey: ['orchestration', 'environment', message.project_id] 
          });
          queryClient.invalidateQueries({ 
            queryKey: ['orchestration', 'status', message.project_id] 
          });
        }
        break;

      case 'error':
        console.error('Orchestration WebSocket error:', message.data);
        break;
    }
  }, [queryClient]);

  const handleConnect = useCallback(() => {
    console.log('Orchestration WebSocket connected');
    setConnectionStatus('connected');
  }, []);

  const handleDisconnect = useCallback(() => {
    console.log('Orchestration WebSocket disconnected');
    setConnectionStatus('disconnected');
  }, []);

  const handleError = useCallback((error: Event) => {
    console.error('Orchestration WebSocket error:', error);
    setConnectionStatus('disconnected');
  }, []);

  const { sendMessage } = useWebSocket({
    url: '/ws/orchestration',
    onMessage: handleMessage,
    onConnect: handleConnect,
    onDisconnect: handleDisconnect,
    onError: handleError,
  });

  return {
    connectionStatus,
    sendMessage,
  };
}

export function useProjectActions(projectId: string) {
  const launchMutation = useProjectLauncher();
  const stopMutation = useProjectStopper();
  const environmentMutation = useEnvironmentSwitcher();
  
  const launch = useCallback(
    (options?: LaunchProjectRequest) => launchMutation.mutateAsync({ projectId, options }),
    [projectId, launchMutation]
  );

  const stop = useCallback(
    (options?: StopProjectRequest) => stopMutation.mutateAsync({ projectId, options }),
    [projectId, stopMutation]
  );

  const switchEnvironment = useCallback(
    (request: SwitchEnvironmentRequest) => environmentMutation.mutateAsync({ projectId, request }),
    [projectId, environmentMutation]
  );

  const restart = useCallback(
    async (environment?: string) => {
      await stop({ timeout: 30 });
      // Wait for stop to complete
      await new Promise(resolve => setTimeout(resolve, 2000));
      return launch({ environment, wait_for_health: true });
    },
    [stop, launch]
  );

  return {
    launch,
    stop,
    restart,
    switchEnvironment,
    isLaunching: launchMutation.isPending,
    isStopping: stopMutation.isPending,
    isSwitchingEnvironment: environmentMutation.isPending,
    isLoading: launchMutation.isPending || stopMutation.isPending || environmentMutation.isPending,
    error: launchMutation.error || stopMutation.error || environmentMutation.error,
  };
}