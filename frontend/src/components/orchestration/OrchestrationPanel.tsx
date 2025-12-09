/**
 * OrchestrationPanel - Main project orchestration control panel
 * Displays all projects with their status and provides launch/stop controls
 */

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Play, 
  Square, 
  RotateCcw, 
  Settings,
  Activity,
  Zap,
  AlertTriangle,
  CheckCircle,
  Loader2
} from 'lucide-react';
import { ProjectCard } from './ProjectCard';
import { EnvironmentSwitcher } from './EnvironmentSwitcher';
import { useOrchestrationStatus, useOrchestrationWebSocket, useResourceManager } from '../../hooks/useOrchestration';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import type { Project, OrchestrationStatus } from '../../types/api';

export function OrchestrationPanel() {
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  // Initialize WebSocket connection for real-time updates
  useOrchestrationWebSocket();

  // Get all projects
  const { data: projects, isLoading: projectsLoading } = useQuery<Project[]>({
    queryKey: ['projects'],
    queryFn: async () => {
      const response = await api.get('/api/projects');
      return response.data.projects || [];
    },
  });

  // Get orchestration status for all projects
  const { status: orchestrationStatuses, isLoading: statusLoading, refresh: refreshStatus } = useOrchestrationStatus();

  // Get system resource summary
  const { systemSummary, isLoading: resourcesLoading } = useResourceManager();

  const isLoading = projectsLoading || statusLoading || resourcesLoading;

  // Combine project data with orchestration status
  const projectsWithStatus = React.useMemo(() => {
    if (!projects || !orchestrationStatuses) return [];
    
    const statusMap = new Map();
    if (Array.isArray(orchestrationStatuses)) {
      orchestrationStatuses.forEach(status => {
        statusMap.set(status.project_id, status);
      });
    }

    return projects.map(project => ({
      ...project,
      orchestrationStatus: statusMap.get(project.id) as OrchestrationStatus | undefined,
    }));
  }, [projects, orchestrationStatuses]);

  // Calculate summary stats
  const summaryStats = React.useMemo(() => {
    const total = projectsWithStatus.length;
    const running = projectsWithStatus.filter(p => p.orchestrationStatus?.is_running).length;
    const stopped = total - running;
    const withErrors = projectsWithStatus.filter(p => 
      p.orchestrationStatus?.status_details?.toLowerCase().includes('error')
    ).length;

    return { total, running, stopped, withErrors };
  }, [projectsWithStatus]);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
        <span className="ml-2 text-gray-600">Loading orchestration panel...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with stats */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Project Orchestration</h1>
          <p className="mt-2 text-gray-600">
            Manage project lifecycle, environments, and resources
          </p>
        </div>
        <button
          onClick={() => refreshStatus()}
          className="flex items-center space-x-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 transition-colors"
        >
          <RotateCcw className="h-4 w-4" />
          <span>Refresh</span>
        </button>
      </div>

      {/* System Summary Cards */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="rounded-lg bg-white p-6 shadow-md border"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Total Projects</p>
              <p className="text-3xl font-bold text-gray-900">{summaryStats.total}</p>
            </div>
            <Settings className="h-8 w-8 text-gray-400" />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="rounded-lg bg-white p-6 shadow-md border"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">Running Projects</p>
              <p className="text-3xl font-bold text-green-600">{summaryStats.running}</p>
            </div>
            <CheckCircle className="h-8 w-8 text-green-400" />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="rounded-lg bg-white p-6 shadow-md border"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">System CPU</p>
              <p className="text-3xl font-bold text-blue-600">
                {systemSummary?.total_cpu_usage?.toFixed(1) || '0'}%
              </p>
            </div>
            <Activity className="h-8 w-8 text-blue-400" />
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="rounded-lg bg-white p-6 shadow-md border"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600">System Memory</p>
              <p className="text-3xl font-bold text-purple-600">
                {systemSummary ? Math.round(systemSummary.total_memory_usage / 1024) : 0} GB
              </p>
            </div>
            <Zap className="h-8 w-8 text-purple-400" />
          </div>
        </motion.div>
      </div>

      {/* Alert for errors */}
      {summaryStats.withErrors > 0 && (
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-center space-x-3 rounded-lg bg-red-50 border border-red-200 p-4"
        >
          <AlertTriangle className="h-5 w-5 text-red-500" />
          <div>
            <p className="font-medium text-red-800">
              {summaryStats.withErrors} project{summaryStats.withErrors > 1 ? 's' : ''} with errors
            </p>
            <p className="text-sm text-red-600">
              Check project status and logs for details
            </p>
          </div>
        </motion.div>
      )}

      {/* View controls */}
      <div className="flex items-center justify-between border-b border-gray-200 pb-4">
        <h2 className="text-xl font-semibold text-gray-900">Projects</h2>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setViewMode('grid')}
            className={`rounded-md px-3 py-1 text-sm ${
              viewMode === 'grid' 
                ? 'bg-blue-100 text-blue-700' 
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Grid
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`rounded-md px-3 py-1 text-sm ${
              viewMode === 'list' 
                ? 'bg-blue-100 text-blue-700' 
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            List
          </button>
        </div>
      </div>

      {/* Projects Grid/List */}
      {projectsWithStatus.length === 0 ? (
        <div className="text-center py-12">
          <Settings className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No projects found</h3>
          <p className="text-gray-600">
            Run the project scanner to discover projects in your workspace
          </p>
        </div>
      ) : (
        <div className={
          viewMode === 'grid' 
            ? "grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3" 
            : "space-y-4"
        }>
          {projectsWithStatus.map((project, index) => (
            <motion.div
              key={project.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <ProjectCard
                project={project}
                orchestrationStatus={project.orchestrationStatus}
                isSelected={selectedProjectId === project.id}
                onSelect={() => setSelectedProjectId(project.id)}
                viewMode={viewMode}
              />
            </motion.div>
          ))}
        </div>
      )}

      {/* Environment Switcher Modal */}
      {selectedProjectId && (
        <EnvironmentSwitcher
          projectId={selectedProjectId}
          isOpen={true}
          onClose={() => setSelectedProjectId(null)}
        />
      )}
    </div>
  );
}