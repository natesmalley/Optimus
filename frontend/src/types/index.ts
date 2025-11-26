export * from './api';

// UI component types
export interface SelectOption {
  value: string;
  label: string;
  icon?: React.ComponentType<{ className?: string }>;
}

export interface CardData {
  title: string;
  value: string | number;
  change?: number;
  changeType?: 'increase' | 'decrease' | 'neutral';
  icon?: React.ComponentType<{ className?: string }>;
  description?: string;
}

export interface ChartData {
  name: string;
  value: number;
  color?: string;
  [key: string]: any;
}

export interface TableColumn<T> {
  key: keyof T;
  label: string;
  sortable?: boolean;
  render?: (value: any, row: T) => React.ReactNode;
  width?: string;
}

export interface Toast {
  id: string;
  title: string;
  description?: string;
  type: 'success' | 'error' | 'warning' | 'info';
  duration?: number;
}

// Theme types
export type ThemeMode = 'light' | 'dark' | 'system';

// View types
export type ViewMode = 'grid' | 'list';
export type SortDirection = 'asc' | 'desc';

export interface SortConfig {
  key: string;
  direction: SortDirection;
}

// Navigation types
export interface NavigationItem {
  id: string;
  label: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string | number;
}

// Filter types
export interface FilterState {
  search: string;
  status: string[];
  techStack: string[];
  dateRange?: {
    from: Date;
    to: Date;
  };
}

// Pagination types
export interface PaginationState {
  page: number;
  size: number;
  total: number;
}

export interface PaginationInfo extends PaginationState {
  hasNext: boolean;
  hasPrev: boolean;
  totalPages: number;
}

// Loading states
export type LoadingState = 'idle' | 'loading' | 'success' | 'error';

// WebSocket types
export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
}

// Real-time update types
export interface RealTimeUpdate {
  type: 'project_update' | 'process_update' | 'metric_update';
  project_id?: string;
  data: any;
}