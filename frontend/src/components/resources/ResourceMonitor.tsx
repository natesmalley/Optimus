/**
 * ResourceMonitor - Real-time resource monitoring dashboard
 * Shows CPU, memory, and other resource usage with interactive charts
 */

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  Cpu, 
  MemoryStick,
  HardDrive,
  Wifi,
  Activity,
  Settings,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Minus
} from 'lucide-react';
import { useResourceManager, useOrchestrationWebSocket } from '../../hooks/useOrchestration';
import { ResourceChart } from './ResourceChart';
import { ResourceAllocator } from './ResourceAllocator';
import type { ResourceAllocation } from '../../types/api';

interface ResourceMonitorProps {
  projectId?: string;
  showAllocator?: boolean;
}

export function ResourceMonitor({ projectId, showAllocator = true }: ResourceMonitorProps) {
  const [selectedResource, setSelectedResource] = useState<'cpu' | 'memory' | 'storage' | 'network'>('cpu');
  const [timeRange, setTimeRange] = useState<'1h' | '6h' | '24h' | '7d'>('1h');
  const [showAllocatorModal, setShowAllocatorModal] = useState(false);
  const [historicalData, setHistoricalData] = useState<Array<{
    timestamp: Date;
    cpu: number;
    memory: number;
    storage: number;
    network: number;
  }>>([]);

  // Initialize WebSocket for real-time updates
  useOrchestrationWebSocket();

  const { 
    resourceUsage, 
    systemSummary, 
    isLoading, 
    error,
    refresh 
  } = useResourceManager();

  // Simulate historical data generation for demo
  useEffect(() => {
    const generateHistoricalData = () => {
      const now = new Date();
      const data = [];
      const points = 30; // Last 30 data points

      for (let i = points - 1; i >= 0; i--) {
        const timestamp = new Date(now.getTime() - i * 60000); // Every minute
        data.push({
          timestamp,
          cpu: Math.random() * 80 + 10,
          memory: Math.random() * 70 + 20,
          storage: Math.random() * 60 + 30,
          network: Math.random() * 50 + 5,
        });
      }
      return data;
    };

    setHistoricalData(generateHistoricalData());

    // Update data every 30 seconds
    const interval = setInterval(() => {
      setHistoricalData(prev => {
        const newPoint = {
          timestamp: new Date(),
          cpu: Math.random() * 80 + 10,
          memory: Math.random() * 70 + 20,
          storage: Math.random() * 60 + 30,
          network: Math.random() * 50 + 5,
        };
        return [...prev.slice(1), newPoint];
      });
    }, 30000);

    return () => clearInterval(interval);
  }, []);

  const getResourceIcon = (resource: string) => {
    switch (resource) {
      case 'cpu': return <Cpu className="h-5 w-5" />;
      case 'memory': return <MemoryStick className="h-5 w-5" />;
      case 'storage': return <HardDrive className="h-5 w-5" />;
      case 'network': return <Wifi className="h-5 w-5" />;
      default: return <Activity className="h-5 w-5" />;
    }
  };

  const getResourceColor = (resource: string) => {
    switch (resource) {
      case 'cpu': return 'text-blue-600';
      case 'memory': return 'text-purple-600';
      case 'storage': return 'text-green-600';
      case 'network': return 'text-orange-600';
      default: return 'text-gray-600';
    }
  };

  const getUsageColor = (percentage: number) => {
    if (percentage >= 90) return 'text-red-600 bg-red-50';
    if (percentage >= 75) return 'text-orange-600 bg-orange-50';
    if (percentage >= 50) return 'text-yellow-600 bg-yellow-50';
    return 'text-green-600 bg-green-50';
  };

  const getTrendIcon = (current: number, previous: number) => {
    if (current > previous + 5) return <TrendingUp className="h-4 w-4 text-red-500" />;
    if (current < previous - 5) return <TrendingDown className="h-4 w-4 text-green-500" />;
    return <Minus className="h-4 w-4 text-gray-400" />;
  };

  // Calculate system-wide stats
  const systemStats = React.useMemo(() => {
    if (!resourceUsage || !systemSummary) return null;

    const totalCpu = resourceUsage.reduce((sum, r) => sum + r.current_usage.cpu_percent, 0);
    const totalMemoryMB = resourceUsage.reduce((sum, r) => sum + r.current_usage.memory_mb, 0);
    const avgCpu = resourceUsage.length > 0 ? totalCpu / resourceUsage.length : 0;
    const totalMemoryGB = totalMemoryMB / 1024;

    return {
      avgCpu: avgCpu.toFixed(1),
      totalMemoryGB: totalMemoryGB.toFixed(1),
      activeProjects: resourceUsage.filter(r => r.current_usage.cpu_percent > 0).length,
      highUsageProjects: resourceUsage.filter(r => r.current_usage.cpu_percent > 50).length,
    };
  }, [resourceUsage, systemSummary]);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2 text-gray-600">Loading resource monitor...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 border border-red-200 p-6">
        <div className="flex items-center space-x-2">
          <AlertTriangle className="h-5 w-5 text-red-500" />
          <span className="text-red-800">Failed to load resource data</span>
        </div>
        <button
          onClick={refresh}
          className="mt-2 text-sm text-red-700 hover:text-red-900 underline"
        >
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Resource Monitor</h1>
          <p className="mt-2 text-gray-600">
            Real-time system and project resource usage
          </p>
        </div>
        
        <div className="flex items-center space-x-4">
          {/* Time range selector */}
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value as any)}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-blue-500"
          >
            <option value="1h">Last Hour</option>
            <option value="6h">Last 6 Hours</option>
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
          </select>

          {showAllocator && (
            <button
              onClick={() => setShowAllocatorModal(true)}
              className="flex items-center space-x-2 rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
            >
              <Settings className="h-4 w-4" />
              <span>Manage Resources</span>
            </button>
          )}
        </div>
      </div>

      {/* System overview cards */}
      {systemStats && (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-lg bg-white p-6 shadow-md border"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">Average CPU</p>
                <p className="text-3xl font-bold text-blue-600">{systemStats.avgCpu}%</p>
              </div>
              <Cpu className="h-8 w-8 text-blue-400" />
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
                <p className="text-sm text-gray-600">Total Memory</p>
                <p className="text-3xl font-bold text-purple-600">{systemStats.totalMemoryGB} GB</p>
              </div>
              <MemoryStick className="h-8 w-8 text-purple-400" />
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
                <p className="text-sm text-gray-600">Active Projects</p>
                <p className="text-3xl font-bold text-green-600">{systemStats.activeProjects}</p>
              </div>
              <Activity className="h-8 w-8 text-green-400" />
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
                <p className="text-sm text-gray-600">High Usage</p>
                <p className="text-3xl font-bold text-red-600">{systemStats.highUsageProjects}</p>
              </div>
              <AlertTriangle className="h-8 w-8 text-red-400" />
            </div>
          </motion.div>
        </div>
      )}

      {/* Resource selection tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {[
            { id: 'cpu', label: 'CPU Usage', icon: Cpu },
            { id: 'memory', label: 'Memory', icon: MemoryStick },
            { id: 'storage', label: 'Storage', icon: HardDrive },
            { id: 'network', label: 'Network', icon: Wifi },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setSelectedResource(id as any)}
              className={`flex items-center space-x-2 border-b-2 py-2 px-1 text-sm font-medium ${
                selectedResource === id
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

      {/* Main chart */}
      <div className="rounded-lg bg-white border shadow-sm p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center space-x-2">
            <span className={getResourceColor(selectedResource)}>
              {getResourceIcon(selectedResource)}
            </span>
            <span>{selectedResource.toUpperCase()} Usage Over Time</span>
          </h3>
          
          <div className="text-sm text-gray-500">
            Last updated: {new Date().toLocaleTimeString()}
          </div>
        </div>

        <ResourceChart
          data={historicalData}
          selectedResource={selectedResource}
          timeRange={timeRange}
        />
      </div>

      {/* Project-specific resource usage */}
      {resourceUsage && resourceUsage.length > 0 && (
        <div className="rounded-lg bg-white border shadow-sm">
          <div className="border-b border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900">
              Project Resource Usage
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              Current resource consumption by project
            </p>
          </div>
          
          <div className="p-6">
            <div className="space-y-4">
              {resourceUsage
                .filter(resource => !projectId || resource.project_id === projectId)
                .sort((a, b) => b.current_usage.cpu_percent - a.current_usage.cpu_percent)
                .map((resource, index) => (
                <motion.div
                  key={resource.project_id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="flex items-center justify-between p-4 rounded-lg border hover:bg-gray-50"
                >
                  <div className="flex-1">
                    <h4 className="font-medium text-gray-900">
                      Project {resource.project_id}
                    </h4>
                    
                    <div className="grid grid-cols-2 gap-4 mt-2 sm:grid-cols-4">
                      <div className="flex items-center space-x-2">
                        <Cpu className="h-4 w-4 text-blue-500" />
                        <span className="text-sm text-gray-600">
                          CPU: {resource.current_usage.cpu_percent.toFixed(1)}%
                        </span>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <MemoryStick className="h-4 w-4 text-purple-500" />
                        <span className="text-sm text-gray-600">
                          RAM: {(resource.current_usage.memory_mb / 1024).toFixed(1)} GB
                        </span>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <HardDrive className="h-4 w-4 text-green-500" />
                        <span className="text-sm text-gray-600">
                          Disk: {(resource.current_usage.storage_mb / 1024).toFixed(1)} GB
                        </span>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <Wifi className="h-4 w-4 text-orange-500" />
                        <span className="text-sm text-gray-600">
                          Net: {resource.current_usage.network_kb} KB/s
                        </span>
                      </div>
                    </div>

                    {/* Resource limits */}
                    {(resource.cpu_limit || resource.memory_limit) && (
                      <div className="mt-2 text-xs text-gray-500">
                        Limits:{' '}
                        {resource.cpu_limit && `CPU ${resource.cpu_limit}%`}
                        {resource.cpu_limit && resource.memory_limit && ', '}
                        {resource.memory_limit && `Memory ${resource.memory_limit} MB`}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center space-x-3">
                    {/* Usage indicators */}
                    <div className={`rounded-full px-2 py-1 text-xs font-medium ${getUsageColor(resource.current_usage.cpu_percent)}`}>
                      {resource.current_usage.cpu_percent >= 90 ? 'High' : 
                       resource.current_usage.cpu_percent >= 50 ? 'Medium' : 'Low'}
                    </div>

                    {/* Recommendations */}
                    {resource.recommendations && (
                      <button
                        onClick={() => {
                          // Show recommendations modal
                          console.log('Show recommendations:', resource.recommendations);
                        }}
                        className="text-blue-600 hover:text-blue-800"
                      >
                        <Settings className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Resource Allocator Modal */}
      {showAllocatorModal && (
        <ResourceAllocator
          projectId={projectId}
          isOpen={showAllocatorModal}
          onClose={() => setShowAllocatorModal(false)}
          resourceUsage={resourceUsage}
        />
      )}
    </div>
  );
}