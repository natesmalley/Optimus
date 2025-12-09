/**
 * DeploymentHistory - Table view of deployment history
 * Shows past deployments with filtering and comparison features
 */

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  CheckCircle, 
  AlertTriangle, 
  Clock,
  Loader2,
  GitBranch,
  Calendar,
  Filter,
  Compare,
  RotateCcw,
  ExternalLink,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { deploymentService } from '../../services/deploymentService';
import { formatDistanceToNow, format } from 'date-fns';
import type { DeploymentStatus } from '../../types/api';

interface DeploymentHistoryProps {
  projectId: string;
  deployments?: DeploymentStatus[];
  isLoading?: boolean;
  showFilters?: boolean;
}

export function DeploymentHistory({ 
  projectId, 
  deployments = [], 
  isLoading = false,
  showFilters = false 
}: DeploymentHistoryProps) {
  const [sortField, setSortField] = useState<'start_time' | 'status' | 'environment' | 'duration'>('start_time');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterEnvironment, setFilterEnvironment] = useState<string>('all');
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [compareMode, setCompareMode] = useState(false);
  const [selectedDeployments, setSelectedDeployments] = useState<Set<string>>(new Set());

  const queryClient = useQueryClient();

  // Rollback mutation
  const rollbackMutation = useMutation({
    mutationFn: (targetDeploymentId: string) => 
      deploymentService.rollback(projectId, targetDeploymentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deployment', projectId] });
      queryClient.invalidateQueries({ queryKey: ['deployment', 'history', projectId] });
    },
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success': return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'failed': return <AlertTriangle className="h-4 w-4 text-red-600" />;
      case 'deploying':
      case 'building': return <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />;
      case 'pending': return <Clock className="h-4 w-4 text-yellow-600" />;
      case 'rolling_back': return <RotateCcw className="h-4 w-4 text-orange-600" />;
      default: return <div className="h-4 w-4 rounded-full bg-gray-300" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return 'text-green-600 bg-green-50 border-green-200';
      case 'failed': return 'text-red-600 bg-red-50 border-red-200';
      case 'deploying':
      case 'building': return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'pending': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'rolling_back': return 'text-orange-600 bg-orange-50 border-orange-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getDuration = (deployment: DeploymentStatus) => {
    if (!deployment.end_time) return 'In progress';
    const start = new Date(deployment.start_time);
    const end = new Date(deployment.end_time);
    const durationMs = end.getTime() - start.getTime();
    return `${Math.round(durationMs / 1000)}s`;
  };

  const filteredAndSortedDeployments = React.useMemo(() => {
    let filtered = deployments;

    // Apply filters
    if (filterStatus !== 'all') {
      filtered = filtered.filter(d => d.status === filterStatus);
    }
    if (filterEnvironment !== 'all') {
      filtered = filtered.filter(d => d.environment === filterEnvironment);
    }

    // Apply sorting
    return [...filtered].sort((a, b) => {
      let aValue: any, bValue: any;

      switch (sortField) {
        case 'start_time':
          aValue = new Date(a.start_time);
          bValue = new Date(b.start_time);
          break;
        case 'status':
          aValue = a.status;
          bValue = b.status;
          break;
        case 'environment':
          aValue = a.environment;
          bValue = b.environment;
          break;
        case 'duration':
          aValue = a.end_time ? new Date(a.end_time).getTime() - new Date(a.start_time).getTime() : 0;
          bValue = b.end_time ? new Date(b.end_time).getTime() - new Date(b.start_time).getTime() : 0;
          break;
        default:
          return 0;
      }

      if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }, [deployments, filterStatus, filterEnvironment, sortField, sortDirection]);

  const toggleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const toggleExpanded = (deploymentId: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(deploymentId)) {
      newExpanded.delete(deploymentId);
    } else {
      newExpanded.add(deploymentId);
    }
    setExpandedRows(newExpanded);
  };

  const toggleCompareSelection = (deploymentId: string) => {
    const newSelected = new Set(selectedDeployments);
    if (newSelected.has(deploymentId)) {
      newSelected.delete(deploymentId);
    } else if (newSelected.size < 2) {
      newSelected.add(deploymentId);
    }
    setSelectedDeployments(newSelected);
  };

  const uniqueStatuses = Array.from(new Set(deployments.map(d => d.status)));
  const uniqueEnvironments = Array.from(new Set(deployments.map(d => d.environment)));

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
        <span className="ml-2 text-gray-600">Loading deployment history...</span>
      </div>
    );
  }

  if (deployments.length === 0) {
    return (
      <div className="text-center py-8">
        <GitBranch className="h-12 w-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          No deployment history
        </h3>
        <p className="text-gray-600">
          Start your first deployment to see history here
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters and controls */}
      {showFilters && (
        <div className="flex items-center justify-between bg-white rounded-lg border p-4">
          <div className="flex items-center space-x-4">
            <Filter className="h-5 w-5 text-gray-400" />
            
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="rounded-md border border-gray-300 px-3 py-1 text-sm focus:border-blue-500 focus:ring-blue-500"
            >
              <option value="all">All Statuses</option>
              {uniqueStatuses.map(status => (
                <option key={status} value={status}>
                  {status.replace('_', ' ').toUpperCase()}
                </option>
              ))}
            </select>

            <select
              value={filterEnvironment}
              onChange={(e) => setFilterEnvironment(e.target.value)}
              className="rounded-md border border-gray-300 px-3 py-1 text-sm focus:border-blue-500 focus:ring-blue-500"
            >
              <option value="all">All Environments</option>
              {uniqueEnvironments.map(env => (
                <option key={env} value={env}>
                  {env.toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setCompareMode(!compareMode)}
              className={`flex items-center space-x-1 rounded-md px-3 py-1 text-sm ${
                compareMode
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <Compare className="h-4 w-4" />
              <span>Compare</span>
            </button>

            <span className="text-sm text-gray-600">
              {filteredAndSortedDeployments.length} deployments
            </span>
          </div>
        </div>
      )}

      {/* Deployment table */}
      <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                {compareMode && (
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Compare
                  </th>
                )}
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th 
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => toggleSort('environment')}
                >
                  <div className="flex items-center space-x-1">
                    <span>Environment</span>
                    {sortField === 'environment' && (
                      sortDirection === 'asc' ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />
                    )}
                  </div>
                </th>
                <th 
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => toggleSort('start_time')}
                >
                  <div className="flex items-center space-x-1">
                    <span>Started</span>
                    {sortField === 'start_time' && (
                      sortDirection === 'asc' ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />
                    )}
                  </div>
                </th>
                <th 
                  className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  onClick={() => toggleSort('duration')}
                >
                  <div className="flex items-center space-x-1">
                    <span>Duration</span>
                    {sortField === 'duration' && (
                      sortDirection === 'asc' ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />
                    )}
                  </div>
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Version
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Details
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredAndSortedDeployments.map((deployment, index) => (
                <React.Fragment key={deployment.deployment_id}>
                  <motion.tr
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="hover:bg-gray-50"
                  >
                    {compareMode && (
                      <td className="px-6 py-4 whitespace-nowrap">
                        <input
                          type="checkbox"
                          checked={selectedDeployments.has(deployment.deployment_id)}
                          onChange={() => toggleCompareSelection(deployment.deployment_id)}
                          disabled={!selectedDeployments.has(deployment.deployment_id) && selectedDeployments.size >= 2}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                      </td>
                    )}
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className={`inline-flex items-center space-x-2 rounded-full border px-2.5 py-1.5 text-xs font-medium ${getStatusColor(deployment.status)}`}>
                        {getStatusIcon(deployment.status)}
                        <span>{deployment.status.replace('_', ' ').toUpperCase()}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="font-medium text-gray-900 capitalize">
                        {deployment.environment}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      <div className="flex items-center space-x-1">
                        <Calendar className="h-4 w-4" />
                        <span>{format(new Date(deployment.start_time), 'MMM dd, HH:mm')}</span>
                      </div>
                      <div className="text-xs text-gray-500">
                        {formatDistanceToNow(new Date(deployment.start_time))} ago
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {getDuration(deployment)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      {deployment.version ? (
                        <span className="font-mono">v{deployment.version}</span>
                      ) : deployment.commit_hash ? (
                        <span className="font-mono">{deployment.commit_hash.substring(0, 8)}</span>
                      ) : (
                        '-'
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      <div className="flex items-center space-x-2">
                        {deployment.rollback_available && deployment.status === 'success' && (
                          <button
                            onClick={() => rollbackMutation.mutate(deployment.deployment_id)}
                            disabled={rollbackMutation.isPending}
                            className="text-orange-600 hover:text-orange-800"
                          >
                            <RotateCcw className="h-4 w-4" />
                          </button>
                        )}
                        
                        <a
                          href={`/deployments/${deployment.deployment_id}`}
                          className="text-blue-600 hover:text-blue-800"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                      <button
                        onClick={() => toggleExpanded(deployment.deployment_id)}
                        className="text-gray-400 hover:text-gray-600"
                      >
                        {expandedRows.has(deployment.deployment_id) ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </button>
                    </td>
                  </motion.tr>

                  {/* Expanded row details */}
                  {expandedRows.has(deployment.deployment_id) && (
                    <tr>
                      <td colSpan={compareMode ? 8 : 7} className="px-6 py-4 bg-gray-50">
                        <div className="space-y-3">
                          <div className="grid grid-cols-2 gap-4 text-sm">
                            <div>
                              <strong>Deployment ID:</strong> {deployment.deployment_id}
                            </div>
                            <div>
                              <strong>Progress:</strong> {deployment.progress}%
                            </div>
                            {deployment.commit_hash && (
                              <div>
                                <strong>Commit:</strong>{' '}
                                <span className="font-mono">{deployment.commit_hash}</span>
                              </div>
                            )}
                            {deployment.end_time && (
                              <div>
                                <strong>Completed:</strong>{' '}
                                {format(new Date(deployment.end_time), 'MMM dd, yyyy HH:mm')}
                              </div>
                            )}
                          </div>

                          {/* Steps summary */}
                          {deployment.steps && deployment.steps.length > 0 && (
                            <div>
                              <strong className="text-sm">Steps:</strong>
                              <div className="mt-2 flex flex-wrap gap-2">
                                {deployment.steps.map((step, stepIndex) => (
                                  <div
                                    key={stepIndex}
                                    className={`inline-flex items-center space-x-1 rounded px-2 py-1 text-xs ${getStatusColor(step.status)}`}
                                  >
                                    {getStatusIcon(step.status)}
                                    <span>{step.name}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Recent logs preview */}
                          {deployment.logs && deployment.logs.length > 0 && (
                            <div>
                              <strong className="text-sm">Recent Logs:</strong>
                              <div className="mt-2 bg-black rounded p-3 max-h-32 overflow-y-auto">
                                <pre className="text-xs text-green-400 font-mono">
                                  {deployment.logs.slice(-10).join('\n')}
                                </pre>
                              </div>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Compare selected deployments */}
      {compareMode && selectedDeployments.size === 2 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Compare className="h-5 w-5 text-blue-600" />
              <span className="font-medium text-blue-800">
                2 deployments selected for comparison
              </span>
            </div>
            <button
              onClick={() => {
                const deploymentIds = Array.from(selectedDeployments);
                // Here you would implement the comparison logic
                console.log('Compare deployments:', deploymentIds);
              }}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
            >
              Compare Deployments
            </button>
          </div>
        </div>
      )}
    </div>
  );
}