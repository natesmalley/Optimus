/**
 * ProjectCard - Individual project card with status and controls
 * Shows project information, orchestration status, and action buttons
 */

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Play, 
  Square, 
  RotateCcw, 
  Settings,
  ExternalLink,
  Activity,
  Clock,
  AlertCircle,
  CheckCircle,
  Loader2,
  Cpu,
  MemoryStick
} from 'lucide-react';
import { useProjectActions, useProjectResourceUsage } from '../../hooks/useOrchestration';
import { StatusBadge } from '../ui/StatusBadge';
import { formatDistanceToNow } from 'date-fns';
import type { Project, OrchestrationStatus } from '../../types/api';

interface ProjectCardProps {
  project: Project;
  orchestrationStatus?: OrchestrationStatus;
  isSelected: boolean;
  onSelect: () => void;
  viewMode: 'grid' | 'list';
}

export function ProjectCard({ 
  project, 
  orchestrationStatus, 
  isSelected, 
  onSelect,
  viewMode 
}: ProjectCardProps) {
  const [showDetails, setShowDetails] = useState(false);
  
  const { 
    launch, 
    stop, 
    restart,
    isLaunching, 
    isStopping, 
    isLoading,
    error 
  } = useProjectActions(project.id);

  const { resources } = useProjectResourceUsage(project.id);

  const isRunning = orchestrationStatus?.is_running || false;
  const environment = orchestrationStatus?.environment || 'dev';

  const handleLaunch = async () => {
    try {
      await launch({ environment: 'dev', wait_for_health: true });
    } catch (err) {
      console.error('Failed to launch project:', err);
    }
  };

  const handleStop = async () => {
    try {
      await stop({ timeout: 30 });
    } catch (err) {
      console.error('Failed to stop project:', err);
    }
  };

  const handleRestart = async () => {
    try {
      await restart(environment);
    } catch (err) {
      console.error('Failed to restart project:', err);
    }
  };

  const openInBrowser = () => {
    if (orchestrationStatus?.port) {
      window.open(`http://localhost:${orchestrationStatus.port}`, '_blank');
    }
  };

  const getStatusColor = () => {
    if (isLoading) return 'yellow';
    if (error) return 'red';
    if (isRunning) return 'green';
    return 'gray';
  };

  const getStatusText = () => {
    if (isLoading) {
      if (isLaunching) return 'Launching...';
      if (isStopping) return 'Stopping...';
      return 'Processing...';
    }
    if (error) return 'Error';
    if (isRunning) return 'Running';
    return 'Stopped';
  };

  if (viewMode === 'list') {
    return (
      <motion.div
        whileHover={{ scale: 1.01 }}
        className={`flex items-center justify-between rounded-lg bg-white p-4 shadow-md border transition-all duration-200 ${
          isSelected ? 'ring-2 ring-blue-500' : 'hover:shadow-lg'
        }`}
      >
        <div className="flex items-center space-x-4 flex-1">
          <div className="flex-shrink-0">
            <StatusBadge status={getStatusColor()} />
          </div>
          
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-gray-900 truncate">{project.name}</h3>
            <div className="flex items-center space-x-4 text-sm text-gray-500">
              <span>{getStatusText()}</span>
              {orchestrationStatus?.port && (
                <span>Port: {orchestrationStatus.port}</span>
              )}
              <span>Env: {environment}</span>
              {resources && (
                <span>CPU: {resources.current_usage.cpu_percent.toFixed(1)}%</span>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {!isRunning ? (
              <button
                onClick={handleLaunch}
                disabled={isLoading}
                className="flex items-center space-x-1 rounded-md bg-green-600 px-3 py-1 text-sm text-white hover:bg-green-700 disabled:opacity-50"
              >
                {isLaunching ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Play className="h-4 w-4" />
                )}
                <span>Start</span>
              </button>
            ) : (
              <div className="flex space-x-2">
                <button
                  onClick={handleStop}
                  disabled={isLoading}
                  className="flex items-center space-x-1 rounded-md bg-red-600 px-3 py-1 text-sm text-white hover:bg-red-700 disabled:opacity-50"
                >
                  {isStopping ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Square className="h-4 w-4" />
                  )}
                  <span>Stop</span>
                </button>
                
                <button
                  onClick={handleRestart}
                  disabled={isLoading}
                  className="flex items-center space-x-1 rounded-md bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  <RotateCcw className="h-4 w-4" />
                  <span>Restart</span>
                </button>

                {orchestrationStatus?.port && (
                  <button
                    onClick={openInBrowser}
                    className="flex items-center space-x-1 rounded-md bg-gray-600 px-3 py-1 text-sm text-white hover:bg-gray-700"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </button>
                )}
              </div>
            )}

            <button
              onClick={onSelect}
              className="rounded-md bg-gray-100 p-1 text-gray-600 hover:bg-gray-200"
            >
              <Settings className="h-4 w-4" />
            </button>
          </div>
        </div>
      </motion.div>
    );
  }

  // Grid view
  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={`relative rounded-xl bg-white p-6 shadow-md border transition-all duration-200 ${
        isSelected ? 'ring-2 ring-blue-500' : 'hover:shadow-lg'
      }`}
    >
      {/* Status indicator */}
      <div className="absolute top-4 right-4">
        <StatusBadge status={getStatusColor()} />
      </div>

      {/* Project header */}
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900 truncate pr-8">
          {project.name}
        </h3>
        <p className="text-sm text-gray-600 mt-1 truncate">
          {project.description || project.path}
        </p>
      </div>

      {/* Status info */}
      <div className="mb-4 space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Status:</span>
          <span className={`font-medium ${
            isRunning ? 'text-green-600' : 'text-gray-600'
          }`}>
            {getStatusText()}
          </span>
        </div>

        <div className="flex items-center justify-between text-sm">
          <span className="text-gray-600">Environment:</span>
          <span className="font-medium text-blue-600">{environment}</span>
        </div>

        {orchestrationStatus?.port && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Port:</span>
            <span className="font-medium">{orchestrationStatus.port}</span>
          </div>
        )}

        {orchestrationStatus?.start_time && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-600">Uptime:</span>
            <span className="font-medium">
              {formatDistanceToNow(new Date(orchestrationStatus.start_time))}
            </span>
          </div>
        )}
      </div>

      {/* Resource usage */}
      {resources && (
        <div className="mb-4 space-y-2">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center space-x-1">
              <Cpu className="h-4 w-4 text-blue-500" />
              <span className="text-gray-600">CPU:</span>
            </div>
            <span className="font-medium">
              {resources.current_usage.cpu_percent.toFixed(1)}%
            </span>
          </div>
          
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center space-x-1">
              <MemoryStick className="h-4 w-4 text-purple-500" />
              <span className="text-gray-600">Memory:</span>
            </div>
            <span className="font-medium">
              {(resources.current_usage.memory_mb / 1024).toFixed(1)} GB
            </span>
          </div>
        </div>
      )}

      {/* Error display */}
      {error && (
        <div className="mb-4 rounded-md bg-red-50 p-3 border border-red-200">
          <div className="flex items-center space-x-2">
            <AlertCircle className="h-4 w-4 text-red-500" />
            <span className="text-sm text-red-800">
              {error instanceof Error ? error.message : 'An error occurred'}
            </span>
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex space-x-2">
        {!isRunning ? (
          <button
            onClick={handleLaunch}
            disabled={isLoading}
            className="flex-1 flex items-center justify-center space-x-2 rounded-lg bg-green-600 py-2 text-white hover:bg-green-700 disabled:opacity-50 transition-colors"
          >
            {isLaunching ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            <span>Launch</span>
          </button>
        ) : (
          <>
            <button
              onClick={handleStop}
              disabled={isLoading}
              className="flex-1 flex items-center justify-center space-x-2 rounded-lg bg-red-600 py-2 text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
            >
              {isStopping ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Square className="h-4 w-4" />
              )}
              <span>Stop</span>
            </button>
            
            <button
              onClick={handleRestart}
              disabled={isLoading}
              className="flex-1 flex items-center justify-center space-x-2 rounded-lg bg-blue-600 py-2 text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              <RotateCcw className="h-4 w-4" />
              <span>Restart</span>
            </button>

            {orchestrationStatus?.port && (
              <button
                onClick={openInBrowser}
                className="rounded-lg bg-gray-600 p-2 text-white hover:bg-gray-700 transition-colors"
              >
                <ExternalLink className="h-4 w-4" />
              </button>
            )}
          </>
        )}

        <button
          onClick={onSelect}
          className="rounded-lg bg-gray-100 p-2 text-gray-600 hover:bg-gray-200 transition-colors"
        >
          <Settings className="h-4 w-4" />
        </button>
      </div>

      {/* Quick details toggle */}
      <button
        onClick={() => setShowDetails(!showDetails)}
        className="mt-3 w-full text-xs text-gray-500 hover:text-gray-700"
      >
        {showDetails ? 'Hide Details' : 'Show Details'}
      </button>

      {/* Expandable details */}
      {showDetails && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="mt-3 rounded-md bg-gray-50 p-3 text-xs space-y-1"
        >
          <div><strong>Path:</strong> {project.path}</div>
          {project.git_url && (
            <div><strong>Git:</strong> {project.git_url}</div>
          )}
          {project.tech_stack && (
            <div><strong>Stack:</strong> {Object.keys(project.tech_stack).join(', ')}</div>
          )}
          {orchestrationStatus?.last_heartbeat && (
            <div>
              <strong>Last Check:</strong>{' '}
              {formatDistanceToNow(new Date(orchestrationStatus.last_heartbeat))} ago
            </div>
          )}
        </motion.div>
      )}
    </motion.div>
  );
}