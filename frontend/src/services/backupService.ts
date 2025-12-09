/**
 * Backup service for managing project backups and schedules
 * Handles backup creation, scheduling, restoration, and management
 */

import { api } from '../lib/api';
import type {
  BackupInfo,
  BackupRequest,
  BackupResponse,
  BackupSchedule,
} from '../types/api';

class BackupService {
  /**
   * Create a manual backup
   */
  async createBackup(
    projectId: string,
    backup: BackupRequest = {}
  ): Promise<BackupResponse> {
    const response = await api.post(`/api/orchestration/backups/${projectId}`, backup);
    return response.data;
  }

  /**
   * Get backup list for a project
   */
  async getBackups(
    projectId: string,
    limit = 50,
    offset = 0
  ): Promise<{
    backups: BackupInfo[];
    total: number;
    total_size_mb: number;
  }> {
    const response = await api.get(
      `/api/orchestration/backups/${projectId}?limit=${limit}&offset=${offset}`
    );
    return response.data;
  }

  /**
   * Get backup details by ID
   */
  async getBackupDetails(
    projectId: string,
    backupId: string
  ): Promise<BackupInfo & {
    file_list: Array<{
      path: string;
      size_mb: number;
      modified: string;
    }>;
    metadata: Record<string, any>;
  }> {
    const response = await api.get(`/api/orchestration/backups/${projectId}/${backupId}`);
    return response.data;
  }

  /**
   * Delete a backup
   */
  async deleteBackup(
    projectId: string,
    backupId: string
  ): Promise<{ success: boolean; message: string; freed_space_mb: number }> {
    const response = await api.delete(`/api/orchestration/backups/${projectId}/${backupId}`);
    return response.data;
  }

  /**
   * Restore from backup
   */
  async restoreBackup(
    projectId: string,
    backupId: string,
    options: {
      target_path?: string;
      overwrite?: boolean;
      selective_restore?: string[];
      create_backup_before_restore?: boolean;
    } = {}
  ): Promise<{
    restore_id: string;
    status: string;
    message: string;
    estimated_duration?: number;
  }> {
    const response = await api.post(
      `/api/orchestration/backups/${projectId}/${backupId}/restore`,
      options
    );
    return response.data;
  }

  /**
   * Get restore status
   */
  async getRestoreStatus(
    projectId: string,
    restoreId: string
  ): Promise<{
    restore_id: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    progress: number;
    current_file?: string;
    files_restored: number;
    total_files: number;
    start_time: string;
    end_time?: string;
    error_message?: string;
  }> {
    const response = await api.get(
      `/api/orchestration/backups/${projectId}/restore/${restoreId}/status`
    );
    return response.data;
  }

  /**
   * Create backup schedule
   */
  async createSchedule(
    projectId: string,
    schedule: {
      name: string;
      cron_expression: string;
      backup_type: string;
      retention_days: number;
      includes?: string[];
      excludes?: string[];
      enabled?: boolean;
    }
  ): Promise<{
    schedule_id: string;
    message: string;
    next_run: string;
  }> {
    const response = await api.post(
      `/api/orchestration/backups/${projectId}/schedules`,
      schedule
    );
    return response.data;
  }

  /**
   * Get backup schedules for a project
   */
  async getSchedules(projectId: string): Promise<BackupSchedule[]> {
    const response = await api.get(`/api/orchestration/backups/${projectId}/schedules`);
    return response.data;
  }

  /**
   * Update backup schedule
   */
  async updateSchedule(
    projectId: string,
    scheduleId: string,
    updates: Partial<BackupSchedule>
  ): Promise<{ success: boolean; message: string; next_run?: string }> {
    const response = await api.patch(
      `/api/orchestration/backups/${projectId}/schedules/${scheduleId}`,
      updates
    );
    return response.data;
  }

  /**
   * Delete backup schedule
   */
  async deleteSchedule(
    projectId: string,
    scheduleId: string
  ): Promise<{ success: boolean; message: string }> {
    const response = await api.delete(
      `/api/orchestration/backups/${projectId}/schedules/${scheduleId}`
    );
    return response.data;
  }

  /**
   * Enable/disable backup schedule
   */
  async toggleSchedule(
    projectId: string,
    scheduleId: string,
    enabled: boolean
  ): Promise<{ success: boolean; message: string; next_run?: string }> {
    const response = await api.post(
      `/api/orchestration/backups/${projectId}/schedules/${scheduleId}/toggle`,
      { enabled }
    );
    return response.data;
  }

  /**
   * Run scheduled backup immediately
   */
  async runScheduleNow(
    projectId: string,
    scheduleId: string
  ): Promise<BackupResponse> {
    const response = await api.post(
      `/api/orchestration/backups/${projectId}/schedules/${scheduleId}/run`
    );
    return response.data;
  }

  /**
   * Get backup statistics
   */
  async getBackupStats(projectId: string): Promise<{
    total_backups: number;
    total_size_mb: number;
    oldest_backup: string;
    newest_backup: string;
    success_rate: number;
    average_size_mb: number;
    retention_compliance: {
      total_scheduled: number;
      expired_not_deleted: number;
      storage_saved_mb: number;
    };
    schedule_summary: {
      total_schedules: number;
      enabled_schedules: number;
      next_run: string;
    };
  }> {
    const response = await api.get(`/api/orchestration/backups/${projectId}/stats`);
    return response.data;
  }

  /**
   * Validate backup integrity
   */
  async validateBackup(
    projectId: string,
    backupId: string
  ): Promise<{
    valid: boolean;
    checks_performed: string[];
    issues: Array<{
      severity: 'error' | 'warning';
      message: string;
      file?: string;
    }>;
    validation_time: string;
  }> {
    const response = await api.post(
      `/api/orchestration/backups/${projectId}/${backupId}/validate`
    );
    return response.data;
  }

  /**
   * Get system-wide backup summary
   */
  async getSystemBackupSummary(): Promise<{
    total_projects_with_backups: number;
    total_backups: number;
    total_size_gb: number;
    total_schedules: number;
    active_schedules: number;
    recent_failures: number;
    storage_usage: Array<{
      project_id: string;
      project_name: string;
      backup_count: number;
      size_gb: number;
      last_backup: string;
    }>;
  }> {
    const response = await api.get('/api/orchestration/backups/summary');
    return response.data;
  }

  /**
   * Clean up expired backups
   */
  async cleanupExpiredBackups(
    projectId: string,
    dryRun = true
  ): Promise<{
    would_delete: number;
    would_free_mb: number;
    deleted?: number;
    freed_mb?: number;
    backups_to_delete: Array<{
      id: string;
      name: string;
      created_at: string;
      size_mb: number;
    }>;
  }> {
    const response = await api.post(
      `/api/orchestration/backups/${projectId}/cleanup`,
      { dry_run: dryRun }
    );
    return response.data;
  }
}

// Export singleton instance
export const backupService = new BackupService();
export default backupService;