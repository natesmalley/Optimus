/**
 * API client for Optimus backend
 * Handles all HTTP requests to the FastAPI backend
 */

import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios';
import type {
  ProjectListResponse,
  ProjectDetail,
  SystemRuntimeResponse,
  RuntimeSummary,
  ProjectMetricsResponse,
  HealthScoreResponse,
  TrendsResponse,
  ProjectFilters,
  MetricFilters,
  MonetizationOpportunity,
  DeliberationRequest,
  DeliberationResponse,
  PersonaInfo,
  CouncilPerformance,
  DeliberationHistory,
  CouncilHealthCheck,
} from '@/types';

class ApiClient {
  private client: AxiosInstance;

  constructor(baseURL: string = '/api/v1') {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000,
    });

    // Request interceptor for logging
    this.client.interceptors.request.use(
      (config) => {
        console.log(`🔄 API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        console.error('❌ API Request Error:', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => {
        console.log(`✅ API Response: ${response.config.method?.toUpperCase()} ${response.config.url} - ${response.status}`);
        return response;
      },
      (error: AxiosError) => {
        console.error(`❌ API Error: ${error.config?.method?.toUpperCase()} ${error.config?.url} - ${error.response?.status}`, error.response?.data);
        return Promise.reject(this.handleApiError(error));
      }
    );
  }

  private handleApiError(error: AxiosError): Error {
    if (error.response) {
      // Server responded with error status
      const message = (error.response.data as any)?.detail || error.message;
      return new Error(`API Error (${error.response.status}): ${message}`);
    } else if (error.request) {
      // Network error
      return new Error('Network Error: Unable to reach the server');
    } else {
      // Request setup error
      return new Error(`Request Error: ${error.message}`);
    }
  }

  // Projects API
  async getProjects(filters?: ProjectFilters): Promise<ProjectListResponse> {
    const response: AxiosResponse<ProjectListResponse> = await this.client.get('/projects', {
      params: filters,
    });
    return response.data;
  }

  async getProject(projectId: string): Promise<ProjectDetail> {
    const response: AxiosResponse<ProjectDetail> = await this.client.get(`/projects/${projectId}`);
    return response.data;
  }

  async scanProject(projectId: string): Promise<{ message: string; project_id: string; status: string }> {
    const response = await this.client.post(`/projects/${projectId}/scan`);
    return response.data;
  }

  async deleteProject(projectId: string): Promise<{ message: string; project_id: string; status: string }> {
    const response = await this.client.delete(`/projects/${projectId}`);
    return response.data;
  }

  async getProjectAnalysis(projectId: string, limit?: number): Promise<{
    project_id: string;
    analysis_results: any[];
    total: number;
  }> {
    const response = await this.client.get(`/projects/${projectId}/analysis`, {
      params: { limit },
    });
    return response.data;
  }

  async getProjectMonetization(projectId: string): Promise<{
    project_id: string;
    opportunities: MonetizationOpportunity[];
    summary: {
      total_opportunities: number;
      active_opportunities: number;
      total_potential_revenue: number;
      highest_priority: number;
    };
  }> {
    const response = await this.client.get(`/projects/${projectId}/monetization`);
    return response.data;
  }

  // Runtime API
  async getRuntimeOverview(runningOnly?: boolean): Promise<SystemRuntimeResponse> {
    const response: AxiosResponse<SystemRuntimeResponse> = await this.client.get('/runtime', {
      params: { running_only: runningOnly },
    });
    return response.data;
  }

  async getProjectRuntime(projectId: string): Promise<RuntimeSummary> {
    const response: AxiosResponse<RuntimeSummary> = await this.client.get(`/runtime/project/${projectId}`);
    return response.data;
  }

  async triggerMonitorCycle(): Promise<{
    timestamp: string;
    duration_seconds: number;
    processes_found: number;
    status: string;
    error?: string;
  }> {
    const response = await this.client.post('/runtime/monitor');
    return response.data;
  }

  async getAllProcesses(filters?: { status?: string; project_id?: string }): Promise<any[]> {
    const response = await this.client.get('/runtime/processes', {
      params: filters,
    });
    return response.data;
  }

  async stopProcessTracking(pid: number): Promise<{
    message: string;
    pid: number;
    status: string;
  }> {
    const response = await this.client.delete(`/runtime/process/${pid}`);
    return response.data;
  }

  async getRuntimeStats(): Promise<{
    status_counts: Record<string, number>;
    running_processes: number;
    total_cpu_usage: number;
    total_memory_usage_mb: number;
    active_ports: number[];
    port_count: number;
  }> {
    const response = await this.client.get('/runtime/stats');
    return response.data;
  }

  // Metrics API
  async getProjectMetrics(projectId: string, filters?: MetricFilters): Promise<ProjectMetricsResponse> {
    const response: AxiosResponse<ProjectMetricsResponse> = await this.client.get(`/metrics/projects/${projectId}`, {
      params: filters,
    });
    return response.data;
  }

  async getSystemMetrics(filters?: MetricFilters): Promise<{
    period: string;
    projects: ProjectMetricsResponse[];
    summary: Record<string, any>;
  }> {
    const response = await this.client.get('/metrics', {
      params: filters,
    });
    return response.data;
  }

  async getProjectHealthScore(projectId: string): Promise<HealthScoreResponse> {
    const response: AxiosResponse<HealthScoreResponse> = await this.client.get(`/metrics/health/${projectId}`);
    return response.data;
  }

  async getMetricsTrends(metricType: string, period?: string, projectIds?: string[]): Promise<TrendsResponse> {
    const response: AxiosResponse<TrendsResponse> = await this.client.get('/metrics/trends', {
      params: {
        metric_type: metricType,
        period,
        project_ids: projectIds,
      },
    });
    return response.data;
  }

  // Utility methods
  async healthCheck(): Promise<boolean> {
    try {
      await this.client.get('/health');
      return true;
    } catch {
      return false;
    }
  }

  // Get base URL for external links
  getBaseUrl(): string {
    return this.client.defaults.baseURL || '';
  }

  // Council of Minds API
  async submitDeliberation(request: DeliberationRequest): Promise<DeliberationResponse> {
    const response: AxiosResponse<DeliberationResponse> = await this.client.post('/council/deliberate', request);
    return response.data;
  }

  async getDeliberation(deliberationId: string): Promise<DeliberationResponse> {
    const response: AxiosResponse<DeliberationResponse> = await this.client.get(`/council/deliberations/${deliberationId}`);
    return response.data;
  }

  async getPersonas(): Promise<PersonaInfo[]> {
    const response: AxiosResponse<PersonaInfo[]> = await this.client.get('/council/personas');
    return response.data;
  }

  async getPersona(personaId: string): Promise<PersonaInfo> {
    const response: AxiosResponse<PersonaInfo> = await this.client.get(`/council/personas/${personaId}`);
    return response.data;
  }

  async getCouncilPerformance(): Promise<CouncilPerformance> {
    const response: AxiosResponse<CouncilPerformance> = await this.client.get('/council/performance');
    return response.data;
  }

  async getDeliberationHistory(limit?: number): Promise<DeliberationHistory> {
    const response: AxiosResponse<DeliberationHistory> = await this.client.get('/council/history', {
      params: { limit },
    });
    return response.data;
  }

  async getCouncilHealth(): Promise<CouncilHealthCheck> {
    const response: AxiosResponse<CouncilHealthCheck> = await this.client.get('/council/health/detailed');
    return response.data;
  }

  async resetCouncil(): Promise<{ status: string; message: string; timestamp: string }> {
    const response = await this.client.post('/council/reset');
    return response.data;
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export class for testing
export { ApiClient };