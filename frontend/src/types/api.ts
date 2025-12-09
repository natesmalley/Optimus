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

// Council of Minds types
export interface DeliberationRequest {
  query: string;
  context?: Record<string, any>;
  topic?: string;
  required_personas?: string[];
  consensus_method?: string;
  timeout?: number;
}

export interface PersonaResponse {
  persona_id: string;
  name: string;
  recommendation: string;
  confidence: number;
  reasoning: string;
  concerns: string[];
  opportunities: string[];
  data_points: string[];
  priority: string;
}

export interface ConsensusResult {
  decision: string;
  confidence: number;
  agreement_level: number;
  method_used: string;
  supporting_personas: string[];
  dissenting_personas: string[];
  alternative_views: Record<string, string>;
  reasoning: string;
}

export interface DeliberationResponse {
  id: string;
  query: string;
  decision: string;
  confidence: number;
  agreement_level: number;
  deliberation_time: number;
  personas_consulted: number;
  timestamp: string;
  consensus_details: ConsensusResult;
  supporting_personas: string[];
  dissenting_personas: string[];
  alternative_views: Record<string, string>;
  statistics: Record<string, any>;
}

export interface PersonaInfo {
  id: string;
  name: string;
  description: string;
  expertise_domains: string[];
  personality_traits: string[];
}

export interface CouncilPerformance {
  timestamp: string;
  personas: Record<string, PersonaPerformanceMetrics>;
}

export interface PersonaPerformanceMetrics {
  name: string;
  participation_count: number;
  consensus_rate: number;
  dissent_rate: number;
  avg_confidence: number;
  expertise_domains: string[];
}

export interface DeliberationHistory {
  timestamp: string;
  deliberations: Array<{
    query: string;
    decision: string;
    confidence: number;
    agreement: number;
    time_taken: number;
    personas_consulted: number;
    timestamp: string;
    consensus_details: ConsensusResult;
    statistics: Record<string, any>;
  }>;
  total: number;
}

export interface CouncilHealthCheck {
  status: string;
  timestamp: string;
  orchestrator: {
    initialized: boolean;
    personas_loaded: number;
    deliberations_processed: number;
  };
  personas: Record<string, {
    name: string;
    blackboard_connected: boolean;
    decisions_made: number;
    memory_size: number;
  }>;
}

// WebSocket message types for real-time deliberations
export interface WebSocketMessage {
  type: 'deliberation_start' | 'persona_response' | 'consensus_update' | 'deliberation_complete' | 'error';
  data: any;
  timestamp: string;
}

export interface DeliberationProgress {
  deliberation_id: string;
  stage: 'starting' | 'gathering_responses' | 'reaching_consensus' | 'complete';
  personas_completed: string[];
  total_personas: number;
  current_confidence?: number;
}

// Orchestration types
export interface OrchestrationStatus {
  project_id: string;
  project_name: string;
  is_running: boolean;
  environment: 'dev' | 'staging' | 'prod';
  start_time?: string;
  pid?: number;
  port?: number;
  health_check_url?: string;
  last_heartbeat?: string;
  cpu_usage?: number;
  memory_usage?: number;
  status_details?: string;
}

export interface ResourceAllocation {
  project_id: string;
  cpu_limit?: number;
  memory_limit?: number;
  storage_limit?: number;
  network_limit?: number;
  current_usage: {
    cpu_percent: number;
    memory_mb: number;
    storage_mb: number;
    network_kb: number;
  };
  recommendations?: {
    cpu?: number;
    memory?: number;
    storage?: number;
  };
}

export interface EnvironmentConfig {
  name: string;
  variables: Record<string, string>;
  secrets: Record<string, string>;
  config_files?: Record<string, string>;
  dependencies?: string[];
  services?: string[];
}

export interface DeploymentStatus {
  project_id: string;
  deployment_id: string;
  status: 'pending' | 'building' | 'deploying' | 'success' | 'failed' | 'rolling_back';
  environment: string;
  progress: number;
  steps: DeploymentStep[];
  start_time: string;
  end_time?: string;
  logs: string[];
  rollback_available?: boolean;
  version?: string;
  commit_hash?: string;
}

export interface DeploymentStep {
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  start_time?: string;
  end_time?: string;
  duration?: number;
  logs: string[];
  error_message?: string;
}

export interface BackupInfo {
  id: string;
  project_id: string;
  name: string;
  type: 'manual' | 'scheduled' | 'pre_deployment';
  size_mb: number;
  created_at: string;
  status: 'creating' | 'completed' | 'failed' | 'expired';
  includes: string[];
  excludes: string[];
  compression: string;
  retention_days: number;
  can_restore: boolean;
}

export interface BackupSchedule {
  id: string;
  project_id: string;
  name: string;
  cron_expression: string;
  enabled: boolean;
  backup_type: string;
  retention_days: number;
  includes: string[];
  excludes: string[];
  last_run?: string;
  next_run?: string;
}

// Request types for orchestration
export interface LaunchProjectRequest {
  environment?: string;
  variables?: Record<string, string>;
  debug?: boolean;
  wait_for_health?: boolean;
}

export interface StopProjectRequest {
  force?: boolean;
  timeout?: number;
}

export interface SwitchEnvironmentRequest {
  environment: string;
  variables?: Record<string, string>;
  restart_if_running?: boolean;
}

export interface ResourceAllocationRequest {
  cpu_limit?: number;
  memory_limit?: number;
  storage_limit?: number;
  priority?: 'low' | 'normal' | 'high';
}

export interface DeploymentRequest {
  environment: string;
  version?: string;
  commit_hash?: string;
  variables?: Record<string, string>;
  strategy?: 'rolling' | 'blue_green' | 'recreate';
  health_check_timeout?: number;
}

export interface BackupRequest {
  name?: string;
  includes?: string[];
  excludes?: string[];
  compression?: string;
  retention_days?: number;
}

// Response types for orchestration
export interface LaunchResponse {
  success: boolean;
  message: string;
  pid?: number;
  port?: number;
  health_check_url?: string;
  environment: string;
}

export interface DeploymentResponse {
  deployment_id: string;
  status: string;
  message: string;
  estimated_duration?: number;
}

export interface BackupResponse {
  backup_id: string;
  status: string;
  message: string;
  estimated_size_mb?: number;
}

// WebSocket message types for orchestration
export interface OrchestrationWebSocketMessage extends WebSocketMessage {
  type: 'project_status_change' | 'resource_update' | 'deployment_progress' | 'backup_progress' | 'environment_switch' | 'error';
  project_id?: string;
  data: {
    status?: OrchestrationStatus;
    resources?: ResourceAllocation;
    deployment?: DeploymentStatus;
    backup?: BackupInfo;
    environment?: string;
    error?: string;
  };
}