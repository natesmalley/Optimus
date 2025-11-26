/**
 * Global state management using Zustand
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { 
  ThemeMode, 
  ViewMode, 
  FilterState, 
  PaginationState,
  Project,
  SystemRuntimeResponse,
  Toast 
} from '@/types';

// Theme store
interface ThemeStore {
  mode: ThemeMode;
  setMode: (mode: ThemeMode) => void;
  toggleMode: () => void;
}

export const useThemeStore = create<ThemeStore>()(
  persist(
    (set, get) => ({
      mode: 'system',
      setMode: (mode) => set({ mode }),
      toggleMode: () => {
        const current = get().mode;
        set({ mode: current === 'light' ? 'dark' : 'light' });
      },
    }),
    {
      name: 'optimus-theme',
      storage: createJSONStorage(() => localStorage),
    }
  )
);

// Dashboard preferences store
interface DashboardStore {
  viewMode: ViewMode;
  autoRefresh: boolean;
  refreshInterval: number;
  sidebarCollapsed: boolean;
  setViewMode: (mode: ViewMode) => void;
  setAutoRefresh: (enabled: boolean) => void;
  setRefreshInterval: (interval: number) => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleSidebar: () => void;
}

export const useDashboardStore = create<DashboardStore>()(
  persist(
    (set, get) => ({
      viewMode: 'grid',
      autoRefresh: true,
      refreshInterval: 30000, // 30 seconds
      sidebarCollapsed: false,
      setViewMode: (mode) => set({ viewMode: mode }),
      setAutoRefresh: (enabled) => set({ autoRefresh: enabled }),
      setRefreshInterval: (interval) => set({ refreshInterval: interval }),
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
    }),
    {
      name: 'optimus-dashboard',
      storage: createJSONStorage(() => localStorage),
    }
  )
);

// Projects store
interface ProjectsStore {
  projects: Project[];
  selectedProject: Project | null;
  filters: FilterState;
  pagination: PaginationState;
  loading: boolean;
  error: string | null;
  setProjects: (projects: Project[]) => void;
  setSelectedProject: (project: Project | null) => void;
  setFilters: (filters: Partial<FilterState>) => void;
  setPagination: (pagination: Partial<PaginationState>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  updateProject: (projectId: string, updates: Partial<Project>) => void;
  removeProject: (projectId: string) => void;
  clearFilters: () => void;
}

export const useProjectsStore = create<ProjectsStore>((set, get) => ({
  projects: [],
  selectedProject: null,
  filters: {
    search: '',
    status: [],
    techStack: [],
  },
  pagination: {
    page: 1,
    size: 20,
    total: 0,
  },
  loading: false,
  error: null,
  
  setProjects: (projects) => set({ projects }),
  setSelectedProject: (project) => set({ selectedProject: project }),
  
  setFilters: (filters) => 
    set((state) => ({ 
      filters: { ...state.filters, ...filters },
      pagination: { ...state.pagination, page: 1 } // Reset to first page
    })),
    
  setPagination: (pagination) =>
    set((state) => ({ pagination: { ...state.pagination, ...pagination } })),
    
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  
  updateProject: (projectId, updates) =>
    set((state) => ({
      projects: state.projects.map((p) =>
        p.id === projectId ? { ...p, ...updates } : p
      ),
      selectedProject: state.selectedProject?.id === projectId
        ? { ...state.selectedProject, ...updates }
        : state.selectedProject,
    })),
    
  removeProject: (projectId) =>
    set((state) => ({
      projects: state.projects.filter((p) => p.id !== projectId),
      selectedProject: state.selectedProject?.id === projectId 
        ? null 
        : state.selectedProject,
    })),
    
  clearFilters: () =>
    set((state) => ({
      filters: {
        search: '',
        status: [],
        techStack: [],
      },
      pagination: { ...state.pagination, page: 1 },
    })),
}));

// Runtime store
interface RuntimeStore {
  systemRuntime: SystemRuntimeResponse | null;
  lastUpdated: Date | null;
  loading: boolean;
  error: string | null;
  setSystemRuntime: (runtime: SystemRuntimeResponse) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  updateProjectRuntime: (projectId: string, runtime: any) => void;
}

export const useRuntimeStore = create<RuntimeStore>((set, get) => ({
  systemRuntime: null,
  lastUpdated: null,
  loading: false,
  error: null,
  
  setSystemRuntime: (runtime) => 
    set({ systemRuntime: runtime, lastUpdated: new Date() }),
    
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  
  updateProjectRuntime: (projectId, runtime) =>
    set((state) => {
      if (!state.systemRuntime) return state;
      
      return {
        systemRuntime: {
          ...state.systemRuntime,
          projects: state.systemRuntime.projects.map((p) =>
            p.project_id === projectId ? { ...p, ...runtime } : p
          ),
        },
        lastUpdated: new Date(),
      };
    }),
}));

// Toast notification store
interface ToastStore {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
  clearToasts: () => void;
}

export const useToastStore = create<ToastStore>((set, get) => ({
  toasts: [],
  
  addToast: (toast) => {
    const id = Math.random().toString(36).substring(2);
    const newToast = { ...toast, id };
    
    set((state) => ({ toasts: [...state.toasts, newToast] }));
    
    // Auto-remove after duration
    const duration = toast.duration || 5000;
    setTimeout(() => {
      set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
    }, duration);
  },
  
  removeToast: (id) =>
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
    
  clearToasts: () => set({ toasts: [] }),
}));

// Search store for global search functionality
interface SearchStore {
  query: string;
  results: any[];
  loading: boolean;
  recentSearches: string[];
  setQuery: (query: string) => void;
  setResults: (results: any[]) => void;
  setLoading: (loading: boolean) => void;
  addRecentSearch: (query: string) => void;
  clearRecentSearches: () => void;
}

export const useSearchStore = create<SearchStore>()(
  persist(
    (set, get) => ({
      query: '',
      results: [],
      loading: false,
      recentSearches: [],
      
      setQuery: (query) => set({ query }),
      setResults: (results) => set({ results }),
      setLoading: (loading) => set({ loading }),
      
      addRecentSearch: (query) => {
        if (!query.trim()) return;
        
        set((state) => {
          const filtered = state.recentSearches.filter((s) => s !== query);
          return {
            recentSearches: [query, ...filtered].slice(0, 10), // Keep only 10 recent searches
          };
        });
      },
      
      clearRecentSearches: () => set({ recentSearches: [] }),
    }),
    {
      name: 'optimus-search',
      storage: createJSONStorage(() => localStorage),
    }
  )
);

// Realtime updates store
interface RealtimeStore {
  connected: boolean;
  lastHeartbeat: Date | null;
  updates: any[];
  setConnected: (connected: boolean) => void;
  setHeartbeat: () => void;
  addUpdate: (update: any) => void;
  clearUpdates: () => void;
}

export const useRealtimeStore = create<RealtimeStore>((set) => ({
  connected: false,
  lastHeartbeat: null,
  updates: [],
  
  setConnected: (connected) => set({ connected }),
  setHeartbeat: () => set({ lastHeartbeat: new Date() }),
  
  addUpdate: (update) =>
    set((state) => ({
      updates: [update, ...state.updates].slice(0, 100), // Keep only 100 recent updates
    })),
    
  clearUpdates: () => set({ updates: [] }),
}));