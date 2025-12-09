/**
 * BackupManager - Comprehensive backup management interface
 * Handles backup creation, scheduling, restoration, and management
 */

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Archive, 
  Calendar,
  History,
  Plus,
  Play,
  Download,
  Trash2,
  Settings,
  Clock,
  CheckCircle,
  AlertTriangle,
  Loader2,
  HardDrive,
  RotateCcw
} from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { BackupScheduler } from './BackupScheduler';
import { BackupHistory } from './BackupHistory';
import { backupService } from '../../services/backupService';
import { api } from '../../lib/api';
import { formatDistanceToNow, formatBytes } from 'date-fns';
import type { Project, BackupInfo, BackupSchedule } from '../../types/api';

interface BackupManagerProps {
  projectId?: string;
}

export function BackupManager({ projectId }: BackupManagerProps) {
  const [selectedProject, setSelectedProject] = useState<string>(projectId || '');
  const [activeTab, setActiveTab] = useState<'overview' | 'schedules' | 'history'>('overview');
  const [showScheduler, setShowScheduler] = useState(false);
  const [showCreateBackup, setShowCreateBackup] = useState(false);
  const [selectedBackup, setSelectedBackup] = useState<BackupInfo | null>(null);

  const queryClient = useQueryClient();

  // Get all projects
  const { data: projects } = useQuery<Project[]>({
    queryKey: ['projects'],
    queryFn: async () => {
      const response = await api.get('/api/projects');
      return response.data.projects || [];
    },
  });

  // Get backups for selected project
  const { data: backupData, isLoading: backupsLoading } = useQuery({
    queryKey: ['backup', selectedProject],
    queryFn: () => backupService.getBackups(selectedProject),
    enabled: !!selectedProject,
  });

  // Get backup schedules
  const { data: schedules, isLoading: schedulesLoading } = useQuery({
    queryKey: ['backup', 'schedules', selectedProject],
    queryFn: () => backupService.getSchedules(selectedProject),
    enabled: !!selectedProject,
  });

  // Get backup statistics
  const { data: stats } = useQuery({
    queryKey: ['backup', 'stats', selectedProject],
    queryFn: () => backupService.getBackupStats(selectedProject),
    enabled: !!selectedProject,
  });

  // Get system backup summary
  const { data: systemSummary } = useQuery({
    queryKey: ['backup', 'system-summary'],
    queryFn: () => backupService.getSystemBackupSummary(),
  });

  // Create manual backup mutation
  const createBackupMutation = useMutation({
    mutationFn: (request: any) => backupService.createBackup(selectedProject, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backup', selectedProject] });
      queryClient.invalidateQueries({ queryKey: ['backup', 'stats', selectedProject] });
      setShowCreateBackup(false);
    },
  });

  // Delete backup mutation
  const deleteBackupMutation = useMutation({
    mutationFn: (backupId: string) => backupService.deleteBackup(selectedProject, backupId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backup', selectedProject] });
      queryClient.invalidateQueries({ queryKey: ['backup', 'stats', selectedProject] });
    },
  });

  // Restore backup mutation
  const restoreBackupMutation = useMutation({
    mutationFn: ({ backupId, options }: { backupId: string; options: any }) => 
      backupService.restoreBackup(selectedProject, backupId, options),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backup', selectedProject] });
    },
  });

  const selectedProjectData = projects?.find(p => p.id === selectedProject);
  const backups = backupData?.backups || [];

  const getBackupStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'creating': return <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />;
      case 'failed': return <AlertTriangle className="h-4 w-4 text-red-600" />;
      case 'expired': return <Clock className="h-4 w-4 text-gray-400" />;
      default: return <Archive className="h-4 w-4 text-gray-600" />;
    }
  };

  const getBackupStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600 bg-green-50 border-green-200';
      case 'creating': return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'failed': return 'text-red-600 bg-red-50 border-red-200';
      case 'expired': return 'text-gray-600 bg-gray-50 border-gray-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const handleCreateManualBackup = () => {
    const name = `Manual backup - ${new Date().toLocaleDateString()}`;
    createBackupMutation.mutate({
      name,
      retention_days: 30,
    });
  };

  const handleRestoreBackup = (backup: BackupInfo) => {
    if (window.confirm(`Are you sure you want to restore from backup "${backup.name}"? This will replace current project files.`)) {
      restoreBackupMutation.mutate({
        backupId: backup.id,
        options: {
          create_backup_before_restore: true,
        },
      });
    }
  };

  const handleDeleteBackup = (backup: BackupInfo) => {
    if (window.confirm(`Are you sure you want to delete backup "${backup.name}"? This cannot be undone.`)) {
      deleteBackupMutation.mutate(backup.id);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Backup Manager</h1>
          <p className="mt-2 text-gray-600">
            Manage project backups and restore points
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
            <>
              <button
                onClick={() => setShowScheduler(true)}
                className="flex items-center space-x-2 rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
              >
                <Calendar className="h-4 w-4" />
                <span>Schedule</span>
              </button>

              <button
                onClick={handleCreateManualBackup}
                disabled={createBackupMutation.isPending}
                className="flex items-center space-x-2 rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {createBackupMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="h-4 w-4" />
                )}
                <span>Create Backup</span>
              </button>
            </>
          )}
        </div>
      </div>

      {/* System summary cards */}
      {systemSummary && (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-lg bg-white p-6 shadow-md border"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Total Projects</p>
                <p className="text-3xl font-bold text-gray-900">
                  {systemSummary.total_projects_with_backups}
                </p>
              </div>
              <Archive className="h-8 w-8 text-gray-400" />
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
                <p className="text-sm text-gray-600">Total Backups</p>
                <p className="text-3xl font-bold text-blue-600">
                  {systemSummary.total_backups}
                </p>
              </div>
              <CheckCircle className="h-8 w-8 text-blue-400" />
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
                <p className="text-sm text-gray-600">Storage Used</p>
                <p className="text-3xl font-bold text-purple-600">
                  {systemSummary.total_size_gb.toFixed(1)} GB
                </p>
              </div>
              <HardDrive className="h-8 w-8 text-purple-400" />
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
                <p className="text-sm text-gray-600">Active Schedules</p>
                <p className="text-3xl font-bold text-green-600">
                  {systemSummary.active_schedules}
                </p>
              </div>
              <Calendar className="h-8 w-8 text-green-400" />
            </div>
          </motion.div>
        </div>
      )}

      {!selectedProject ? (
        <div className="text-center py-12">
          <Archive className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Select a project to manage backups
          </h3>
          <p className="text-gray-600">
            Choose a project from the dropdown above to view and manage its backups
          </p>
        </div>
      ) : (
        <>
          {/* Project stats */}
          {stats && (
            <div className="rounded-lg bg-white border shadow-sm p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Project Backup Statistics
              </h3>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div className="text-center">
                  <p className="text-2xl font-bold text-blue-600">{stats.total_backups}</p>
                  <p className="text-sm text-gray-600">Total Backups</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-green-600">
                    {(stats.total_size_mb / 1024).toFixed(1)} GB
                  </p>
                  <p className="text-sm text-gray-600">Storage Used</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-purple-600">
                    {Math.round(stats.success_rate * 100)}%
                  </p>
                  <p className="text-sm text-gray-600">Success Rate</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-orange-600">
                    {stats.schedule_summary.enabled_schedules}
                  </p>
                  <p className="text-sm text-gray-600">Active Schedules</p>
                </div>
              </div>
            </div>
          )}

          {/* Tabs */}
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              {[
                { id: 'overview', label: 'Overview', icon: Archive },
                { id: 'schedules', label: 'Schedules', icon: Calendar },
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
            {activeTab === 'overview' && (
              <div className="space-y-6">
                {/* Recent backups */}
                <div className="rounded-lg bg-white border shadow-sm">
                  <div className="border-b border-gray-200 p-6">
                    <h3 className="text-lg font-semibold text-gray-900">
                      Recent Backups
                    </h3>
                  </div>
                  <div className="p-6">
                    {backupsLoading ? (
                      <div className="flex items-center justify-center py-8">
                        <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                        <span className="ml-2 text-gray-600">Loading backups...</span>
                      </div>
                    ) : backups.length === 0 ? (
                      <div className="text-center py-8">
                        <Archive className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                        <h3 className="text-lg font-medium text-gray-900 mb-2">
                          No backups found
                        </h3>
                        <p className="text-gray-600 mb-4">
                          Create your first backup to protect your project
                        </p>
                        <button
                          onClick={handleCreateManualBackup}
                          disabled={createBackupMutation.isPending}
                          className="flex items-center space-x-2 rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
                        >
                          <Plus className="h-4 w-4" />
                          <span>Create First Backup</span>
                        </button>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {backups.slice(0, 5).map((backup, index) => (
                          <motion.div
                            key={backup.id}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.1 }}
                            className="flex items-center justify-between p-4 rounded-lg border hover:bg-gray-50"
                          >
                            <div className="flex items-center space-x-4">
                              {getBackupStatusIcon(backup.status)}
                              <div>
                                <h4 className="font-medium text-gray-900">{backup.name}</h4>
                                <div className="flex items-center space-x-4 text-sm text-gray-600">
                                  <span>{(backup.size_mb / 1024).toFixed(1)} GB</span>
                                  <span>{formatDistanceToNow(new Date(backup.created_at))} ago</span>
                                  <span className="capitalize">{backup.type} backup</span>
                                </div>
                              </div>
                            </div>

                            <div className="flex items-center space-x-2">
                              <div className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium ${getBackupStatusColor(backup.status)}`}>
                                {backup.status.toUpperCase()}
                              </div>

                              {backup.can_restore && backup.status === 'completed' && (
                                <button
                                  onClick={() => handleRestoreBackup(backup)}
                                  disabled={restoreBackupMutation.isPending}
                                  className="text-blue-600 hover:text-blue-800 p-1"
                                  title="Restore backup"
                                >
                                  <RotateCcw className="h-4 w-4" />
                                </button>
                              )}

                              <button
                                onClick={() => handleDeleteBackup(backup)}
                                disabled={deleteBackupMutation.isPending}
                                className="text-red-600 hover:text-red-800 p-1"
                                title="Delete backup"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </div>
                          </motion.div>
                        ))}

                        {backups.length > 5 && (
                          <button
                            onClick={() => setActiveTab('history')}
                            className="w-full text-center py-2 text-blue-600 hover:text-blue-800 text-sm"
                          >
                            View all {backups.length} backups
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Active schedules preview */}
                {schedules && schedules.length > 0 && (
                  <div className="rounded-lg bg-white border shadow-sm">
                    <div className="border-b border-gray-200 p-6">
                      <h3 className="text-lg font-semibold text-gray-900">
                        Active Schedules
                      </h3>
                    </div>
                    <div className="p-6">
                      <div className="space-y-3">
                        {schedules.filter(s => s.enabled).slice(0, 3).map((schedule) => (
                          <div key={schedule.id} className="flex items-center justify-between">
                            <div>
                              <span className="font-medium text-gray-900">{schedule.name}</span>
                              <span className="ml-2 text-sm text-gray-600">{schedule.cron_expression}</span>
                            </div>
                            <span className="text-sm text-gray-600">
                              Next: {schedule.next_run ? formatDistanceToNow(new Date(schedule.next_run)) : 'Not scheduled'}
                            </span>
                          </div>
                        ))}
                      </div>
                      {schedules.filter(s => s.enabled).length > 3 && (
                        <button
                          onClick={() => setActiveTab('schedules')}
                          className="mt-3 text-blue-600 hover:text-blue-800 text-sm"
                        >
                          View all schedules
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'schedules' && (
              <BackupScheduler
                projectId={selectedProject}
                schedules={schedules}
                isLoading={schedulesLoading}
              />
            )}

            {activeTab === 'history' && (
              <BackupHistory
                projectId={selectedProject}
                backups={backups}
                isLoading={backupsLoading}
              />
            )}
          </div>
        </>
      )}

      {/* Backup Scheduler Modal */}
      {showScheduler && (
        <BackupScheduler
          projectId={selectedProject}
          schedules={schedules}
          isLoading={schedulesLoading}
          isModal={true}
          onClose={() => setShowScheduler(false)}
        />
      )}
    </div>
  );
}