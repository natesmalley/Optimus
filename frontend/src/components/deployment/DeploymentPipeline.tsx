/**
 * DeploymentPipeline - Visual representation of deployment pipeline
 * Shows deployment steps, progress, and status
 */

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  CheckCircle, 
  AlertTriangle, 
  Clock,
  Loader2,
  Play,
  Pause,
  RotateCcw,
  Eye,
  Download,
  GitBranch
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { deploymentService } from '../../services/deploymentService';
import { formatDistanceToNow, format } from 'date-fns';
import type { DeploymentStatus, DeploymentStep } from '../../types/api';

interface DeploymentPipelineProps {
  projectId: string;
  deploymentStatus?: DeploymentStatus;
  showFullPipeline?: boolean;
}

export function DeploymentPipeline({ 
  projectId, 
  deploymentStatus,
  showFullPipeline = false 
}: DeploymentPipelineProps) {
  const [selectedStep, setSelectedStep] = useState<DeploymentStep | null>(null);
  const [showLogs, setShowLogs] = useState(false);
  const queryClient = useQueryClient();

  // Get deployment logs for selected step
  const { data: stepLogs } = useQuery({
    queryKey: ['deployment', 'logs', projectId, deploymentStatus?.deployment_id, selectedStep?.name],
    queryFn: () => deploymentService.getDeploymentLogs(
      projectId, 
      deploymentStatus!.deployment_id, 
      selectedStep!.name
    ),
    enabled: !!(deploymentStatus?.deployment_id && selectedStep?.name),
  });

  // Cancel deployment mutation
  const cancelMutation = useMutation({
    mutationFn: () => deploymentService.cancelDeployment(
      projectId, 
      deploymentStatus!.deployment_id
    ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deployment', projectId] });
    },
  });

  // Rollback mutation
  const rollbackMutation = useMutation({
    mutationFn: () => deploymentService.rollback(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deployment', projectId] });
    },
  });

  const getStepIcon = (step: DeploymentStep) => {
    switch (step.status) {
      case 'completed': return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'failed': return <AlertTriangle className="h-5 w-5 text-red-600" />;
      case 'running': return <Loader2 className="h-5 w-5 text-blue-600 animate-spin" />;
      case 'pending': return <Clock className="h-5 w-5 text-gray-400" />;
      default: return <div className="h-5 w-5 rounded-full bg-gray-300" />;
    }
  };

  const getStepColor = (step: DeploymentStep) => {
    switch (step.status) {
      case 'completed': return 'border-green-500 bg-green-50';
      case 'failed': return 'border-red-500 bg-red-50';
      case 'running': return 'border-blue-500 bg-blue-50';
      case 'pending': return 'border-gray-300 bg-gray-50';
      default: return 'border-gray-300 bg-white';
    }
  };

  const getOverallStatusColor = () => {
    if (!deploymentStatus) return 'text-gray-600';
    switch (deploymentStatus.status) {
      case 'success': return 'text-green-600';
      case 'failed': return 'text-red-600';
      case 'deploying':
      case 'building': return 'text-blue-600';
      case 'pending': return 'text-yellow-600';
      case 'rolling_back': return 'text-orange-600';
      default: return 'text-gray-600';
    }
  };

  const isActiveDeployment = deploymentStatus?.status === 'deploying' || 
                            deploymentStatus?.status === 'building';
  const canCancel = isActiveDeployment && !cancelMutation.isPending;
  const canRollback = deploymentStatus?.rollback_available && !rollbackMutation.isPending;

  if (!deploymentStatus) {
    return (
      <div className="rounded-lg bg-white border shadow-sm p-6">
        <div className="text-center py-8">
          <GitBranch className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No deployment in progress
          </h3>
          <p className="text-gray-600">
            Start a new deployment to see the pipeline
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Deployment header */}
      <div className="rounded-lg bg-white border shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="flex items-center space-x-3">
              <h3 className="text-lg font-semibold text-gray-900">
                Deployment Pipeline
              </h3>
              <span className={`font-medium ${getOverallStatusColor()}`}>
                {deploymentStatus.status.replace('_', ' ').toUpperCase()}
              </span>
            </div>
            <div className="flex items-center space-x-4 mt-2 text-sm text-gray-600">
              <span>ID: {deploymentStatus.deployment_id}</span>
              <span>Environment: {deploymentStatus.environment}</span>
              {deploymentStatus.version && (
                <span>Version: v{deploymentStatus.version}</span>
              )}
              {deploymentStatus.commit_hash && (
                <span>Commit: {deploymentStatus.commit_hash.substring(0, 8)}</span>
              )}
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {/* Progress indicator */}
            {isActiveDeployment && (
              <div className="flex items-center space-x-2">
                <div className="w-32 bg-gray-200 rounded-full h-2">
                  <motion.div
                    className="bg-blue-600 h-2 rounded-full"
                    initial={{ width: 0 }}
                    animate={{ width: `${deploymentStatus.progress}%` }}
                    transition={{ duration: 0.5 }}
                  />
                </div>
                <span className="text-sm font-medium text-gray-700">
                  {deploymentStatus.progress}%
                </span>
              </div>
            )}

            {/* Action buttons */}
            <div className="flex items-center space-x-2">
              {canCancel && (
                <button
                  onClick={() => cancelMutation.mutate()}
                  disabled={cancelMutation.isPending}
                  className="flex items-center space-x-1 rounded-md bg-red-600 px-3 py-1 text-sm text-white hover:bg-red-700 disabled:opacity-50"
                >
                  {cancelMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Pause className="h-4 w-4" />
                  )}
                  <span>Cancel</span>
                </button>
              )}

              {canRollback && (
                <button
                  onClick={() => rollbackMutation.mutate()}
                  disabled={rollbackMutation.isPending}
                  className="flex items-center space-x-1 rounded-md bg-orange-600 px-3 py-1 text-sm text-white hover:bg-orange-700 disabled:opacity-50"
                >
                  {rollbackMutation.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <RotateCcw className="h-4 w-4" />
                  )}
                  <span>Rollback</span>
                </button>
              )}

              <button
                onClick={() => setShowLogs(!showLogs)}
                className="flex items-center space-x-1 rounded-md bg-gray-600 px-3 py-1 text-sm text-white hover:bg-gray-700"
              >
                <Eye className="h-4 w-4" />
                <span>{showLogs ? 'Hide' : 'Show'} Logs</span>
              </button>
            </div>
          </div>
        </div>

        {/* Deployment timeline */}
        <div className="flex items-center space-x-2 text-sm text-gray-600">
          <span>Started: {format(new Date(deploymentStatus.start_time), 'MMM dd, HH:mm')}</span>
          <span>•</span>
          <span>
            Duration:{' '}
            {deploymentStatus.end_time
              ? formatDistanceToNow(new Date(deploymentStatus.start_time), { addSuffix: false })
              : 'In progress'
            }
          </span>
          {deploymentStatus.end_time && (
            <>
              <span>•</span>
              <span>Ended: {format(new Date(deploymentStatus.end_time), 'MMM dd, HH:mm')}</span>
            </>
          )}
        </div>
      </div>

      {/* Pipeline steps */}
      <div className="rounded-lg bg-white border shadow-sm p-6">
        <h4 className="text-md font-semibold text-gray-900 mb-4">Pipeline Steps</h4>
        
        <div className="space-y-4">
          {deploymentStatus.steps.map((step, index) => (
            <motion.div
              key={`${step.name}-${index}`}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className={`relative rounded-lg border p-4 transition-all cursor-pointer hover:shadow-md ${getStepColor(step)}`}
              onClick={() => setSelectedStep(step)}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  {getStepIcon(step)}
                  <div>
                    <h5 className="font-medium text-gray-900">{step.name}</h5>
                    {step.duration && (
                      <p className="text-sm text-gray-600">
                        {Math.round(step.duration / 1000)}s
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  {step.status === 'running' && step.start_time && (
                    <span className="text-sm text-gray-600">
                      Running for {formatDistanceToNow(new Date(step.start_time))}
                    </span>
                  )}
                  
                  {step.error_message && (
                    <span className="text-sm text-red-600 truncate max-w-xs">
                      {step.error_message}
                    </span>
                  )}

                  {step.logs.length > 0 && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedStep(step);
                        setShowLogs(true);
                      }}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      <Eye className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>

              {/* Step progress bar for running steps */}
              {step.status === 'running' && (
                <div className="mt-3">
                  <div className="w-full bg-gray-200 rounded-full h-1">
                    <motion.div
                      className="bg-blue-600 h-1 rounded-full"
                      initial={{ width: 0 }}
                      animate={{ width: '70%' }}
                      transition={{ 
                        duration: 2,
                        repeat: Infinity,
                        repeatType: 'reverse'
                      }}
                    />
                  </div>
                </div>
              )}

              {/* Step connector line */}
              {index < deploymentStatus.steps.length - 1 && (
                <div className="absolute left-[22px] top-full h-4 w-0.5 bg-gray-300" />
              )}
            </motion.div>
          ))}
        </div>
      </div>

      {/* Logs panel */}
      {showLogs && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="rounded-lg bg-white border shadow-sm"
        >
          <div className="flex items-center justify-between border-b border-gray-200 p-4">
            <h4 className="text-md font-semibold text-gray-900">
              {selectedStep ? `${selectedStep.name} Logs` : 'Deployment Logs'}
            </h4>
            <div className="flex items-center space-x-2">
              {stepLogs && (
                <button
                  onClick={() => {
                    const logs = selectedStep?.logs || deploymentStatus.logs;
                    const blob = new Blob([logs.join('\n')], { type: 'text/plain' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `deployment-logs-${deploymentStatus.deployment_id}.txt`;
                    a.click();
                    URL.revokeObjectURL(url);
                  }}
                  className="text-blue-600 hover:text-blue-800"
                >
                  <Download className="h-4 w-4" />
                </button>
              )}
              <button
                onClick={() => setShowLogs(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                ×
              </button>
            </div>
          </div>
          
          <div className="p-4">
            <div className="bg-black rounded-md p-4 max-h-96 overflow-y-auto">
              <pre className="text-sm text-green-400 font-mono whitespace-pre-wrap">
                {(selectedStep?.logs || deploymentStatus.logs || []).map((log, index) => (
                  <div key={index} className="mb-1">
                    {log}
                  </div>
                ))}
                {(!selectedStep?.logs?.length && !deploymentStatus.logs?.length) && (
                  <div className="text-gray-500">No logs available</div>
                )}
              </pre>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
}