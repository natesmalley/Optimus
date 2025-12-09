/**
 * EnvironmentSwitcher - Modal component for switching project environments
 * Allows users to select and switch between dev/staging/prod environments
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, CheckCircle, Settings, AlertTriangle, Loader2 } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useEnvironmentSwitcher } from '../../hooks/useOrchestration';
import { orchestrationService } from '../../services/orchestrationService';
import type { EnvironmentConfig, SwitchEnvironmentRequest } from '../../types/api';

interface EnvironmentSwitcherProps {
  projectId: string;
  isOpen: boolean;
  onClose: () => void;
}

export function EnvironmentSwitcher({ projectId, isOpen, onClose }: EnvironmentSwitcherProps) {
  const [selectedEnvironment, setSelectedEnvironment] = useState<string>('');
  const [customVariables, setCustomVariables] = useState<Record<string, string>>({});
  const [restartIfRunning, setRestartIfRunning] = useState(true);

  // Get current environment
  const { data: currentEnvironment, isLoading: currentLoading } = useQuery({
    queryKey: ['orchestration', 'environment', projectId],
    queryFn: () => orchestrationService.getCurrentEnvironment(projectId),
    enabled: isOpen && !!projectId,
  });

  // Get available environments
  const { data: availableEnvironments, isLoading: availableLoading } = useQuery({
    queryKey: ['orchestration', 'environments', 'available', projectId],
    queryFn: () => orchestrationService.getAvailableEnvironments(projectId),
    enabled: isOpen && !!projectId,
  });

  const switchMutation = useEnvironmentSwitcher();

  // Set default selected environment
  useEffect(() => {
    if (currentEnvironment && !selectedEnvironment) {
      setSelectedEnvironment(currentEnvironment.name);
    }
  }, [currentEnvironment, selectedEnvironment]);

  const handleSwitch = async () => {
    if (!selectedEnvironment || selectedEnvironment === currentEnvironment?.name) {
      onClose();
      return;
    }

    const request: SwitchEnvironmentRequest = {
      environment: selectedEnvironment,
      restart_if_running: restartIfRunning,
    };

    if (Object.keys(customVariables).length > 0) {
      request.variables = customVariables;
    }

    try {
      await switchMutation.mutateAsync({ projectId, request });
      onClose();
    } catch (error) {
      console.error('Failed to switch environment:', error);
    }
  };

  const handleAddVariable = () => {
    const key = prompt('Enter variable name:');
    if (key && !customVariables[key]) {
      setCustomVariables(prev => ({ ...prev, [key]: '' }));
    }
  };

  const handleUpdateVariable = (key: string, value: string) => {
    setCustomVariables(prev => ({ ...prev, [key]: value }));
  };

  const handleRemoveVariable = (key: string) => {
    setCustomVariables(prev => {
      const updated = { ...prev };
      delete updated[key];
      return updated;
    });
  };

  const isLoading = currentLoading || availableLoading || switchMutation.isPending;
  const hasChanges = selectedEnvironment !== currentEnvironment?.name || 
                    Object.keys(customVariables).length > 0;

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
            className="inline-block w-full max-w-md transform rounded-lg bg-white p-6 text-left align-bottom shadow-xl transition-all sm:my-8 sm:align-middle"
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-3">
                <Settings className="h-6 w-6 text-blue-600" />
                <h3 className="text-lg font-medium text-gray-900">
                  Switch Environment
                </h3>
              </div>
              <button
                onClick={onClose}
                className="rounded-md p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                <span className="ml-2 text-gray-600">Loading environments...</span>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Current environment info */}
                {currentEnvironment && (
                  <div className="rounded-md bg-blue-50 border border-blue-200 p-4">
                    <div className="flex items-center space-x-2">
                      <CheckCircle className="h-5 w-5 text-blue-600" />
                      <span className="font-medium text-blue-800">
                        Current: {currentEnvironment.name}
                      </span>
                    </div>
                    {Object.keys(currentEnvironment.variables).length > 0 && (
                      <div className="mt-2 text-sm text-blue-700">
                        Variables: {Object.keys(currentEnvironment.variables).length} configured
                      </div>
                    )}
                  </div>
                )}

                {/* Environment selection */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Select Environment
                  </label>
                  <div className="grid grid-cols-1 gap-3">
                    {availableEnvironments?.map((env) => (
                      <label
                        key={env.name}
                        className={`relative flex cursor-pointer rounded-lg border p-3 focus:outline-none ${
                          selectedEnvironment === env.name
                            ? 'border-blue-600 ring-2 ring-blue-600'
                            : 'border-gray-300 hover:border-gray-400'
                        }`}
                      >
                        <input
                          type="radio"
                          name="environment"
                          value={env.name}
                          checked={selectedEnvironment === env.name}
                          onChange={(e) => setSelectedEnvironment(e.target.value)}
                          className="sr-only"
                        />
                        <div className="flex flex-1 items-center justify-between">
                          <div>
                            <div className="flex items-center space-x-2">
                              <span className="font-medium text-gray-900 capitalize">
                                {env.name}
                              </span>
                              {env.name === 'prod' && (
                                <AlertTriangle className="h-4 w-4 text-red-500" />
                              )}
                            </div>
                            <div className="text-sm text-gray-600">
                              {Object.keys(env.variables).length} variables configured
                            </div>
                          </div>
                          {selectedEnvironment === env.name && (
                            <CheckCircle className="h-5 w-5 text-blue-600" />
                          )}
                        </div>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Custom variables */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-gray-700">
                      Custom Variables
                    </label>
                    <button
                      onClick={handleAddVariable}
                      className="text-sm text-blue-600 hover:text-blue-800"
                    >
                      Add Variable
                    </button>
                  </div>
                  
                  {Object.keys(customVariables).length > 0 ? (
                    <div className="space-y-2 max-h-32 overflow-y-auto">
                      {Object.entries(customVariables).map(([key, value]) => (
                        <div key={key} className="flex items-center space-x-2">
                          <input
                            type="text"
                            value={key}
                            readOnly
                            className="flex-1 rounded-md border border-gray-300 bg-gray-50 px-3 py-2 text-sm"
                          />
                          <span className="text-gray-400">=</span>
                          <input
                            type="text"
                            value={value}
                            onChange={(e) => handleUpdateVariable(key, e.target.value)}
                            placeholder="Value"
                            className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-blue-500"
                          />
                          <button
                            onClick={() => handleRemoveVariable(key)}
                            className="text-red-500 hover:text-red-700"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">
                      No custom variables set
                    </p>
                  )}
                </div>

                {/* Options */}
                <div>
                  <label className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      checked={restartIfRunning}
                      onChange={(e) => setRestartIfRunning(e.target.checked)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-sm text-gray-700">
                      Restart project if currently running
                    </span>
                  </label>
                </div>

                {/* Error message */}
                {switchMutation.error && (
                  <div className="rounded-md bg-red-50 border border-red-200 p-3">
                    <div className="flex items-center space-x-2">
                      <AlertTriangle className="h-4 w-4 text-red-500" />
                      <span className="text-sm text-red-800">
                        {switchMutation.error instanceof Error 
                          ? switchMutation.error.message 
                          : 'Failed to switch environment'}
                      </span>
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
                  <button
                    onClick={onClose}
                    className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSwitch}
                    disabled={!hasChanges || switchMutation.isPending}
                    className={`flex items-center space-x-2 rounded-md px-4 py-2 text-sm font-medium text-white ${
                      hasChanges && !switchMutation.isPending
                        ? 'bg-blue-600 hover:bg-blue-700'
                        : 'bg-gray-400 cursor-not-allowed'
                    }`}
                  >
                    {switchMutation.isPending && (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    )}
                    <span>
                      {switchMutation.isPending ? 'Switching...' : 'Switch Environment'}
                    </span>
                  </button>
                </div>
              </div>
            )}
          </motion.div>
        </div>
      </div>
    </AnimatePresence>
  );
}