/**
 * TypeScript definitions for the Optimus API
 * Generated from backend API models
 */

// Base types
export interface Project {
  id: string;
  name: string;
  path: string;
  description?: string;
  tech_stack: Record<string, any>;
  dependencies: Record<string, any>;
  status: string;
  git_url?: string;
  default_branch: string;
  last_commit_hash?: string;
  language_stats: Record<string, any>;
  last_scanned?: string;
  created_at: string;
  updated_at: string;
  
  // Runtime information
  is_running: boolean;
  process_count: number;
  running_ports: number[];
  
  // Analysis information
  latest_quality_score?: number;
  open_issues_count: number;
  monetization_opportunities: number;
}

export interface ProjectDetail extends Project {
  runtime_processes: ProcessInfo[];
  recent_analysis: AnalysisResult[];
  monetization_summary: MonetizationSummary;
}

export interface ProcessInfo {
  pid: number;
  name: string;
  status: string;
  cpu_usage?: number;
  memory_usage_mb?: number;
  port?: number;
  started_at: string;
  last_heartbeat: string;
}

export interface AnalysisResult {
  id: string;
  analysis_type: string;
  score?: number;
  issues_count: number;
  results: Record<string, any>;
  analyzer_version: string;
  created_at: string;
  grade: string;
  is_passing: boolean;
}

export interface MonetizationOpportunity {
  id: string;
  opportunity_type: string;
  description: string;
  potential_revenue?: number;
  effort_required: string;
  priority: number;
  status: string;
  confidence_score?: number;
  opportunity_score: number;
  risk_level: string;
  created_at: string;
  updated_at: string;
}

export interface MonetizationSummary {
  total_opportunities: number;
  active_opportunities: number;
  total_potential_revenue: number;
  highest_priority: number;
}

// API Response types
export interface ProjectListResponse {
  projects: Project[];
  total: number;
  page: number;
  size: number;
}

export interface RuntimeSummary {
  project_id: string;
  project_name: string;
  is_running: boolean;
  process_count: number;
  total_cpu_usage: number;
  total_memory_usage_mb: number;
  ports: number[];
  processes: ProcessInfo[];
}

export interface SystemRuntimeResponse {
  total_projects: number;
  running_projects: number;
  total_processes: number;
  total_cpu_usage: number;
  total_memory_usage_mb: number;
  projects: RuntimeSummary[];
}

// Metrics types
export interface MetricPoint {
  timestamp: string;
  value: number;
  unit?: string;
  metadata: Record<string, any>;
}

export interface MetricSeries {
  metric_type: string;
  project_id: string;
  project_name: string;
  data_points: MetricPoint[];
  summary: Record<string, any>;
}

export interface ProjectMetricsResponse {
  project_id: string;
  project_name: string;
  metrics: MetricSeries[];
  period: string;
  total_points: number;
}

export interface HealthScoreResponse {
  project_id: string;
  project_name: string;
  overall_score: number;
  components: Record<string, number>;
  last_updated: string;
  grade: string;
}

export interface TrendAnalysis {
  project_id: string;
  project_name: string;
  trend_direction: 'increasing' | 'decreasing' | 'stable' | 'insufficient_data';
  trend_slope: number;
  value_count: number;
  latest_value?: number;
  min_value?: number;
  max_value?: number;
  avg_value?: number;
}

export interface TrendsResponse {
  metric_type: string;
  period: string;
  trends: TrendAnalysis[];
  summary: Record<string, any>;
}

// Request types
export interface ProjectFilters {
  page?: number;
  size?: number;
  status?: string;
  tech_stack?: string;
  search?: string;
}

export interface MetricFilters {
  metric_types?: string[];
  period?: string;
  project_ids?: string[];
}

// Utility types
export type ProjectStatus = 'active' | 'discovered' | 'archived' | 'error';
export type ProcessStatus = 'running' | 'starting' | 'stopped' | 'error';
export type MetricPeriod = '1h' | '24h' | '7d' | '30d' | '90d';
export type AnalysisType = 'code_quality' | 'security' | 'performance' | 'dependencies';
export type OpportunityStatus = 'identified' | 'evaluating' | 'in_progress' | 'completed' | 'dismissed';

// Error types
export interface ApiError {
  detail: string;
  status?: number;
}

// Dashboard specific types
export interface DashboardStats {
  total_projects: number;
  running_projects: number;
  total_processes: number;
  avg_health_score: number;
  total_revenue_potential: number;
  critical_issues: number;
}

export interface TechStackStats {
  language: string;
  count: number;
  percentage: number;
  health_score: number;
}