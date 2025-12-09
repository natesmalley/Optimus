/**
 * BackupHistory - Component for viewing and managing backup history
 * Shows detailed backup history with filtering and management options
 */

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Archive,
  Download,
  Trash2,
  RotateCcw,
  Eye,
  Calendar,
  Filter,
  Search,
  CheckCircle,
  AlertTriangle,
  Clock,
  Loader2,
  HardDrive,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { backupService } from '../../services/backupService';
import { formatDistanceToNow, format } from 'date-fns';
import type { BackupInfo } from '../../types/api';

interface BackupHistoryProps {
  projectId: string;
  backups: BackupInfo[];
  isLoading?: boolean;
}

export function BackupHistory({ projectId, backups, isLoading = false }: BackupHistoryProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [sortField, setSortField] = useState<'created_at' | 'size_mb' | 'name'>('created_at');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [expandedBackups, setExpandedBackups] = useState<Set<string>>(new Set());

  const queryClient = useQueryClient();

  // Delete backup mutation
  const deleteMutation = useMutation({
    mutationFn: (backupId: string) => backupService.deleteBackup(projectId, backupId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backup', projectId] });
    },
  });

  // Restore backup mutation
  const restoreMutation = useMutation({
    mutationFn: ({ backupId, options }: { backupId: string; options: any }) => 
      backupService.restoreBackup(projectId, backupId, options),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backup', projectId] });
    },
  });

  // Validate backup mutation
  const validateMutation = useMutation({
    mutationFn: (backupId: string) => backupService.validateBackup(projectId, backupId),
  });

  const getBackupStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'creating': return <Loader2 className="h-4 w-4 text-blue-600 animate-spin" />;
      case 'failed': return <AlertTriangle className="h-4 w-4 text-red-600" />;
      case 'expired': return <Clock className="h-4 w-4 text-gray-400" />;
      default: return <Archive className="h-4 w-4 text-gray-600" />;
    }
  };

  const getBackupStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600 bg-green-50 border-green-200';
      case 'creating': return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'failed': return 'text-red-600 bg-red-50 border-red-200';
      case 'expired': return 'text-gray-600 bg-gray-50 border-gray-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const filteredAndSortedBackups = React.useMemo(() => {
    let filtered = backups.filter(backup => {
      const matchesSearch = backup.name.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesStatus = statusFilter === 'all' || backup.status === statusFilter;
      const matchesType = typeFilter === 'all' || backup.type === typeFilter;
      
      return matchesSearch && matchesStatus && matchesType;
    });

    return [...filtered].sort((a, b) => {
      let aValue: any, bValue: any;

      switch (sortField) {
        case 'created_at':
          aValue = new Date(a.created_at);
          bValue = new Date(b.created_at);
          break;
        case 'size_mb':
          aValue = a.size_mb;
          bValue = b.size_mb;
          break;
        case 'name':
          aValue = a.name.toLowerCase();
          bValue = b.name.toLowerCase();
          break;
        default:
          return 0;
      }

      if (aValue < bValue) return sortDirection === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }, [backups, searchTerm, statusFilter, typeFilter, sortField, sortDirection]);

  const toggleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const toggleExpanded = (backupId: string) => {
    const newExpanded = new Set(expandedBackups);
    if (newExpanded.has(backupId)) {
      newExpanded.delete(backupId);
    } else {
      newExpanded.add(backupId);
    }
    setExpandedBackups(newExpanded);
  };

  const handleRestore = (backup: BackupInfo) => {
    const confirmMessage = `Are you sure you want to restore from backup "${backup.name}"?\n\nThis will:\n- Replace current project files\n- Create a backup of current state first\n- Cannot be undone after confirmation`;
    
    if (window.confirm(confirmMessage)) {
      restoreMutation.mutate({
        backupId: backup.id,
        options: {
          create_backup_before_restore: true,
          overwrite: true,
        },
      });
    }
  };

  const handleDelete = (backup: BackupInfo) => {
    const confirmMessage = `Are you sure you want to delete backup "${backup.name}"?\n\nThis will:\n- Permanently delete the backup\n- Free ${(backup.size_mb / 1024).toFixed(1)} GB of storage\n- Cannot be undone`;
    
    if (window.confirm(confirmMessage)) {
      deleteMutation.mutate(backup.id);
    }
  };

  const handleValidate = (backup: BackupInfo) => {
    validateMutation.mutate(backup.id);
  };

  const uniqueStatuses = Array.from(new Set(backups.map(b => b.status)));
  const uniqueTypes = Array.from(new Set(backups.map(b => b.type)));

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
        <span className="ml-2 text-gray-600">Loading backup history...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Filters and search */}
      <div className="bg-white rounded-lg border p-4">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Search
            </label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search backups..."
                className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md focus:border-blue-500 focus:ring-blue-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Status
            </label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:border-blue-500 focus:ring-blue-500"
            >
              <option value="all">All Statuses</option>
              {uniqueStatuses.map(status => (
                <option key={status} value={status}>
                  {status.charAt(0).toUpperCase() + status.slice(1)}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Type
            </label>
            <select
              value={typeFilter}
              onChange={(e) => setTypeFilter(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:border-blue-500 focus:ring-blue-500"
            >
              <option value="all">All Types</option>
              {uniqueTypes.map(type => (
                <option key={type} value={type}>
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-end">
            <span className="text-sm text-gray-600">
              {filteredAndSortedBackups.length} of {backups.length} backups
            </span>
          </div>
        </div>
      </div>

      {/* Backup table */}
      {filteredAndSortedBackups.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border">
          <Archive className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            {backups.length === 0 ? 'No backups found' : 'No matching backups'}
          </h3>
          <p className="text-gray-600">
            {backups.length === 0 
              ? 'Create your first backup to see it here'
              : 'Try adjusting your filters or search term'
            }
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th 
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => toggleSort('name')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>Name</span>
                      {sortField === 'name' && (
                        sortDirection === 'asc' ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />
                      )}
                    </div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th 
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => toggleSort('size_mb')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>Size</span>
                      {sortField === 'size_mb' && (
                        sortDirection === 'asc' ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />
                      )}
                    </div>
                  </th>
                  <th 
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                    onClick={() => toggleSort('created_at')}
                  >
                    <div className="flex items-center space-x-1">
                      <span>Created</span>
                      {sortField === 'created_at' && (
                        sortDirection === 'asc' ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />
                      )}
                    </div>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Retention
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Details
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredAndSortedBackups.map((backup, index) => (
                  <React.Fragment key={backup.id}>
                    <motion.tr
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="hover:bg-gray-50"
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className={`inline-flex items-center space-x-2 rounded-full border px-2.5 py-1 text-xs font-medium ${getBackupStatusColor(backup.status)}`}>
                          {getBackupStatusIcon(backup.status)}
                          <span>{backup.status.toUpperCase()}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="font-medium text-gray-900">{backup.name}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="capitalize text-gray-600">{backup.type}</span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                        <div className="flex items-center space-x-1">
                          <HardDrive className="h-4 w-4" />
                          <span>{(backup.size_mb / 1024).toFixed(1)} GB</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                        <div className="flex items-center space-x-1">
                          <Calendar className="h-4 w-4" />
                          <span>{format(new Date(backup.created_at), 'MMM dd, yyyy')}</span>
                        </div>
                        <div className="text-xs text-gray-500">
                          {formatDistanceToNow(new Date(backup.created_at))} ago
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                        {backup.retention_days} days
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                        <div className="flex items-center space-x-2">
                          {backup.can_restore && backup.status === 'completed' && (
                            <button
                              onClick={() => handleRestore(backup)}
                              disabled={restoreMutation.isPending}
                              className="text-blue-600 hover:text-blue-800 p-1"
                              title="Restore backup"
                            >
                              <RotateCcw className="h-4 w-4" />
                            </button>
                          )}

                          {backup.status === 'completed' && (
                            <button
                              onClick={() => handleValidate(backup)}
                              disabled={validateMutation.isPending}
                              className="text-green-600 hover:text-green-800 p-1"
                              title="Validate backup"
                            >
                              <CheckCircle className="h-4 w-4" />
                            </button>
                          )}

                          <button
                            onClick={() => handleDelete(backup)}
                            disabled={deleteMutation.isPending}
                            className="text-red-600 hover:text-red-800 p-1"
                            title="Delete backup"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                        <button
                          onClick={() => toggleExpanded(backup.id)}
                          className="text-gray-400 hover:text-gray-600"
                        >
                          {expandedBackups.has(backup.id) ? (
                            <ChevronUp className="h-4 w-4" />
                          ) : (
                            <ChevronDown className="h-4 w-4" />
                          )}
                        </button>
                      </td>
                    </motion.tr>

                    {/* Expanded row details */}
                    {expandedBackups.has(backup.id) && (
                      <tr>
                        <td colSpan={8} className="px-6 py-4 bg-gray-50">
                          <div className="space-y-3">
                            <div className="grid grid-cols-2 gap-4 text-sm">
                              <div>
                                <strong>Compression:</strong> {backup.compression}
                              </div>
                              <div>
                                <strong>Includes:</strong> {backup.includes.length} patterns
                              </div>
                              <div>
                                <strong>Excludes:</strong> {backup.excludes.length} patterns
                              </div>
                              {backup.retention_days && (
                                <div>
                                  <strong>Expires:</strong>{' '}
                                  {format(
                                    new Date(new Date(backup.created_at).getTime() + backup.retention_days * 24 * 60 * 60 * 1000),
                                    'MMM dd, yyyy'
                                  )}
                                </div>
                              )}
                            </div>

                            {backup.includes.length > 0 && (
                              <div>
                                <strong className="text-sm">Included:</strong>
                                <div className="mt-1 text-sm text-gray-600">
                                  {backup.includes.join(', ')}
                                </div>
                              </div>
                            )}

                            {backup.excludes.length > 0 && (
                              <div>
                                <strong className="text-sm">Excluded:</strong>
                                <div className="mt-1 text-sm text-gray-600">
                                  {backup.excludes.slice(0, 10).join(', ')}
                                  {backup.excludes.length > 10 && ` and ${backup.excludes.length - 10} more`}
                                </div>
                              </div>
                            )}

                            {/* Validation results */}
                            {validateMutation.data && validateMutation.variables === backup.id && (
                              <div className="rounded-md border p-3">
                                <strong className="text-sm">Validation Results:</strong>
                                <div className="mt-2 space-y-1">
                                  <div className={`text-sm ${
                                    validateMutation.data.valid ? 'text-green-600' : 'text-red-600'
                                  }`}>
                                    Status: {validateMutation.data.valid ? 'Valid' : 'Invalid'}
                                  </div>
                                  {validateMutation.data.issues.length > 0 && (
                                    <div className="text-sm text-red-600">
                                      Issues: {validateMutation.data.issues.map(i => i.message).join(', ')}
                                    </div>
                                  )}
                                  <div className="text-xs text-gray-500">
                                    Validated: {validateMutation.data.validation_time}
                                  </div>
                                </div>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}