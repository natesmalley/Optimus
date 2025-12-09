/**
 * Deployment service for managing application deployments
 * Handles deployment pipeline management, status tracking, and rollback operations
 */

import { api } from '../lib/api';
import type {
  DeploymentStatus,
  DeploymentRequest,
  DeploymentResponse,
  DeploymentStep,
} from '../types/api';

class DeploymentService {
  /**
   * Start a new deployment
   */
  async deploy(
    projectId: string,
    deployment: DeploymentRequest
  ): Promise<DeploymentResponse> {
    const response = await api.post(`/api/orchestration/deploy/${projectId}`, deployment);
    return response.data;
  }

  /**
   * Get deployment status
   */
  async getDeploymentStatus(
    projectId: string,
    deploymentId?: string
  ): Promise<DeploymentStatus> {
    const url = deploymentId
      ? `/api/orchestration/deploy/${projectId}/status/${deploymentId}`
      : `/api/orchestration/deploy/${projectId}/status`;
    
    const response = await api.get(url);
    return response.data;
  }

  /**
   * Get deployment history for a project
   */
  async getDeploymentHistory(
    projectId: string,
    limit = 20
  ): Promise<DeploymentStatus[]> {
    const response = await api.get(
      `/api/orchestration/deploy/${projectId}/history?limit=${limit}`
    );
    return response.data;
  }

  /**
   * Cancel a running deployment
   */
  async cancelDeployment(
    projectId: string,
    deploymentId: string
  ): Promise<{ success: boolean; message: string }> {
    const response = await api.post(
      `/api/orchestration/deploy/${projectId}/cancel/${deploymentId}`
    );
    return response.data;
  }

  /**
   * Rollback to previous deployment
   */
  async rollback(
    projectId: string,
    targetDeploymentId?: string
  ): Promise<DeploymentResponse> {
    const payload = targetDeploymentId ? { target_deployment_id: targetDeploymentId } : {};
    const response = await api.post(`/api/orchestration/deploy/${projectId}/rollback`, payload);
    return response.data;
  }

  /**
   * Get deployment logs
   */
  async getDeploymentLogs(
    projectId: string,
    deploymentId: string,
    stepName?: string
  ): Promise<{
    logs: string[];
    total_lines: number;
    last_updated: string;
  }> {
    const url = stepName
      ? `/api/orchestration/deploy/${projectId}/logs/${deploymentId}/${stepName}`
      : `/api/orchestration/deploy/${projectId}/logs/${deploymentId}`;
    
    const response = await api.get(url);
    return response.data;
  }

  /**
   * Get available deployment strategies for a project
   */
  async getDeploymentStrategies(projectId: string): Promise<{
    strategies: Array<{
      name: string;
      description: string;
      supported: boolean;
      requirements?: string[];
    }>;
    recommended: string;
  }> {
    const response = await api.get(`/api/orchestration/deploy/${projectId}/strategies`);
    return response.data;
  }

  /**
   * Validate deployment configuration
   */
  async validateDeployment(
    projectId: string,
    deployment: DeploymentRequest
  ): Promise<{
    valid: boolean;
    issues: Array<{
      level: 'error' | 'warning' | 'info';
      message: string;
      field?: string;
    }>;
    estimated_duration?: number;
  }> {
    const response = await api.post(
      `/api/orchestration/deploy/${projectId}/validate`,
      deployment
    );
    return response.data;
  }

  /**
   * Get deployment environments and their current status
   */
  async getDeploymentEnvironments(projectId: string): Promise<Array<{
    name: string;
    status: 'active' | 'inactive' | 'deploying' | 'error';
    version?: string;
    last_deployed?: string;
    health_check_url?: string;
    is_production: boolean;
  }>> {
    const response = await api.get(`/api/orchestration/deploy/${projectId}/environments`);
    return response.data;
  }

  /**
   * Compare two deployments
   */
  async compareDeployments(
    projectId: string,
    deployment1Id: string,
    deployment2Id: string
  ): Promise<{
    differences: Array<{
      category: string;
      field: string;
      old_value: any;
      new_value: any;
      impact: 'low' | 'medium' | 'high';
    }>;
    summary: {
      total_changes: number;
      breaking_changes: number;
      risk_level: 'low' | 'medium' | 'high';
    };
  }> {
    const response = await api.get(
      `/api/orchestration/deploy/${projectId}/compare/${deployment1Id}/${deployment2Id}`
    );
    return response.data;
  }

  /**
   * Get deployment metrics and analytics
   */
  async getDeploymentMetrics(
    projectId: string,
    period = '30d'
  ): Promise<{
    total_deployments: number;
    success_rate: number;
    average_duration: number;
    failure_reasons: Array<{
      reason: string;
      count: number;
      percentage: number;
    }>;
    deployment_frequency: Array<{
      date: string;
      count: number;
    }>;
    performance_trends: Array<{
      metric: string;
      trend: 'improving' | 'declining' | 'stable';
      current_value: number;
      change_percent: number;
    }>;
  }> {
    const response = await api.get(
      `/api/orchestration/deploy/${projectId}/metrics?period=${period}`
    );
    return response.data;
  }

  /**
   * Schedule a deployment
   */
  async scheduleDeployment(
    projectId: string,
    deployment: DeploymentRequest,
    scheduledTime: string
  ): Promise<{
    schedule_id: string;
    scheduled_time: string;
    deployment_config: DeploymentRequest;
  }> {
    const response = await api.post(`/api/orchestration/deploy/${projectId}/schedule`, {
      ...deployment,
      scheduled_time: scheduledTime,
    });
    return response.data;
  }

  /**
   * Get scheduled deployments
   */
  async getScheduledDeployments(projectId: string): Promise<Array<{
    schedule_id: string;
    scheduled_time: string;
    deployment_config: DeploymentRequest;
    status: 'pending' | 'completed' | 'cancelled' | 'failed';
    created_at: string;
  }>> {
    const response = await api.get(`/api/orchestration/deploy/${projectId}/scheduled`);
    return response.data;
  }

  /**
   * Cancel a scheduled deployment
   */
  async cancelScheduledDeployment(
    projectId: string,
    scheduleId: string
  ): Promise<{ success: boolean; message: string }> {
    const response = await api.delete(
      `/api/orchestration/deploy/${projectId}/schedule/${scheduleId}`
    );
    return response.data;
  }
}

// Export singleton instance
export const deploymentService = new DeploymentService();
export default deploymentService;