/**
 * ResourceAllocator - Modal component for managing resource allocation
 * Allows users to set resource limits and priorities for projects
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  X, 
  Settings,
  Cpu,
  MemoryStick,
  HardDrive,
  Wifi,
  Save,
  RotateCcw,
  AlertTriangle,
  Info,
  TrendingUp,
  Loader2
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useResourceManager } from '../../hooks/useOrchestration';
import { orchestrationService } from '../../services/orchestrationService';
import type { ResourceAllocation, ResourceAllocationRequest } from '../../types/api';

interface ResourceAllocatorProps {
  projectId?: string;
  isOpen: boolean;
  onClose: () => void;
  resourceUsage?: ResourceAllocation[];
}

interface ResourceLimits {
  cpu_limit: number;
  memory_limit: number;
  storage_limit: number;
  priority: 'low' | 'normal' | 'high';
}

export function ResourceAllocator({ 
  projectId, 
  isOpen, 
  onClose, 
  resourceUsage = [] 
}: ResourceAllocatorProps) {
  const [selectedProjectId, setSelectedProjectId] = useState(projectId || '');
  const [limits, setLimits] = useState<ResourceLimits>({
    cpu_limit: 50,
    memory_limit: 1024,
    storage_limit: 10240,
    priority: 'normal',
  });
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  const { allocateResources, isAllocating } = useResourceManager();

  // Get projects for selection dropdown
  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      const response = await orchestrationService.getAllProjectStatuses();
      return response;
    },
    enabled: isOpen,
  });

  // Get current resource allocation for selected project
  const { data: currentAllocation } = useQuery({
    queryKey: ['orchestration', 'resources', selectedProjectId],
    queryFn: () => orchestrationService.getResourceUsage(selectedProjectId),
    enabled: isOpen && !!selectedProjectId,
  });

  // Update limits when current allocation changes
  useEffect(() => {
    if (currentAllocation) {
      setLimits({
        cpu_limit: currentAllocation.cpu_limit || 50,
        memory_limit: currentAllocation.memory_limit || 1024,
        storage_limit: currentAllocation.storage_limit || 10240,
        priority: 'normal', // Default priority
      });
      setHasUnsavedChanges(false);
    }
  }, [currentAllocation]);

  const handleLimitChange = (field: keyof ResourceLimits, value: number | string) => {
    setLimits(prev => ({
      ...prev,
      [field]: value
    }));
    setHasUnsavedChanges(true);
  };

  const handleSave = async () => {
    if (!selectedProjectId) return;

    const request: ResourceAllocationRequest = {
      cpu_limit: limits.cpu_limit,
      memory_limit: limits.memory_limit,
      storage_limit: limits.storage_limit,
      priority: limits.priority,
    };

    try {
      await allocateResources(selectedProjectId, request);
      setHasUnsavedChanges(false);
      // Don't close automatically - let user see the success state
    } catch (error) {
      console.error('Failed to allocate resources:', error);
    }
  };

  const handleReset = () => {
    if (currentAllocation) {
      setLimits({
        cpu_limit: currentAllocation.cpu_limit || 50,
        memory_limit: currentAllocation.memory_limit || 1024,
        storage_limit: currentAllocation.storage_limit || 10240,
        priority: 'normal',
      });
      setHasUnsavedChanges(false);
    }
  };

  const getUsagePercentage = (current: number, limit: number) => {
    return limit > 0 ? (current / limit) * 100 : 0;
  };

  const getUsageColor = (percentage: number) => {
    if (percentage >= 90) return 'text-red-600 bg-red-100';
    if (percentage >= 75) return 'text-orange-600 bg-orange-100';
    if (percentage >= 50) return 'text-yellow-600 bg-yellow-100';
    return 'text-green-600 bg-green-100';
  };

  const getRecommendation = (current: number, limit: number, type: 'cpu' | 'memory' | 'storage') => {
    const usage = getUsagePercentage(current, limit);
    
    if (usage >= 90) {
      const suggested = Math.ceil(limit * 1.5);
      return {
        type: 'warning',
        message: `Consider increasing ${type} limit to ${suggested}${type === 'cpu' ? '%' : ' MB'}`,
      };
    }
    
    if (usage <= 25) {
      const suggested = Math.max(Math.ceil(current * 1.2), Math.ceil(limit * 0.8));
      return {
        type: 'info',
        message: `You could reduce ${type} limit to ${suggested}${type === 'cpu' ? '%' : ' MB'} to save resources`,
      };
    }
    
    return null;
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 overflow-y-auto">
        <div className="flex min-h-screen items-end justify-center px-4 pt-4 pb-20 text-center sm:block sm:p-0">
          {/* Background overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
            onClick={onClose}
          />

          {/* Modal panel */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="inline-block w-full max-w-2xl transform rounded-lg bg-white p-6 text-left align-bottom shadow-xl transition-all sm:my-8 sm:align-middle"
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-3">
                <Settings className="h-6 w-6 text-blue-600" />
                <h3 className="text-lg font-medium text-gray-900">
                  Resource Allocation
                </h3>
              </div>
              <button
                onClick={onClose}
                className="rounded-md p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-6">
              {/* Project selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select Project
                </label>
                <select
                  value={selectedProjectId}
                  onChange={(e) => setSelectedProjectId(e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-blue-500"
                >
                  <option value="">Select a project...</option>
                  {projects?.map(project => (
                    <option key={project.project_id} value={project.project_id}>
                      {project.project_name}
                    </option>
                  ))}
                </select>
              </div>

              {selectedProjectId && currentAllocation && (
                <>
                  {/* Current usage overview */}
                  <div className="rounded-lg bg-gray-50 border p-4">
                    <h4 className="font-medium text-gray-900 mb-3">Current Usage</h4>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <Cpu className="h-4 w-4 text-blue-500" />
                          <span className="text-sm text-gray-600">CPU</span>
                        </div>
                        <span className="text-sm font-medium">
                          {currentAllocation.current_usage.cpu_percent.toFixed(1)}%
                        </span>
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <MemoryStick className="h-4 w-4 text-purple-500" />
                          <span className="text-sm text-gray-600">Memory</span>
                        </div>
                        <span className="text-sm font-medium">
                          {(currentAllocation.current_usage.memory_mb / 1024).toFixed(1)} GB
                        </span>
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <HardDrive className="h-4 w-4 text-green-500" />
                          <span className="text-sm text-gray-600">Storage</span>
                        </div>
                        <span className="text-sm font-medium">
                          {(currentAllocation.current_usage.storage_mb / 1024).toFixed(1)} GB
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Resource limits */}
                  <div className="space-y-4">
                    <h4 className="font-medium text-gray-900">Resource Limits</h4>
                    
                    {/* CPU Limit */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        CPU Limit (%)
                      </label>
                      <div className="space-y-2">
                        <input
                          type="range"
                          min="10"
                          max="100"
                          step="5"
                          value={limits.cpu_limit}
                          onChange={(e) => handleLimitChange('cpu_limit', parseInt(e.target.value))}
                          className="w-full"
                        />
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-gray-500">10%</span>
                          <span className="font-medium">{limits.cpu_limit}%</span>
                          <span className="text-gray-500">100%</span>
                        </div>
                        {/* Usage indicator */}
                        <div className="flex items-center space-x-2">
                          <div className="flex-1 bg-gray-200 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full ${
                                getUsagePercentage(currentAllocation.current_usage.cpu_percent, limits.cpu_limit) >= 90
                                  ? 'bg-red-500'
                                  : getUsagePercentage(currentAllocation.current_usage.cpu_percent, limits.cpu_limit) >= 75
                                  ? 'bg-orange-500'
                                  : 'bg-blue-500'
                              }`}
                              style={{
                                width: `${Math.min(getUsagePercentage(currentAllocation.current_usage.cpu_percent, limits.cpu_limit), 100)}%`
                              }}
                            />
                          </div>
                          <span className="text-xs text-gray-500">
                            {getUsagePercentage(currentAllocation.current_usage.cpu_percent, limits.cpu_limit).toFixed(0)}% used
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Memory Limit */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Memory Limit (MB)
                      </label>
                      <div className="space-y-2">
                        <input
                          type="range"
                          min="256"
                          max="16384"
                          step="256"
                          value={limits.memory_limit}
                          onChange={(e) => handleLimitChange('memory_limit', parseInt(e.target.value))}
                          className="w-full"
                        />
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-gray-500">256 MB</span>
                          <span className="font-medium">{limits.memory_limit} MB ({(limits.memory_limit / 1024).toFixed(1)} GB)</span>
                          <span className="text-gray-500">16 GB</span>
                        </div>
                        <div className="flex items-center space-x-2">
                          <div className="flex-1 bg-gray-200 rounded-full h-2">
                            <div
                              className={`h-2 rounded-full ${
                                getUsagePercentage(currentAllocation.current_usage.memory_mb, limits.memory_limit) >= 90
                                  ? 'bg-red-500'
                                  : getUsagePercentage(currentAllocation.current_usage.memory_mb, limits.memory_limit) >= 75
                                  ? 'bg-orange-500'
                                  : 'bg-purple-500'
                              }`}
                              style={{
                                width: `${Math.min(getUsagePercentage(currentAllocation.current_usage.memory_mb, limits.memory_limit), 100)}%`
                              }}
                            />
                          </div>
                          <span className="text-xs text-gray-500">
                            {getUsagePercentage(currentAllocation.current_usage.memory_mb, limits.memory_limit).toFixed(0)}% used
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Advanced options */}
                    <button
                      onClick={() => setShowAdvanced(!showAdvanced)}
                      className="flex items-center space-x-2 text-sm text-blue-600 hover:text-blue-800"
                    >
                      <Settings className="h-4 w-4" />
                      <span>{showAdvanced ? 'Hide' : 'Show'} Advanced Options</span>
                    </button>

                    {showAdvanced && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="space-y-4 pt-4 border-t border-gray-200"
                      >
                        {/* Storage Limit */}
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            Storage Limit (MB)
                          </label>
                          <div className="space-y-2">
                            <input
                              type="range"
                              min="1024"
                              max="102400"
                              step="1024"
                              value={limits.storage_limit}
                              onChange={(e) => handleLimitChange('storage_limit', parseInt(e.target.value))}
                              className="w-full"
                            />
                            <div className="flex items-center justify-between text-sm">
                              <span className="text-gray-500">1 GB</span>
                              <span className="font-medium">{(limits.storage_limit / 1024).toFixed(1)} GB</span>
                              <span className="text-gray-500">100 GB</span>
                            </div>
                          </div>
                        </div>

                        {/* Priority */}
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            Resource Priority
                          </label>
                          <select
                            value={limits.priority}
                            onChange={(e) => handleLimitChange('priority', e.target.value)}
                            className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-blue-500"
                          >
                            <option value="low">Low - Background tasks</option>
                            <option value="normal">Normal - Standard applications</option>
                            <option value="high">High - Critical services</option>
                          </select>
                          <p className="mt-1 text-xs text-gray-500">
                            Higher priority projects get more resources when there's contention
                          </p>
                        </div>
                      </motion.div>
                    )}
                  </div>

                  {/* Recommendations */}
                  {currentAllocation && (
                    <div className="space-y-3">
                      {[
                        getRecommendation(currentAllocation.current_usage.cpu_percent, limits.cpu_limit, 'cpu'),
                        getRecommendation(currentAllocation.current_usage.memory_mb, limits.memory_limit, 'memory'),
                        showAdvanced && getRecommendation(currentAllocation.current_usage.storage_mb, limits.storage_limit, 'storage'),
                      ].filter(Boolean).map((recommendation, index) => (
                        <div
                          key={index}
                          className={`rounded-md border p-3 ${
                            recommendation!.type === 'warning'
                              ? 'border-orange-200 bg-orange-50'
                              : 'border-blue-200 bg-blue-50'
                          }`}
                        >
                          <div className="flex items-start space-x-2">
                            {recommendation!.type === 'warning' ? (
                              <AlertTriangle className="h-4 w-4 text-orange-500 mt-0.5" />
                            ) : (
                              <Info className="h-4 w-4 text-blue-500 mt-0.5" />
                            )}
                            <span className={`text-sm ${
                              recommendation!.type === 'warning' ? 'text-orange-700' : 'text-blue-700'
                            }`}>
                              {recommendation!.message}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}

              {/* Actions */}
              <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
                <button
                  onClick={handleReset}
                  disabled={!hasUnsavedChanges}
                  className="flex items-center space-x-2 rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <RotateCcw className="h-4 w-4" />
                  <span>Reset</span>
                </button>

                <button
                  onClick={onClose}
                  className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>

                <button
                  onClick={handleSave}
                  disabled={!selectedProjectId || !hasUnsavedChanges || isAllocating}
                  className={`flex items-center space-x-2 rounded-md px-4 py-2 text-sm font-medium text-white ${
                    selectedProjectId && hasUnsavedChanges && !isAllocating
                      ? 'bg-blue-600 hover:bg-blue-700'
                      : 'bg-gray-400 cursor-not-allowed'
                  }`}
                >
                  {isAllocating ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Save className="h-4 w-4" />
                  )}
                  <span>
                    {isAllocating ? 'Saving...' : 'Save Changes'}
                  </span>
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </AnimatePresence>
  );
}