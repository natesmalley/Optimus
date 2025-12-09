/**
 * Orchestration service for managing project lifecycle operations
 * Handles project launching, stopping, environment switching, and resource management
 */

import { api } from '../lib/api';
import type {
  OrchestrationStatus,
  LaunchProjectRequest,
  LaunchResponse,
  StopProjectRequest,
  SwitchEnvironmentRequest,
  EnvironmentConfig,
  ResourceAllocation,
  ResourceAllocationRequest,
} from '../types/api';

class OrchestrationService {
  /**
   * Launch a project with optional environment and configuration
   */
  async launchProject(
    projectId: string,
    options: LaunchProjectRequest = {}
  ): Promise<LaunchResponse> {
    const response = await api.post(`/api/orchestration/launch/${projectId}`, options);
    return response.data;
  }

  /**
   * Stop a running project
   */
  async stopProject(
    projectId: string,
    options: StopProjectRequest = {}
  ): Promise<{ success: boolean; message: string }> {
    const response = await api.post(`/api/orchestration/stop/${projectId}`, options);
    return response.data;
  }

  /**
   * Get current orchestration status for a project
   */
  async getProjectStatus(projectId: string): Promise<OrchestrationStatus> {
    const response = await api.get(`/api/orchestration/status/${projectId}`);
    return response.data;
  }

  /**
   * Get orchestration status for all projects
   */
  async getAllProjectStatuses(): Promise<OrchestrationStatus[]> {
    const response = await api.get('/api/orchestration/status');
    return response.data;
  }

  /**
   * Switch project environment
   */
  async switchEnvironment(
    projectId: string,
    request: SwitchEnvironmentRequest
  ): Promise<{ success: boolean; message: string; environment: string }> {
    const response = await api.post(
      `/api/orchestration/environments/${projectId}/switch`,
      request
    );
    return response.data;
  }

  /**
   * Get current environment configuration
   */
  async getCurrentEnvironment(projectId: string): Promise<EnvironmentConfig> {
    const response = await api.get(`/api/orchestration/environments/${projectId}`);
    return response.data;
  }

  /**
   * Get available environments for a project
   */
  async getAvailableEnvironments(projectId: string): Promise<EnvironmentConfig[]> {
    const response = await api.get(`/api/orchestration/environments/${projectId}/available`);
    return response.data;
  }

  /**
   * Allocate resources to a project
   */
  async allocateResources(
    projectId: string,
    allocation: ResourceAllocationRequest
  ): Promise<{ success: boolean; message: string }> {
    const response = await api.post('/api/orchestration/resources/allocate', {
      project_id: projectId,
      ...allocation,
    });
    return response.data;
  }

  /**
   * Get current resource usage and allocation
   */
  async getResourceUsage(projectId: string): Promise<ResourceAllocation> {
    const response = await api.get(`/api/orchestration/resources/${projectId}`);
    return response.data;
  }

  /**
   * Get resource usage for all projects
   */
  async getAllResourceUsage(): Promise<ResourceAllocation[]> {
    const response = await api.get('/api/orchestration/resources');
    return response.data;
  }

  /**
   * Get system-wide resource summary
   */
  async getSystemResourceSummary(): Promise<{
    total_cpu_usage: number;
    total_memory_usage: number;
    available_cpu: number;
    available_memory: number;
    projects_count: number;
    running_projects: number;
  }> {
    const response = await api.get('/api/orchestration/resources/summary');
    return response.data;
  }

  /**
   * Restart a project (stop and start)
   */
  async restartProject(
    projectId: string,
    environment?: string
  ): Promise<LaunchResponse> {
    try {
      // First stop the project
      await this.stopProject(projectId, { timeout: 30 });
      
      // Wait a moment for cleanup
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Then start it again
      const launchOptions: LaunchProjectRequest = {
        wait_for_health: true,
      };
      
      if (environment) {
        launchOptions.environment = environment;
      }
      
      return await this.launchProject(projectId, launchOptions);
    } catch (error) {
      throw new Error(`Failed to restart project: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Quick health check for a project
   */
  async healthCheck(projectId: string): Promise<{
    healthy: boolean;
    status: string;
    response_time?: number;
    last_check: string;
    details?: Record<string, any>;
  }> {
    const response = await api.get(`/api/orchestration/health/${projectId}`);
    return response.data;
  }

  /**
   * Get project startup logs
   */
  async getStartupLogs(projectId: string, lines = 100): Promise<{
    logs: string[];
    total_lines: number;
    last_updated: string;
  }> {
    const response = await api.get(`/api/orchestration/logs/${projectId}?lines=${lines}`);
    return response.data;
  }

  /**
   * Kill a specific process associated with a project
   */
  async killProcess(projectId: string, pid: number): Promise<{
    success: boolean;
    message: string;
  }> {
    const response = await api.post(`/api/orchestration/kill-process/${projectId}`, { pid });
    return response.data;
  }
}

// Export singleton instance
export const orchestrationService = new OrchestrationService();
export default orchestrationService;