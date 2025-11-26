import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  TrendingUp, 
  BarChart3, 
  PieChart,
  Calendar,
  Filter,
  Download,
  AlertTriangle
} from 'lucide-react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart as RechartsPieChart,
  Cell,
  BarChart,
  Bar,
  LineChart,
  Line
} from 'recharts';
import { apiClient } from '@/lib/api';
import { cn } from '@/lib/utils';
import LoadingSpinner from '@/components/ui/LoadingSpinner';

// Sample data for charts (would be replaced with real API data)
const performanceData = [
  { name: 'Jan', value: 85 },
  { name: 'Feb', value: 88 },
  { name: 'Mar', value: 92 },
  { name: 'Apr', value: 87 },
  { name: 'May', value: 94 },
  { name: 'Jun', value: 91 },
];

const techStackData = [
  { name: 'React', value: 35, color: '#61dafb' },
  { name: 'Python', value: 28, color: '#3776ab' },
  { name: 'Node.js', value: 22, color: '#339933' },
  { name: 'Java', value: 10, color: '#f89820' },
  { name: 'Other', value: 5, color: '#8884d8' },
];

const healthTrendsData = [
  { name: 'Week 1', code_quality: 78, security: 85, performance: 82 },
  { name: 'Week 2', code_quality: 82, security: 87, performance: 85 },
  { name: 'Week 3', code_quality: 85, security: 89, performance: 88 },
  { name: 'Week 4', code_quality: 88, security: 91, performance: 90 },
];

const activityData = [
  { hour: '00', commits: 2 },
  { hour: '04', commits: 1 },
  { hour: '08', commits: 12 },
  { hour: '12', commits: 25 },
  { hour: '16', commits: 18 },
  { hour: '20', commits: 8 },
];

export default function Analytics() {
  const [selectedPeriod, setSelectedPeriod] = useState('7d');
  const [selectedMetric, setSelectedMetric] = useState('performance');

  const { data: projectsData, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => apiClient.getProjects(),
  });

  const { data: systemMetrics } = useQuery({
    queryKey: ['system-metrics', selectedPeriod],
    queryFn: () => apiClient.getSystemMetrics({ period: selectedPeriod }),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold">Analytics Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Project health scores, technology trends, and performance insights
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <select 
            value={selectedPeriod}
            onChange={(e) => setSelectedPeriod(e.target.value)}
            className="input"
          >
            <option value="1h">Last Hour</option>
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
          </select>
          <button className="btn btn-outline">
            <Download className="w-4 h-4 mr-2" />
            Export
          </button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="card">
          <div className="card-content p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Avg Health Score</p>
                <p className="text-2xl font-bold text-green-600">87.5</p>
                <div className="flex items-center space-x-1 mt-1">
                  <TrendingUp className="w-3 h-3 text-green-600" />
                  <span className="text-xs text-green-600">+5.2% this week</span>
                </div>
              </div>
              <BarChart3 className="w-8 h-8 text-green-500" />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-content p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Critical Issues</p>
                <p className="text-2xl font-bold text-red-600">3</p>
                <div className="flex items-center space-x-1 mt-1">
                  <span className="text-xs text-red-600">-2 from last week</span>
                </div>
              </div>
              <AlertTriangle className="w-8 h-8 text-red-500" />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-content p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Revenue Potential</p>
                <p className="text-2xl font-bold text-blue-600">$45K</p>
                <div className="flex items-center space-x-1 mt-1">
                  <span className="text-xs text-blue-600">12 opportunities</span>
                </div>
              </div>
              <TrendingUp className="w-8 h-8 text-blue-500" />
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-content p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Active Projects</p>
                <p className="text-2xl font-bold text-purple-600">
                  {projectsData?.projects?.length || 0}
                </p>
                <div className="flex items-center space-x-1 mt-1">
                  <span className="text-xs text-purple-600">
                    {projectsData?.projects?.filter(p => p.is_running).length || 0} running
                  </span>
                </div>
              </div>
              <PieChart className="w-8 h-8 text-purple-500" />
            </div>
          </div>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Performance Trends */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Performance Trends</h3>
            <p className="card-description">
              Average performance scores over time
            </p>
          </div>
          <div className="card-content">
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={performanceData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Area 
                  type="monotone" 
                  dataKey="value" 
                  stroke="#3b82f6" 
                  fill="#3b82f6" 
                  fillOpacity={0.2} 
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Technology Distribution */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Technology Stack Distribution</h3>
            <p className="card-description">
              Primary technologies across all projects
            </p>
          </div>
          <div className="card-content">
            <ResponsiveContainer width="100%" height={300}>
              <RechartsPieChart>
                <Tooltip />
                <RechartsPieChart
                  data={techStackData}
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {techStackData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </RechartsPieChart>
              </RechartsPieChart>
            </ResponsiveContainer>
            <div className="mt-4 grid grid-cols-2 gap-2">
              {techStackData.map((tech) => (
                <div key={tech.name} className="flex items-center space-x-2">
                  <div 
                    className="w-3 h-3 rounded-full" 
                    style={{ backgroundColor: tech.color }}
                  />
                  <span className="text-sm">{tech.name}</span>
                  <span className="text-xs text-muted-foreground">({tech.value}%)</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Health Score Trends */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Health Score Components</h3>
            <p className="card-description">
              Tracking different health aspects over time
            </p>
          </div>
          <div className="card-content">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={healthTrendsData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="code_quality" stroke="#10b981" name="Code Quality" />
                <Line type="monotone" dataKey="security" stroke="#3b82f6" name="Security" />
                <Line type="monotone" dataKey="performance" stroke="#f59e0b" name="Performance" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Activity Heatmap */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Development Activity</h3>
            <p className="card-description">
              Commit activity throughout the day
            </p>
          </div>
          <div className="card-content">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={activityData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hour" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="commits" fill="#8b5cf6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Project Health Table */}
      <div className="card mt-6">
        <div className="card-header">
          <h3 className="card-title">Project Health Overview</h3>
          <p className="card-description">
            Individual project health scores and key metrics
          </p>
        </div>
        <div className="card-content">
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Project</th>
                  <th>Health Score</th>
                  <th>Status</th>
                  <th>Technology</th>
                  <th>Last Updated</th>
                  <th>Issues</th>
                  <th>Opportunities</th>
                </tr>
              </thead>
              <tbody>
                {projectsData?.projects?.slice(0, 10).map((project) => (
                  <tr key={project.id}>
                    <td className="font-medium">{project.name}</td>
                    <td>
                      <div className="flex items-center space-x-2">
                        <div className="w-12 h-2 bg-muted rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500"
                            style={{ width: `${project.latest_quality_score || 50}%` }}
                          />
                        </div>
                        <span className="text-sm">
                          {project.latest_quality_score?.toFixed(0) || 'N/A'}
                        </span>
                      </div>
                    </td>
                    <td>
                      <div className="flex items-center space-x-2">
                        <div className={cn(
                          "w-2 h-2 rounded-full",
                          project.is_running ? "bg-green-500" : "bg-gray-400"
                        )} />
                        <span className="text-sm capitalize">{project.status}</span>
                      </div>
                    </td>
                    <td className="text-sm">
                      {Object.keys(project.tech_stack)[0] || 'Unknown'}
                    </td>
                    <td className="text-sm text-muted-foreground">
                      {project.last_scanned ? new Date(project.last_scanned).toLocaleDateString() : 'Never'}
                    </td>
                    <td className="text-sm">
                      {project.open_issues_count}
                    </td>
                    <td className="text-sm">
                      {project.monetization_opportunities}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}