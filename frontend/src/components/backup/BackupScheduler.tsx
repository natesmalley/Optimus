/**
 * BackupScheduler - Component for managing backup schedules
 * Allows creating, editing, and managing automated backup schedules
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Calendar,
  Clock,
  Plus,
  Edit,
  Trash2,
  Power,
  PowerOff,
  Play,
  X,
  Save,
  Loader2,
  AlertTriangle,
  CheckCircle
} from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { backupService } from '../../services/backupService';
import { formatDistanceToNow } from 'date-fns';
import type { BackupSchedule } from '../../types/api';

interface BackupSchedulerProps {
  projectId: string;
  schedules?: BackupSchedule[];
  isLoading?: boolean;
  isModal?: boolean;
  onClose?: () => void;
}

interface ScheduleForm {
  name: string;
  cron_expression: string;
  backup_type: string;
  retention_days: number;
  includes: string[];
  excludes: string[];
  enabled: boolean;
}

export function BackupScheduler({ 
  projectId, 
  schedules = [], 
  isLoading = false,
  isModal = false,
  onClose 
}: BackupSchedulerProps) {
  const [showForm, setShowForm] = useState(false);
  const [editingSchedule, setEditingSchedule] = useState<BackupSchedule | null>(null);
  const [form, setForm] = useState<ScheduleForm>({
    name: '',
    cron_expression: '0 2 * * *', // Daily at 2 AM
    backup_type: 'full',
    retention_days: 30,
    includes: [],
    excludes: ['.git', 'node_modules', '.DS_Store'],
    enabled: true,
  });

  const queryClient = useQueryClient();

  // Create schedule mutation
  const createMutation = useMutation({
    mutationFn: (data: any) => backupService.createSchedule(projectId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backup', 'schedules', projectId] });
      resetForm();
      setShowForm(false);
    },
  });

  // Update schedule mutation
  const updateMutation = useMutation({
    mutationFn: ({ scheduleId, updates }: { scheduleId: string; updates: any }) =>
      backupService.updateSchedule(projectId, scheduleId, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backup', 'schedules', projectId] });
      resetForm();
      setShowForm(false);
      setEditingSchedule(null);
    },
  });

  // Delete schedule mutation
  const deleteMutation = useMutation({
    mutationFn: (scheduleId: string) => backupService.deleteSchedule(projectId, scheduleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backup', 'schedules', projectId] });
    },
  });

  // Toggle schedule mutation
  const toggleMutation = useMutation({
    mutationFn: ({ scheduleId, enabled }: { scheduleId: string; enabled: boolean }) =>
      backupService.toggleSchedule(projectId, scheduleId, enabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backup', 'schedules', projectId] });
    },
  });

  // Run schedule now mutation
  const runNowMutation = useMutation({
    mutationFn: (scheduleId: string) => backupService.runScheduleNow(projectId, scheduleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backup', projectId] });
    },
  });

  const resetForm = () => {
    setForm({
      name: '',
      cron_expression: '0 2 * * *',
      backup_type: 'full',
      retention_days: 30,
      includes: [],
      excludes: ['.git', 'node_modules', '.DS_Store'],
      enabled: true,
    });
    setEditingSchedule(null);
  };

  const handleEdit = (schedule: BackupSchedule) => {
    setForm({
      name: schedule.name,
      cron_expression: schedule.cron_expression,
      backup_type: schedule.backup_type,
      retention_days: schedule.retention_days,
      includes: schedule.includes,
      excludes: schedule.excludes,
      enabled: schedule.enabled,
    });
    setEditingSchedule(schedule);
    setShowForm(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (editingSchedule) {
      updateMutation.mutate({ scheduleId: editingSchedule.id, updates: form });
    } else {
      createMutation.mutate(form);
    }
  };

  const handleToggleSchedule = (schedule: BackupSchedule) => {
    toggleMutation.mutate({ 
      scheduleId: schedule.id, 
      enabled: !schedule.enabled 
    });
  };

  const handleDeleteSchedule = (schedule: BackupSchedule) => {
    if (window.confirm(`Are you sure you want to delete the schedule "${schedule.name}"?`)) {
      deleteMutation.mutate(schedule.id);
    }
  };

  const handleRunNow = (schedule: BackupSchedule) => {
    if (window.confirm(`Run backup schedule "${schedule.name}" immediately?`)) {
      runNowMutation.mutate(schedule.id);
    }
  };

  const parseCronExpression = (cron: string) => {
    const parts = cron.split(' ');
    if (parts.length !== 5) return 'Custom schedule';
    
    const [minute, hour, day, month, dayOfWeek] = parts;
    
    if (minute === '0' && hour !== '*' && day === '*' && month === '*' && dayOfWeek === '*') {
      return `Daily at ${hour}:00`;
    }
    if (minute === '0' && hour !== '*' && day === '*' && month === '*' && dayOfWeek !== '*') {
      const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      return `Weekly on ${days[parseInt(dayOfWeek)]} at ${hour}:00`;
    }
    if (minute === '0' && hour !== '*' && day !== '*' && month === '*' && dayOfWeek === '*') {
      return `Monthly on day ${day} at ${hour}:00`;
    }
    
    return 'Custom schedule';
  };

  const content = (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Backup Schedules</h3>
          <p className="text-sm text-gray-600">Automated backup scheduling and management</p>
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center space-x-2 rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
          >
            <Plus className="h-4 w-4" />
            <span>New Schedule</span>
          </button>
          
          {isModal && (
            <button
              onClick={onClose}
              className="rounded-md p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100"
            >
              <X className="h-5 w-5" />
            </button>
          )}
        </div>
      </div>

      {/* Schedules list */}
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
          <span className="ml-2 text-gray-600">Loading schedules...</span>
        </div>
      ) : schedules.length === 0 ? (
        <div className="text-center py-8">
          <Calendar className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No backup schedules
          </h3>
          <p className="text-gray-600 mb-4">
            Create automated backup schedules to protect your project regularly
          </p>
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center space-x-2 rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 mx-auto"
          >
            <Plus className="h-4 w-4" />
            <span>Create First Schedule</span>
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {schedules.map((schedule, index) => (
            <motion.div
              key={schedule.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className={`rounded-lg border p-4 ${
                schedule.enabled ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-gray-50'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3">
                    <h4 className="font-medium text-gray-900">{schedule.name}</h4>
                    <div className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-medium ${
                      schedule.enabled 
                        ? 'text-green-700 bg-green-100' 
                        : 'text-gray-700 bg-gray-100'
                    }`}>
                      {schedule.enabled ? 'Active' : 'Disabled'}
                    </div>
                  </div>
                  
                  <div className="mt-2 space-y-1 text-sm text-gray-600">
                    <div className="flex items-center space-x-4">
                      <span className="flex items-center space-x-1">
                        <Clock className="h-4 w-4" />
                        <span>{parseCronExpression(schedule.cron_expression)}</span>
                      </span>
                      <span>Retention: {schedule.retention_days} days</span>
                    </div>
                    
                    {schedule.last_run && (
                      <div>
                        Last run: {formatDistanceToNow(new Date(schedule.last_run))} ago
                      </div>
                    )}
                    
                    {schedule.next_run && schedule.enabled && (
                      <div>
                        Next run: {formatDistanceToNow(new Date(schedule.next_run))}
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleRunNow(schedule)}
                    disabled={runNowMutation.isPending}
                    className="text-blue-600 hover:text-blue-800 p-1"
                    title="Run now"
                  >
                    <Play className="h-4 w-4" />
                  </button>

                  <button
                    onClick={() => handleToggleSchedule(schedule)}
                    disabled={toggleMutation.isPending}
                    className={`p-1 ${
                      schedule.enabled 
                        ? 'text-green-600 hover:text-green-800' 
                        : 'text-gray-400 hover:text-gray-600'
                    }`}
                    title={schedule.enabled ? 'Disable' : 'Enable'}
                  >
                    {schedule.enabled ? <PowerOff className="h-4 w-4" /> : <Power className="h-4 w-4" />}
                  </button>

                  <button
                    onClick={() => handleEdit(schedule)}
                    className="text-blue-600 hover:text-blue-800 p-1"
                    title="Edit"
                  >
                    <Edit className="h-4 w-4" />
                  </button>

                  <button
                    onClick={() => handleDeleteSchedule(schedule)}
                    disabled={deleteMutation.isPending}
                    className="text-red-600 hover:text-red-800 p-1"
                    title="Delete"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Form modal */}
      {showForm && (
        <AnimatePresence>
          <div className="fixed inset-0 z-50 overflow-y-auto">
            <div className="flex min-h-screen items-center justify-center p-4">
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-black bg-opacity-25"
                onClick={() => setShowForm(false)}
              />
              
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="relative bg-white rounded-lg p-6 w-full max-w-lg shadow-xl"
              >
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900">
                      {editingSchedule ? 'Edit Schedule' : 'Create Schedule'}
                    </h3>
                    <button
                      type="button"
                      onClick={() => {
                        setShowForm(false);
                        resetForm();
                      }}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      <X className="h-5 w-5" />
                    </button>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Schedule Name
                    </label>
                    <input
                      type="text"
                      value={form.name}
                      onChange={(e) => setForm(prev => ({ ...prev, name: e.target.value }))}
                      className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-blue-500"
                      placeholder="e.g., Daily backup"
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Schedule (Cron Expression)
                    </label>
                    <select
                      value={form.cron_expression}
                      onChange={(e) => setForm(prev => ({ ...prev, cron_expression: e.target.value }))}
                      className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-blue-500"
                    >
                      <option value="0 2 * * *">Daily at 2:00 AM</option>
                      <option value="0 3 * * 0">Weekly on Sunday at 3:00 AM</option>
                      <option value="0 4 1 * *">Monthly on 1st at 4:00 AM</option>
                      <option value="0 1 * * 1-5">Weekdays at 1:00 AM</option>
                    </select>
                    <p className="mt-1 text-xs text-gray-500">
                      Current: {parseCronExpression(form.cron_expression)}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Backup Type
                      </label>
                      <select
                        value={form.backup_type}
                        onChange={(e) => setForm(prev => ({ ...prev, backup_type: e.target.value }))}
                        className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-blue-500"
                      >
                        <option value="full">Full Backup</option>
                        <option value="incremental">Incremental</option>
                        <option value="differential">Differential</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        Retention (Days)
                      </label>
                      <input
                        type="number"
                        value={form.retention_days}
                        onChange={(e) => setForm(prev => ({ ...prev, retention_days: parseInt(e.target.value) }))}
                        className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-blue-500"
                        min="1"
                        max="365"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Exclude Patterns (one per line)
                    </label>
                    <textarea
                      value={form.excludes.join('\n')}
                      onChange={(e) => setForm(prev => ({ 
                        ...prev, 
                        excludes: e.target.value.split('\n').filter(line => line.trim()) 
                      }))}
                      className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-blue-500"
                      rows={3}
                      placeholder=".git&#10;node_modules&#10;*.log"
                    />
                  </div>

                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="enabled"
                      checked={form.enabled}
                      onChange={(e) => setForm(prev => ({ ...prev, enabled: e.target.checked }))}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <label htmlFor="enabled" className="text-sm text-gray-700">
                      Enable schedule immediately
                    </label>
                  </div>

                  <div className="flex justify-end space-x-3 pt-4 border-t">
                    <button
                      type="button"
                      onClick={() => {
                        setShowForm(false);
                        resetForm();
                      }}
                      className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={createMutation.isPending || updateMutation.isPending}
                      className="flex items-center space-x-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                    >
                      {(createMutation.isPending || updateMutation.isPending) && (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      )}
                      <Save className="h-4 w-4" />
                      <span>{editingSchedule ? 'Update' : 'Create'}</span>
                    </button>
                  </div>
                </form>
              </motion.div>
            </div>
          </div>
        </AnimatePresence>
      )}
    </div>
  );

  if (isModal) {
    return (
      <AnimatePresence>
        <div className="fixed inset-0 z-50 overflow-y-auto">
          <div className="flex min-h-screen items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black bg-opacity-25"
              onClick={onClose}
            />
            
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="relative bg-white rounded-lg p-6 w-full max-w-4xl shadow-xl max-h-screen overflow-y-auto"
            >
              {content}
            </motion.div>
          </div>
        </div>
      </AnimatePresence>
    );
  }

  return content;
}