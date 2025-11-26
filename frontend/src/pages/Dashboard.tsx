import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  Plus, 
  Search, 
  Filter, 
  Grid3X3, 
  List,
  Loader2,
  AlertTriangle,
  Scan,
  Play,
  Square,
  Settings,
  MoreVertical,
  FolderOpen,
  GitBranch,
  Clock,
  Zap
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { useProjectsStore, useDashboardStore, useToastStore } from '@/store';
import { cn, formatRelativeTime, formatBytes, getStatusColor, getTechIcon } from '@/lib/utils';
import LoadingSpinner from '@/components/ui/LoadingSpinner';
import StatusBadge from '@/components/ui/StatusBadge';
import type { Project } from '@/types';

// Dashboard stats component
function DashboardStats() {
  const { data: runtimeData } = useQuery({
    queryKey: ['runtime-overview'],
    queryFn: () => apiClient.getRuntimeOverview(),
    refetchInterval: 30000,
  });

  const stats = [
    {
      title: 'Total Projects',
      value: runtimeData?.total_projects || 0,
      change: +5,
      changeType: 'increase' as const,
      icon: FolderOpen,
    },
    {
      title: 'Running Projects',
      value: runtimeData?.running_projects || 0,
      change: +2,
      changeType: 'increase' as const,
      icon: Play,
    },
    {
      title: 'Total Processes',
      value: runtimeData?.total_processes || 0,
      change: -1,
      changeType: 'decrease' as const,
      icon: Zap,
    },
    {
      title: 'Memory Usage',
      value: formatBytes((runtimeData?.total_memory_usage_mb || 0) * 1024 * 1024),
      change: +12.5,
      changeType: 'increase' as const,
      icon: Settings,
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
      {stats.map((stat) => {
        const Icon = stat.icon;
        return (
          <div key={stat.title} className="card">
            <div className="card-content p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">{stat.title}</p>
                  <p className="text-2xl font-bold">{stat.value}</p>
                  <div className="flex items-center space-x-1 mt-1">
                    <span
                      className={cn(
                        "text-xs font-medium",
                        stat.changeType === 'increase' ? 'text-green-600' : 'text-red-600'
                      )}
                    >
                      {stat.changeType === 'increase' ? '+' : '-'}{Math.abs(stat.change)}%
                    </span>
                    <span className="text-xs text-muted-foreground">vs last week</span>
                  </div>
                </div>
                <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center">
                  <Icon className="w-6 h-6 text-primary" />
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Project filters component
function ProjectFilters() {
  const { filters, setFilters } = useProjectsStore();
  const [showFilters, setShowFilters] = useState(false);

  return (
    <div className="flex items-center space-x-4 mb-6">
      <div className="relative flex-1 max-w-md">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
        <input
          type="text"
          placeholder="Search projects..."
          value={filters.search}
          onChange={(e) => setFilters({ search: e.target.value })}
          className="input pl-10 w-full"
        />
      </div>

      <button
        onClick={() => setShowFilters(!showFilters)}
        className={cn("btn btn-outline", showFilters && "bg-accent")}
      >
        <Filter className="w-4 h-4 mr-2" />
        Filters
      </button>

      {showFilters && (
        <div className="absolute top-full left-0 mt-2 w-full bg-card border border-border rounded-lg shadow-lg p-4 z-10">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Status</label>
              <select className="input">
                <option value="">All statuses</option>
                <option value="active">Active</option>
                <option value="running">Running</option>
                <option value="stopped">Stopped</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Technology</label>
              <select className="input">
                <option value="">All technologies</option>
                <option value="react">React</option>
                <option value="node">Node.js</option>
                <option value="python">Python</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Sort by</label>
              <select className="input">
                <option value="updated">Last Updated</option>
                <option value="name">Name</option>
                <option value="status">Status</option>
              </select>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Project card component
function ProjectCard({ project }: { project: Project }) {
  const { addToast } = useToastStore();

  const handleScan = async () => {
    try {
      await apiClient.scanProject(project.id);
      addToast({
        type: 'success',
        title: 'Project scanned',
        description: `${project.name} has been scanned successfully`,
      });
    } catch (error) {
      addToast({
        type: 'error',
        title: 'Scan failed',
        description: error instanceof Error ? error.message : 'Unknown error',
      });
    }
  };

  const primaryTech = Object.keys(project.tech_stack)[0] || 'unknown';

  return (
    <div className="card hover:shadow-lg transition-shadow">
      <div className="card-content p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <h3 className="text-lg font-semibold mb-1">{project.name}</h3>
            <p className="text-sm text-muted-foreground line-clamp-2">
              {project.description || 'No description available'}
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <StatusBadge status={project.status} />
            <button className="btn btn-ghost btn-sm">
              <MoreVertical className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Technology stack */}
        <div className="flex items-center space-x-2 mb-4">
          <div className="w-6 h-6 bg-muted rounded flex items-center justify-center">
            <span className="text-xs">{primaryTech.charAt(0).toUpperCase()}</span>
          </div>
          <span className="text-sm text-muted-foreground capitalize">{primaryTech}</span>
          {Object.keys(project.tech_stack).length > 1 && (
            <span className="text-xs text-muted-foreground">
              +{Object.keys(project.tech_stack).length - 1} more
            </span>
          )}
        </div>

        {/* Runtime info */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <div className="text-xs text-muted-foreground mb-1">Running</div>
            <div className="flex items-center space-x-1">
              <div
                className={cn(
                  "w-2 h-2 rounded-full",
                  project.is_running ? "bg-green-500" : "bg-gray-400"
                )}
              />
              <span className="text-sm">
                {project.is_running ? 'Yes' : 'No'}
              </span>
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground mb-1">Processes</div>
            <div className="text-sm">{project.process_count}</div>
          </div>
        </div>

        {/* Git info */}
        <div className="flex items-center space-x-4 mb-4 text-xs text-muted-foreground">
          <div className="flex items-center space-x-1">
            <GitBranch className="w-3 h-3" />
            <span>{project.default_branch}</span>
          </div>
          {project.last_scanned && (
            <div className="flex items-center space-x-1">
              <Clock className="w-3 h-3" />
              <span>{formatRelativeTime(project.last_scanned)}</span>
            </div>
          )}
        </div>

        {/* Quality indicators */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            {project.latest_quality_score && (
              <div className="text-xs">
                <span className="text-muted-foreground">Quality:</span>{' '}
                <span className="font-medium">{project.latest_quality_score.toFixed(1)}/100</span>
              </div>
            )}
          </div>
          <div className="flex items-center space-x-2">
            {project.monetization_opportunities > 0 && (
              <span className="badge badge-secondary text-xs">
                ${project.monetization_opportunities} opportunities
              </span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center space-x-2">
          <button
            onClick={handleScan}
            className="btn btn-outline btn-sm flex-1"
          >
            <Scan className="w-4 h-4 mr-1" />
            Scan
          </button>
          <button className="btn btn-secondary btn-sm flex-1">
            <FolderOpen className="w-4 h-4 mr-1" />
            Open
          </button>
        </div>
      </div>
    </div>
  );
}

// Main dashboard component
export default function Dashboard() {
  const { viewMode, setViewMode } = useDashboardStore();
  const { filters, pagination } = useProjectsStore();

  const { data: projectsData, isLoading, error } = useQuery({
    queryKey: ['projects', filters, pagination],
    queryFn: () => apiClient.getProjects({
      ...filters,
      page: pagination.page,
      size: pagination.size,
    }),
    refetchInterval: 30000,
  });

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">Failed to load projects</h3>
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
          <h1 className="text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Manage and monitor your development projects
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <div className="flex items-center border border-border rounded-lg">
            <button
              onClick={() => setViewMode('grid')}
              className={cn(
                "btn btn-ghost btn-sm rounded-r-none",
                viewMode === 'grid' && "bg-accent"
              )}
            >
              <Grid3X3 className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={cn(
                "btn btn-ghost btn-sm rounded-l-none border-l border-border",
                viewMode === 'list' && "bg-accent"
              )}
            >
              <List className="w-4 h-4" />
            </button>
          </div>
          <button className="btn btn-default">
            <Plus className="w-4 h-4 mr-2" />
            Add Project
          </button>
        </div>
      </div>

      <DashboardStats />
      <ProjectFilters />

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <LoadingSpinner size="lg" />
        </div>
      ) : projectsData?.projects.length === 0 ? (
        <div className="text-center py-12">
          <FolderOpen className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-xl font-semibold mb-2">No projects found</h3>
          <p className="text-muted-foreground mb-4">
            Get started by adding your first project or scanning your workspace
          </p>
          <button className="btn btn-default">
            <Plus className="w-4 h-4 mr-2" />
            Add Project
          </button>
        </div>
      ) : (
        <div
          className={cn(
            viewMode === 'grid'
              ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6'
              : 'space-y-4'
          )}
        >
          {projectsData?.projects.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {projectsData && projectsData.total > projectsData.size && (
        <div className="flex items-center justify-between mt-8">
          <div className="text-sm text-muted-foreground">
            Showing {((projectsData.page - 1) * projectsData.size) + 1} to{' '}
            {Math.min(projectsData.page * projectsData.size, projectsData.total)} of{' '}
            {projectsData.total} results
          </div>
          <div className="flex items-center space-x-2">
            <button 
              disabled={projectsData.page === 1}
              className="btn btn-outline btn-sm"
            >
              Previous
            </button>
            <span className="text-sm">
              Page {projectsData.page} of {Math.ceil(projectsData.total / projectsData.size)}
            </span>
            <button 
              disabled={projectsData.page * projectsData.size >= projectsData.total}
              className="btn btn-outline btn-sm"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}