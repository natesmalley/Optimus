/**
 * WebSocket client for real-time communication with the backend
 * Handles deliberation updates and system events
 */

import React from 'react';
import type { WebSocketMessage, DeliberationProgress } from '@/types';

export type WebSocketEventHandler = (message: WebSocketMessage) => void;

export class DeliberationWebSocket {
  private ws: WebSocket | null = null;
  private deliberationId: string;
  private listeners: Map<string, WebSocketEventHandler[]> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private heartbeatInterval: NodeJS.Timeout | null = null;

  constructor(deliberationId: string) {
    this.deliberationId = deliberationId;
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/deliberation/${this.deliberationId}`;
        
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log(`WebSocket connected for deliberation: ${this.deliberationId}`);
          this.reconnectAttempts = 0;
          this.startHeartbeat();
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            this.handleMessage(message);
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
          }
        };

        this.ws.onclose = () => {
          console.log('WebSocket connection closed');
          this.stopHeartbeat();
          this.attemptReconnect();
        };

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };

      } catch (error) {
        reject(error);
      }
    });
  }

  private handleMessage(message: WebSocketMessage) {
    // Emit to type-specific listeners
    const typeListeners = this.listeners.get(message.type) || [];
    typeListeners.forEach(handler => handler(message));

    // Emit to global listeners
    const globalListeners = this.listeners.get('*') || [];
    globalListeners.forEach(handler => handler(message));
  }

  private startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.send('ping', {});
      }
    }, 30000); // Ping every 30 seconds
  }

  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  private attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnect attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);

    setTimeout(async () => {
      try {
        await this.connect();
      } catch (error) {
        console.error('Reconnection failed:', error);
      }
    }, delay);
  }

  send(type: string, data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type,
        data,
        timestamp: new Date().toISOString()
      }));
    } else {
      console.warn('WebSocket not connected, cannot send message');
    }
  }

  on(eventType: string, handler: WebSocketEventHandler) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, []);
    }
    this.listeners.get(eventType)!.push(handler);
  }

  off(eventType: string, handler: WebSocketEventHandler) {
    const handlers = this.listeners.get(eventType);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    }
  }

  disconnect() {
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

export class SystemWebSocket {
  private ws: WebSocket | null = null;
  private listeners: Map<string, WebSocketEventHandler[]> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/system`;
        
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          console.log('System WebSocket connected');
          this.reconnectAttempts = 0;
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message: WebSocketMessage = JSON.parse(event.data);
            this.handleMessage(message);
          } catch (error) {
            console.error('Failed to parse system WebSocket message:', error);
          }
        };

        this.ws.onclose = () => {
          console.log('System WebSocket connection closed');
          this.attemptReconnect();
        };

        this.ws.onerror = (error) => {
          console.error('System WebSocket error:', error);
          reject(error);
        };

      } catch (error) {
        reject(error);
      }
    });
  }

  private handleMessage(message: WebSocketMessage) {
    const typeListeners = this.listeners.get(message.type) || [];
    typeListeners.forEach(handler => handler(message));

    const globalListeners = this.listeners.get('*') || [];
    globalListeners.forEach(handler => handler(message));
  }

  private attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max system WebSocket reconnect attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    setTimeout(async () => {
      try {
        await this.connect();
      } catch (error) {
        console.error('System WebSocket reconnection failed:', error);
      }
    }, delay);
  }

  send(type: string, data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data, timestamp: new Date().toISOString() }));
    }
  }

  on(eventType: string, handler: WebSocketEventHandler) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, []);
    }
    this.listeners.get(eventType)!.push(handler);
  }

  off(eventType: string, handler: WebSocketEventHandler) {
    const handlers = this.listeners.get(eventType);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// Utility to create a deliberation WebSocket with React hooks integration
export function useDeliberationWebSocket(deliberationId: string) {
  const wsRef = React.useRef<DeliberationWebSocket | null>(null);
  const [isConnected, setIsConnected] = React.useState(false);
  const [progress, setProgress] = React.useState<DeliberationProgress | null>(null);

  React.useEffect(() => {
    if (!deliberationId) return;

    const ws = new DeliberationWebSocket(deliberationId);
    wsRef.current = ws;

    // Set up event handlers
    ws.on('connection_established', () => setIsConnected(true));
    ws.on('deliberation_start', (message) => {
      setProgress({
        deliberation_id: deliberationId,
        stage: 'starting',
        personas_completed: [],
        total_personas: 0
      });
    });
    
    ws.on('deliberation_progress', (message) => {
      setProgress(prev => ({
        ...prev!,
        stage: message.data.stage,
        total_personas: message.data.total_personas
      }));
    });

    ws.on('persona_response', (message) => {
      setProgress(prev => ({
        ...prev!,
        personas_completed: message.data.personas_completed,
        current_confidence: message.data.confidence
      }));
    });

    ws.on('deliberation_complete', (message) => {
      setProgress(prev => ({
        ...prev!,
        stage: 'complete'
      }));
    });

    // Connect
    ws.connect().catch(console.error);

    return () => {
      ws.disconnect();
      wsRef.current = null;
      setIsConnected(false);
      setProgress(null);
    };
  }, [deliberationId]);

  return {
    ws: wsRef.current,
    isConnected,
    progress,
    send: (type: string, data: any) => wsRef.current?.send(type, data),
    on: (eventType: string, handler: WebSocketEventHandler) => wsRef.current?.on(eventType, handler),
    off: (eventType: string, handler: WebSocketEventHandler) => wsRef.current?.off(eventType, handler)
  };
}