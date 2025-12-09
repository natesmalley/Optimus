/**
 * Generic WebSocket hook for real-time communication
 * Supports orchestration, deployment, backup, and other real-time updates
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import type { OrchestrationWebSocketMessage } from '../types/api';

interface UseWebSocketOptions {
  url: string;
  onMessage?: (message: any) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onError?: (error: Event) => void;
  reconnect?: boolean;
  reconnectAttempts?: number;
  reconnectInterval?: number;
}

export function useWebSocket({
  url,
  onMessage,
  onConnect,
  onDisconnect,
  onError,
  reconnect = true,
  reconnectAttempts = 5,
  reconnectInterval = 1000,
}: UseWebSocketOptions) {
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [error, setError] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const attemptCountRef = useRef(0);
  const heartbeatIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    try {
      setConnectionStatus('connecting');
      setError(null);

      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}${url}`;
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log(`WebSocket connected: ${url}`);
        setIsConnected(true);
        setConnectionStatus('connected');
        attemptCountRef.current = 0;
        setError(null);
        
        // Start heartbeat
        heartbeatIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping', timestamp: new Date().toISOString() }));
          }
        }, 30000);

        onConnect?.();
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          // Handle pong responses
          if (message.type === 'pong') {
            return;
          }

          onMessage?.(message);
        } catch (err) {
          console.error('Failed to parse WebSocket message:', err);
          setError('Failed to parse message');
        }
      };

      ws.onclose = (event) => {
        console.log(`WebSocket disconnected: ${url}`, event.code, event.reason);
        setIsConnected(false);
        setConnectionStatus('disconnected');
        
        // Clear heartbeat
        if (heartbeatIntervalRef.current) {
          clearInterval(heartbeatIntervalRef.current);
          heartbeatIntervalRef.current = null;
        }

        onDisconnect?.();

        // Attempt reconnection if enabled and not a normal closure
        if (reconnect && event.code !== 1000 && attemptCountRef.current < reconnectAttempts) {
          attemptReconnection();
        }
      };

      ws.onerror = (event) => {
        console.error(`WebSocket error: ${url}`, event);
        setConnectionStatus('error');
        setError('Connection error');
        onError?.(event);
      };

    } catch (err) {
      console.error('Failed to create WebSocket connection:', err);
      setConnectionStatus('error');
      setError('Failed to create connection');
    }
  }, [url, onMessage, onConnect, onDisconnect, onError, reconnect, reconnectAttempts]);

  const attemptReconnection = useCallback(() => {
    if (attemptCountRef.current >= reconnectAttempts) {
      console.error(`Max WebSocket reconnection attempts reached for ${url}`);
      setError('Max reconnection attempts reached');
      return;
    }

    attemptCountRef.current++;
    const delay = reconnectInterval * Math.pow(2, attemptCountRef.current - 1);
    
    console.log(`Attempting WebSocket reconnection ${attemptCountRef.current}/${reconnectAttempts} in ${delay}ms`);

    reconnectTimeoutRef.current = setTimeout(() => {
      connect();
    }, delay);
  }, [connect, reconnectAttempts, reconnectInterval, url]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, 'Manual disconnect');
      wsRef.current = null;
    }

    setIsConnected(false);
    setConnectionStatus('disconnected');
    attemptCountRef.current = 0;
  }, []);

  const sendMessage = useCallback((message: any) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        ...message,
        timestamp: new Date().toISOString(),
      }));
      return true;
    } else {
      console.warn('WebSocket not connected, cannot send message');
      return false;
    }
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    connect();
    
    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    isConnected,
    connectionStatus,
    error,
    sendMessage,
    reconnect: connect,
    disconnect,
  };
}

// Specialized hook for orchestration WebSocket
export function useOrchestrationWebSocket() {
  const [lastMessage, setLastMessage] = useState<OrchestrationWebSocketMessage | null>(null);
  const [messageHistory, setMessageHistory] = useState<OrchestrationWebSocketMessage[]>([]);

  const handleMessage = useCallback((message: OrchestrationWebSocketMessage) => {
    setLastMessage(message);
    setMessageHistory(prev => [...prev.slice(-99), message]); // Keep last 100 messages
  }, []);

  const { isConnected, connectionStatus, error, sendMessage, disconnect } = useWebSocket({
    url: '/ws/orchestration',
    onMessage: handleMessage,
    onConnect: () => console.log('Orchestration WebSocket connected'),
    onDisconnect: () => console.log('Orchestration WebSocket disconnected'),
    onError: (error) => console.error('Orchestration WebSocket error:', error),
  });

  const subscribeToProject = useCallback((projectId: string) => {
    return sendMessage({
      type: 'subscribe',
      project_id: projectId,
    });
  }, [sendMessage]);

  const unsubscribeFromProject = useCallback((projectId: string) => {
    return sendMessage({
      type: 'unsubscribe', 
      project_id: projectId,
    });
  }, [sendMessage]);

  return {
    isConnected,
    connectionStatus,
    error,
    lastMessage,
    messageHistory,
    subscribeToProject,
    unsubscribeFromProject,
    disconnect,
  };
}

// Hook for deployment WebSocket updates
export function useDeploymentWebSocket(projectId?: string) {
  const [deploymentUpdates, setDeploymentUpdates] = useState<any[]>([]);

  const handleMessage = useCallback((message: any) => {
    if (message.type === 'deployment_progress' || message.type === 'deployment_complete') {
      if (!projectId || message.project_id === projectId) {
        setDeploymentUpdates(prev => [...prev.slice(-49), message]); // Keep last 50 updates
      }
    }
  }, [projectId]);

  const { isConnected, connectionStatus, sendMessage } = useWebSocket({
    url: '/ws/deployment',
    onMessage: handleMessage,
  });

  useEffect(() => {
    if (isConnected && projectId) {
      sendMessage({ type: 'subscribe', project_id: projectId });
    }
  }, [isConnected, projectId, sendMessage]);

  return {
    isConnected,
    connectionStatus,
    deploymentUpdates,
    clearUpdates: () => setDeploymentUpdates([]),
  };
}

// Hook for backup WebSocket updates  
export function useBackupWebSocket(projectId?: string) {
  const [backupUpdates, setBackupUpdates] = useState<any[]>([]);

  const handleMessage = useCallback((message: any) => {
    if (message.type === 'backup_progress' || message.type === 'backup_complete') {
      if (!projectId || message.project_id === projectId) {
        setBackupUpdates(prev => [...prev.slice(-49), message]); // Keep last 50 updates
      }
    }
  }, [projectId]);

  const { isConnected, connectionStatus, sendMessage } = useWebSocket({
    url: '/ws/backup',
    onMessage: handleMessage,
  });

  useEffect(() => {
    if (isConnected && projectId) {
      sendMessage({ type: 'subscribe', project_id: projectId });
    }
  }, [isConnected, projectId, sendMessage]);

  return {
    isConnected,
    connectionStatus,
    backupUpdates,
    clearUpdates: () => setBackupUpdates([]),
  };
}