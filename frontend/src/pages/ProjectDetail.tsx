import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { 
  ArrowLeft, 
  Play, 
  Square, 
  Settings, 
  GitBranch, 
  Clock,
  AlertTriangle,
  TrendingUp,
  DollarSign,
  Cpu,
  MemoryStick,
  Activity
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { formatRelativeTime, formatBytes, getStatusColor, getHealthScoreColor } from '@/lib/utils';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import StatusBadge from '@/components/ui/StatusBadge';

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>();

  const { data: project, isLoading, error } = useQuery({
    queryKey: ['project', id],
    queryFn: () => apiClient.getProject(id!),
    enabled: !!id,
  });

  const { data: healthScore } = useQuery({
    queryKey: ['project-health', id],
    queryFn: () => apiClient.getProjectHealthScore(id!),
    enabled: !!id,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">Project not found</h3>
          <p className="text-muted-foreground">
            {error instanceof Error ? error.message : 'The project could not be loaded'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center space-x-4 mb-6">
        <button className="btn btn-ghost btn-sm">
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div className="flex-1">
          <h1 className="text-3xl font-bold">{project.name}</h1>
          <p className="text-muted-foreground mt-1">
            {project.description || 'No description available'}
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <StatusBadge status={project.status} />
          <button className="btn btn-outline">
            <Settings className="w-4 h-4 mr-2" />
            Settings
          </button>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="card">
          <div className="card-content p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Health Score</p>
                <p className={`text-2xl font-bold ${healthScore ? getHealthScoreColor(healthScore.overall_score) : ''}`}>
                  {healthScore ? `${healthScore.overall_score}/100` : 'N/A'}
                </p>
                <p className="text-xs text-muted-foreground">
                  Grade: {healthScore?.grade || 'N/A'}
                </p>
              </div>
              <TrendingUp className="w-8 h-8 text-primary" />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-content p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Running Processes</p>
                <p className="text-2xl font-bold">{project.process_count}</p>
                <p className="text-xs text-muted-foreground">
                  {project.is_running ? 'Active' : 'Inactive'}
                </p>
              </div>
              <Activity className="w-8 h-8 text-primary" />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-content p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Monetization</p>
                <p className="text-2xl font-bold">{project.monetization_opportunities}</p>
                <p className="text-xs text-muted-foreground">Opportunities</p>
              </div>
              <DollarSign className="w-8 h-8 text-primary" />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-content p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Last Updated</p>
                <p className="text-2xl font-bold text-sm">
                  {project.last_scanned ? formatRelativeTime(project.last_scanned) : 'Never'}
                </p>
                <p className="text-xs text-muted-foreground">Last scan</p>
              </div>
              <Clock className="w-8 h-8 text-primary" />
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Runtime Processes */}
        <div className="lg:col-span-2">
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Runtime Processes</h3>
              <p className="card-description">
                Currently running processes for this project
              </p>
            </div>
            <div className="card-content">
              {project.runtime_processes?.length > 0 ? (
                <div className="space-y-4">
                  {project.runtime_processes.map((process) => (
                    <div key={process.pid} className="flex items-center justify-between p-4 border border-border rounded-lg">
                      <div className="flex items-center space-x-4">
                        <div className="w-10 h-10 bg-muted rounded-lg flex items-center justify-center">
                          <Cpu className="w-5 h-5" />
                        </div>
                        <div>
                          <p className="font-medium">{process.name}</p>
                          <p className="text-sm text-muted-foreground">PID: {process.pid}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="flex items-center space-x-4 text-sm">
                          <div>
                            <span className="text-muted-foreground">CPU:</span> {process.cpu_usage?.toFixed(1)}%
                          </div>
                          <div>
                            <span className="text-muted-foreground">Memory:</span> {formatBytes((process.memory_usage_mb || 0) * 1024 * 1024)}
                          </div>
                          {process.port && (
                            <div>
                              <span className="text-muted-foreground">Port:</span> {process.port}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8">
                  <Square className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground">No processes running</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Project Info */}
        <div className="space-y-6">
          {/* Basic Info */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Project Information</h3>
            </div>
            <div className="card-content">
              <div className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground">Path</p>
                  <p className="font-mono text-sm break-all">{project.path}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Git Branch</p>
                  <div className="flex items-center space-x-2">
                    <GitBranch className="w-4 h-4" />
                    <span className="text-sm">{project.default_branch}</span>
                  </div>
                </div>
                {project.git_url && (
                  <div>
                    <p className="text-sm text-muted-foreground">Repository</p>
                    <a 
                      href={project.git_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-primary hover:underline break-all"
                    >
                      {project.git_url}
                    </a>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Tech Stack */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Technology Stack</h3>
            </div>
            <div className="card-content">
              <div className="space-y-2">
                {Object.entries(project.tech_stack).map(([tech, info]) => (
                  <div key={tech} className="flex items-center justify-between">
                    <span className="text-sm capitalize">{tech}</span>
                    <span className="text-xs text-muted-foreground">
                      {typeof info === 'string' ? info : JSON.stringify(info)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Health Components */}
          {healthScore && (
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Health Components</h3>
              </div>
              <div className="card-content">
                <div className="space-y-3">
                  {Object.entries(healthScore.components).map(([component, score]) => (
                    <div key={component} className="flex items-center justify-between">
                      <span className="text-sm capitalize">{component.replace('_', ' ')}</span>
                      <div className="flex items-center space-x-2">
                        <div className="w-20 h-2 bg-muted rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500 transition-all"
                            style={{ width: `${score}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium w-10 text-right">{score.toFixed(0)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}