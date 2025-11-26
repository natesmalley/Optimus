import { useQuery } from '@tanstack/react-query';
import { 
  Cpu, 
  MemoryStick, 
  HardDrive,
  Wifi,
  Play,
  Square,
  AlertTriangle,
  Server,
  Activity
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { formatBytes, formatPercentage, getStatusColor } from '@/lib/utils';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import StatusBadge from '@/components/ui/StatusBadge';

export default function SystemMonitor() {
  const { data: runtimeData, isLoading, error } = useQuery({
    queryKey: ['runtime-overview'],
    queryFn: () => apiClient.getRuntimeOverview(),
    refetchInterval: 5000, // 5 second refresh for real-time monitoring
  });

  const { data: runtimeStats } = useQuery({
    queryKey: ['runtime-stats'],
    queryFn: () => apiClient.getRuntimeStats(),
    refetchInterval: 5000,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">Failed to load system monitor</h3>
          <p className="text-muted-foreground">
            {error instanceof Error ? error.message : 'Unknown error occurred'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">System Monitor</h1>
          <p className="text-muted-foreground mt-1">
            Real-time monitoring of system resources and processes
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-2 text-sm text-green-600">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span>Live</span>
          </div>
        </div>
      </div>

      {/* System Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="card">
          <div className="card-content p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">CPU Usage</p>
                <p className="text-2xl font-bold">
                  {runtimeData?.total_cpu_usage.toFixed(1)}%
                </p>
                <p className="text-xs text-muted-foreground">
                  {runtimeData?.total_processes} processes
                </p>
              </div>
              <Cpu className="w-8 h-8 text-blue-500" />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-content p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Memory Usage</p>
                <p className="text-2xl font-bold">
                  {formatBytes((runtimeData?.total_memory_usage_mb || 0) * 1024 * 1024)}
                </p>
                <p className="text-xs text-muted-foreground">
                  RAM in use
                </p>
              </div>
              <MemoryStick className="w-8 h-8 text-green-500" />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-content p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Active Ports</p>
                <p className="text-2xl font-bold">
                  {runtimeStats?.port_count || 0}
                </p>
                <p className="text-xs text-muted-foreground">
                  Ports in use
                </p>
              </div>
              <Wifi className="w-8 h-8 text-purple-500" />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-content p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Running Projects</p>
                <p className="text-2xl font-bold">
                  {runtimeData?.running_projects || 0}
                </p>
                <p className="text-xs text-muted-foreground">
                  of {runtimeData?.total_projects || 0} total
                </p>
              </div>
              <Server className="w-8 h-8 text-orange-500" />
            </div>
          </div>
        </div>
      </div>

      {/* Projects Runtime Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Project Runtime Status</h3>
            <p className="card-description">
              Real-time status of all projects
            </p>
          </div>
          <div className="card-content">
            {runtimeData?.projects ? (
              <div className="space-y-4">
                {runtimeData.projects.map((project) => (
                  <div key={project.project_id} className="flex items-center justify-between p-4 border border-border rounded-lg">
                    <div className="flex items-center space-x-4">
                      <div className={`w-3 h-3 rounded-full ${project.is_running ? 'bg-green-500' : 'bg-gray-400'}`} />
                      <div>
                        <p className="font-medium">{project.project_name}</p>
                        <p className="text-sm text-muted-foreground">
                          {project.process_count} processes
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm">
                        <span className="text-muted-foreground">CPU:</span> {project.total_cpu_usage.toFixed(1)}%
                      </div>
                      <div className="text-sm">
                        <span className="text-muted-foreground">Memory:</span> {formatBytes(project.total_memory_usage_mb * 1024 * 1024)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Server className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                <p className="text-muted-foreground">No projects running</p>
              </div>
            )}
          </div>
        </div>

        {/* Active Ports */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Active Ports</h3>
            <p className="card-description">
              Ports currently in use by running processes
            </p>
          </div>
          <div className="card-content">
            {runtimeStats?.active_ports && runtimeStats.active_ports.length > 0 ? (
              <div className="grid grid-cols-3 gap-3">
                {runtimeStats.active_ports.map((port) => (
                  <div key={port} className="p-3 bg-muted rounded-lg text-center">
                    <div className="font-medium">:{port}</div>
                    <div className="text-xs text-muted-foreground">Active</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Wifi className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                <p className="text-muted-foreground">No active ports</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Process Details */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Running Processes</h3>
          <p className="card-description">
            Detailed view of all running processes
          </p>
        </div>
        <div className="card-content">
          {runtimeData?.projects && runtimeData.projects.some(p => p.processes.length > 0) ? (
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>PID</th>
                    <th>Process Name</th>
                    <th>Project</th>
                    <th>Status</th>
                    <th>CPU Usage</th>
                    <th>Memory Usage</th>
                    <th>Port</th>
                    <th>Started</th>
                  </tr>
                </thead>
                <tbody>
                  {runtimeData.projects.map((project) =>
                    project.processes.map((process) => (
                      <tr key={process.pid}>
                        <td className="font-mono">{process.pid}</td>
                        <td>{process.name}</td>
                        <td>{project.project_name}</td>
                        <td>
                          <StatusBadge status={process.status} variant="dot" />
                        </td>
                        <td>{process.cpu_usage?.toFixed(1)}%</td>
                        <td>{formatBytes((process.memory_usage_mb || 0) * 1024 * 1024)}</td>
                        <td>{process.port || '-'}</td>
                        <td className="text-sm text-muted-foreground">
                          {new Date(process.started_at).toLocaleTimeString()}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12">
              <Activity className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-xl font-semibold mb-2">No running processes</h3>
              <p className="text-muted-foreground">
                All projects are currently stopped
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}