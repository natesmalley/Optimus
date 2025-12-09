/**
 * DeploymentDashboard - Main deployment management interface
 * Shows deployment pipeline, current status, and deployment history
 */

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Rocket, 
  History,
  Play,
  RotateCcw,
  Settings,
  AlertTriangle,
  CheckCircle,
  Clock,
  Loader2,
  GitBranch,
  Package
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { DeploymentPipeline } from './DeploymentPipeline';
import { DeploymentHistory } from './DeploymentHistory';
import { deploymentService } from '../../services/deploymentService';
import { api } from '../../lib/api';
import type { Project, DeploymentStatus } from '../../types/api';

interface DeploymentDashboardProps {
  projectId?: string;
}

export function DeploymentDashboard({ projectId }: DeploymentDashboardProps) {
  const [selectedProject, setSelectedProject] = useState<string>(projectId || '');
  const [activeTab, setActiveTab] = useState<'overview' | 'pipeline' | 'history'>('overview');
  const [showNewDeployment, setShowNewDeployment] = useState(false);

  // Get all projects for selection
  const { data: projects } = useQuery<Project[]>({
    queryKey: ['projects'],
    queryFn: async () => {
      const response = await api.get('/api/projects');
      return response.data.projects || [];
    },
  });

  // Get deployment status for selected project
  const { data: deploymentStatus, isLoading: statusLoading } = useQuery({
    queryKey: ['deployment', selectedProject],
    queryFn: () => deploymentService.getDeploymentStatus(selectedProject),
    enabled: !!selectedProject,
    refetchInterval: 5000, // Poll every 5 seconds for active deployments
  });

  // Get deployment history
  const { data: deploymentHistory, isLoading: historyLoading } = useQuery({
    queryKey: ['deployment', 'history', selectedProject],
    queryFn: () => deploymentService.getDeploymentHistory(selectedProject, 10),
    enabled: !!selectedProject,
  });

  // Get deployment environments
  const { data: environments } = useQuery({
    queryKey: ['deployment', 'environments', selectedProject],
    queryFn: () => deploymentService.getDeploymentEnvironments(selectedProject),
    enabled: !!selectedProject,
  });

  // Get deployment metrics
  const { data: metrics } = useQuery({
    queryKey: ['deployment', 'metrics', selectedProject],
    queryFn: () => deploymentService.getDeploymentMetrics(selectedProject, '30d'),
    enabled: !!selectedProject,
  });

  const selectedProjectData = projects?.find(p => p.id === selectedProject);
  const isActiveDeployment = deploymentStatus?.status === 'deploying' || 
                            deploymentStatus?.status === 'building';

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return 'text-green-600';
      case 'failed': return 'text-red-600';
      case 'deploying':
      case 'building': return 'text-blue-600';
      case 'pending': return 'text-yellow-600';
      case 'rolling_back': return 'text-orange-600';
      default: return 'text-gray-600';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success': return <CheckCircle className="h-5 w-5 text-green-600" />;
      case 'failed': return <AlertTriangle className="h-5 w-5 text-red-600" />;
      case 'deploying':
      case 'building': return <Loader2 className="h-5 w-5 text-blue-600 animate-spin" />;
      case 'pending': return <Clock className="h-5 w-5 text-yellow-600" />;
      case 'rolling_back': return <RotateCcw className="h-5 w-5 text-orange-600" />;
      default: return <Package className="h-5 w-5 text-gray-600" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Deployment Dashboard</h1>
          <p className="mt-2 text-gray-600">
            Manage deployments across environments
          </p>
        </div>
        
        <div className="flex items-center space-x-4">
          {/* Project selector */}
          <select
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-blue-500"
          >
            <option value="">Select project...</option>
            {projects?.map(project => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>

          {selectedProject && (
            <button
              onClick={() => setShowNewDeployment(true)}
              className="flex items-center space-x-2 rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
            >
              <Rocket className="h-4 w-4" />
              <span>New Deployment</span>
            </button>
          )}
        </div>
      </div>

      {!selectedProject ? (
        <div className="text-center py-12">
          <Rocket className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Select a project to view deployments
          </h3>
          <p className="text-gray-600">
            Choose a project from the dropdown above to manage its deployments
          </p>
        </div>
      ) : (
        <>
          {/* Project info bar */}
          <div className="rounded-lg bg-white border p-4 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div>
                  <h3 className="font-semibold text-gray-900">
                    {selectedProjectData?.name}
                  </h3>
                  <p className="text-sm text-gray-600">
                    {selectedProjectData?.path}
                  </p>
                </div>
                {selectedProjectData?.git_url && (
                  <div className="flex items-center space-x-1 text-sm text-gray-500">
                    <GitBranch className="h-4 w-4" />
                    <span>{selectedProjectData.default_branch}</span>
                  </div>
                )}
              </div>

              {deploymentStatus && (
                <div className="flex items-center space-x-2">
                  {getStatusIcon(deploymentStatus.status)}
                  <span className={`font-medium ${getStatusColor(deploymentStatus.status)}`}>
                    {deploymentStatus.status.replace('_', ' ').toUpperCase()}
                  </span>
                  {isActiveDeployment && (
                    <span className="text-sm text-gray-600">
                      {deploymentStatus.progress}%
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Metrics cards */}
          {metrics && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="rounded-lg bg-white p-4 shadow-md border"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Total Deployments</p>
                    <p className="text-2xl font-bold text-gray-900">
                      {metrics.total_deployments}
                    </p>
                  </div>
                  <Rocket className="h-6 w-6 text-blue-500" />
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="rounded-lg bg-white p-4 shadow-md border"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Success Rate</p>
                    <p className="text-2xl font-bold text-green-600">
                      {(metrics.success_rate * 100).toFixed(1)}%
                    </p>
                  </div>
                  <CheckCircle className="h-6 w-6 text-green-500" />
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="rounded-lg bg-white p-4 shadow-md border"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Avg Duration</p>
                    <p className="text-2xl font-bold text-purple-600">
                      {Math.round(metrics.average_duration / 60)}m
                    </p>
                  </div>
                  <Clock className="h-6 w-6 text-purple-500" />
                </div>
              </motion.div>

              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="rounded-lg bg-white p-4 shadow-md border"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Environments</p>
                    <p className="text-2xl font-bold text-orange-600">
                      {environments?.length || 0}
                    </p>
                  </div>
                  <Settings className="h-6 w-6 text-orange-500" />
                </div>
              </motion.div>
            </div>
          )}

          {/* Environment status */}
          {environments && environments.length > 0 && (
            <div className="rounded-lg bg-white border shadow-sm">
              <div className="border-b border-gray-200 p-4">
                <h3 className="font-semibold text-gray-900">Environment Status</h3>
              </div>
              <div className="p-4">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                  {environments.map((env) => (
                    <div
                      key={env.name}
                      className="flex items-center justify-between rounded-md border p-3"
                    >
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="font-medium capitalize">{env.name}</span>
                          {env.is_production && (
                            <span className="rounded-full bg-red-100 px-2 py-1 text-xs font-medium text-red-800">
                              PROD
                            </span>
                          )}
                        </div>
                        {env.version && (
                          <p className="text-sm text-gray-600">v{env.version}</p>
                        )}
                        {env.last_deployed && (
                          <p className="text-xs text-gray-500">
                            {new Date(env.last_deployed).toLocaleDateString()}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center space-x-1">
                        {env.status === 'active' && (
                          <CheckCircle className="h-4 w-4 text-green-500" />
                        )}
                        {env.status === 'deploying' && (
                          <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
                        )}
                        {env.status === 'error' && (
                          <AlertTriangle className="h-4 w-4 text-red-500" />
                        )}
                        {env.status === 'inactive' && (
                          <div className="h-4 w-4 rounded-full bg-gray-300" />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Tabs */}
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              {[
                { id: 'overview', label: 'Overview', icon: Rocket },
                { id: 'pipeline', label: 'Pipeline', icon: GitBranch },
                { id: 'history', label: 'History', icon: History },
              ].map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setActiveTab(id as any)}
                  className={`flex items-center space-x-2 border-b-2 py-2 px-1 text-sm font-medium ${
                    activeTab === id
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  <span>{label}</span>
                </button>
              ))}
            </nav>
          </div>

          {/* Tab content */}
          <div className="mt-6">
            {activeTab === 'overview' && deploymentStatus && (
              <div className="space-y-6">
                <DeploymentPipeline 
                  projectId={selectedProject}
                  deploymentStatus={deploymentStatus}
                />
                
                {deploymentHistory && deploymentHistory.length > 0 && (
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 mb-4">
                      Recent Deployments
                    </h3>
                    <DeploymentHistory 
                      projectId={selectedProject}
                      deployments={deploymentHistory.slice(0, 5)}
                      isLoading={historyLoading}
                    />
                  </div>
                )}
              </div>
            )}

            {activeTab === 'pipeline' && (
              <DeploymentPipeline 
                projectId={selectedProject}
                deploymentStatus={deploymentStatus}
                showFullPipeline={true}
              />
            )}

            {activeTab === 'history' && (
              <DeploymentHistory 
                projectId={selectedProject}
                deployments={deploymentHistory}
                isLoading={historyLoading}
                showFilters={true}
              />
            )}
          </div>
        </>
      )}
    </div>
  );
}