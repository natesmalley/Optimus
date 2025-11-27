/**
 * Real-time Deliberation Progress Component
 * Shows live updates during deliberation process
 */

import React, { useState, useEffect } from 'react';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { DeliberationWebSocket } from '@/lib/websocket';
import type { WebSocketMessage, DeliberationProgress as ProgressType } from '@/types';

interface DeliberationProgressProps {
  deliberationId: string;
  onComplete?: (result: any) => void;
  onError?: (error: string) => void;
}

export function DeliberationProgress({ 
  deliberationId, 
  onComplete, 
  onError 
}: DeliberationProgressProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [progress, setProgress] = useState<ProgressType | null>(null);
  const [personaResponses, setPersonaResponses] = useState<any[]>([]);
  const [currentStage, setCurrentStage] = useState<string>('connecting');
  const [error, setError] = useState<string | null>(null);
  const [ws, setWs] = useState<DeliberationWebSocket | null>(null);

  useEffect(() => {
    if (!deliberationId) return;

    const websocket = new DeliberationWebSocket(deliberationId);
    setWs(websocket);

    // Set up event handlers
    websocket.on('connection_established', () => {
      setIsConnected(true);
      setCurrentStage('connected');
    });

    websocket.on('deliberation_start', (message: WebSocketMessage) => {
      setCurrentStage('starting');
      setProgress({
        deliberation_id: deliberationId,
        stage: 'starting',
        personas_completed: [],
        total_personas: 0
      });
    });

    websocket.on('deliberation_progress', (message: WebSocketMessage) => {
      setCurrentStage(message.data.stage);
      setProgress(prev => ({
        ...prev!,
        stage: message.data.stage,
        total_personas: message.data.total_personas
      }));
    });

    websocket.on('persona_response', (message: WebSocketMessage) => {
      setPersonaResponses(prev => [...prev, message.data]);
      setProgress(prev => ({
        ...prev!,
        personas_completed: message.data.personas_completed,
        current_confidence: message.data.confidence
      }));
    });

    websocket.on('consensus_update', (message: WebSocketMessage) => {
      setCurrentStage('reaching_consensus');
      setProgress(prev => ({
        ...prev!,
        stage: 'reaching_consensus',
        current_confidence: message.data.confidence
      }));
    });

    websocket.on('deliberation_complete', (message: WebSocketMessage) => {
      setCurrentStage('complete');
      setProgress(prev => ({
        ...prev!,
        stage: 'complete'
      }));
      onComplete?.(message.data);
    });

    websocket.on('error', (message: WebSocketMessage) => {
      setError(message.data.error);
      setCurrentStage('error');
      onError?.(message.data.error);
    });

    // Connect
    websocket.connect().catch((err) => {
      setError('Failed to connect to real-time updates');
      setCurrentStage('error');
    });

    return () => {
      websocket.disconnect();
    };
  }, [deliberationId, onComplete, onError]);

  const getStageDescription = (stage: string) => {
    switch (stage) {
      case 'connecting': return 'Connecting to real-time updates...';
      case 'connected': return 'Connected. Waiting for deliberation to start...';
      case 'starting': return 'Initializing deliberation...';
      case 'gathering_responses': return 'Gathering persona responses...';
      case 'reaching_consensus': return 'Reaching consensus...';
      case 'complete': return 'Deliberation complete!';
      case 'error': return 'Error occurred during deliberation';
      default: return stage;
    }
  };

  const getProgressPercentage = () => {
    if (!progress) return 0;
    
    switch (progress.stage) {
      case 'starting': return 10;
      case 'gathering_responses':
        if (progress.total_personas === 0) return 20;
        return 20 + (progress.personas_completed.length / progress.total_personas) * 60;
      case 'reaching_consensus': return 85;
      case 'complete': return 100;
      default: return 0;
    }
  };

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center gap-2">
          <StatusBadge status="error" />
          <span className="text-red-800 font-medium">Error</span>
        </div>
        <p className="text-red-700 mt-2">{error}</p>
      </div>
    );
  }

  return (
    <div className="bg-white border rounded-lg p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Deliberation Progress</h3>
        <div className="flex items-center gap-2">
          <StatusBadge status={isConnected ? 'running' : 'stopped'} />
          <span className="text-sm text-gray-600">
            {isConnected ? 'Live Updates' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm">
          <span className="text-gray-600">{getStageDescription(currentStage)}</span>
          <span className="font-medium">{Math.round(getProgressPercentage())}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${getProgressPercentage()}%` }}
          />
        </div>
      </div>

      {/* Current Stage Details */}
      {progress && (
        <div className="bg-gray-50 rounded-lg p-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-600">Stage:</span>
              <div className="font-medium capitalize">{progress.stage.replace('_', ' ')}</div>
            </div>
            {progress.total_personas > 0 && (
              <div>
                <span className="text-gray-600">Personas:</span>
                <div className="font-medium">
                  {progress.personas_completed.length} / {progress.total_personas}
                </div>
              </div>
            )}
            {progress.current_confidence && (
              <div>
                <span className="text-gray-600">Current Confidence:</span>
                <div className="font-medium">{Math.round(progress.current_confidence * 100)}%</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Live Persona Responses */}
      {personaResponses.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-gray-700">Live Persona Responses</h4>
          <div className="max-h-40 overflow-y-auto space-y-2">
            {personaResponses.slice(-5).map((response, index) => (
              <div key={index} className="flex items-start gap-3 p-2 bg-gray-50 rounded">
                <StatusBadge status="running" size="sm" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium">{response.persona_id}</div>
                  <div className="text-xs text-gray-600 truncate">
                    {response.recommendation}
                  </div>
                  <div className="text-xs text-blue-600">
                    {Math.round(response.confidence * 100)}% confidence
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Loading Animation */}
      {currentStage !== 'complete' && currentStage !== 'error' && (
        <div className="flex items-center justify-center py-2">
          <LoadingSpinner size="sm" />
          <span className="ml-2 text-sm text-gray-600">Processing...</span>
        </div>
      )}
    </div>
  );
}