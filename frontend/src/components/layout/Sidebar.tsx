import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Monitor, 
  BarChart3, 
  Settings,
  ChevronLeft,
  Zap,
  Activity,
  Database,
  Code,
  Users
} from 'lucide-react';
import { useDashboardStore, useRuntimeStore } from '@/store';
import { cn } from '@/lib/utils';

const navigationItems = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    id: 'deliberation',
    label: 'Council of Minds',
    href: '/deliberation',
    icon: Users,
  },
  {
    id: 'monitor',
    label: 'System Monitor',
    href: '/monitor',
    icon: Monitor,
  },
  {
    id: 'analytics',
    label: 'Analytics',
    href: '/analytics',
    icon: BarChart3,
  },
];

const quickStats = [
  { icon: Code, label: 'Projects', key: 'total_projects' },
  { icon: Activity, label: 'Running', key: 'running_projects' },
  { icon: Database, label: 'Processes', key: 'total_processes' },
];

export default function Sidebar() {
  const location = useLocation();
  const { sidebarCollapsed, toggleSidebar } = useDashboardStore();
  const { systemRuntime } = useRuntimeStore();

  return (
    <div
      className={cn(
        "fixed left-0 top-0 z-40 h-screen bg-card border-r border-border transition-all duration-300",
        sidebarCollapsed ? "w-16" : "w-64"
      )}
    >
      {/* Logo/Header */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-border">
        {!sidebarCollapsed && (
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-gradient-primary rounded-lg flex items-center justify-center">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg font-semibold">Optimus</span>
          </div>
        )}
        
        <button
          onClick={toggleSidebar}
          className={cn(
            "btn btn-ghost btn-sm p-2 hover:bg-accent",
            sidebarCollapsed && "mx-auto"
          )}
        >
          <ChevronLeft
            className={cn(
              "w-4 h-4 transition-transform",
              sidebarCollapsed && "rotate-180"
            )}
          />
        </button>
      </div>

      {/* Navigation */}
      <div className="px-3 py-4">
        <nav className="space-y-2">
          {navigationItems.map((item) => {
            const isActive = location.pathname === item.href;
            const Icon = item.icon;

            return (
              <Link
                key={item.id}
                to={item.href}
                className={cn(
                  "flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors group relative",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-foreground"
                )}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                
                {!sidebarCollapsed ? (
                  <span className="text-sm font-medium">{item.label}</span>
                ) : (
                  <div className="absolute left-full ml-2 px-2 py-1 bg-popover text-popover-foreground text-sm rounded-md shadow-md opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
                    {item.label}
                  </div>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Quick Stats */}
      {!sidebarCollapsed && systemRuntime && (
        <div className="px-3 py-4 border-t border-border">
          <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
            System Status
          </h3>
          <div className="space-y-3">
            {quickStats.map((stat) => {
              const Icon = stat.icon;
              const value = systemRuntime[stat.key as keyof typeof systemRuntime];
              
              return (
                <div key={stat.key} className="flex items-center space-x-3">
                  <div className="w-8 h-8 rounded-md bg-muted flex items-center justify-center">
                    <Icon className="w-4 h-4 text-muted-foreground" />
                  </div>
                  <div className="flex-1">
                    <div className="text-sm font-medium">{value}</div>
                    <div className="text-xs text-muted-foreground">{stat.label}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Settings */}
      <div className="absolute bottom-0 left-0 right-0 p-3 border-t border-border">
        <button
          className={cn(
            "flex items-center space-x-3 w-full px-3 py-2 rounded-lg transition-colors text-muted-foreground hover:bg-accent hover:text-foreground group relative"
          )}
        >
          <Settings className="w-5 h-5 flex-shrink-0" />
          
          {!sidebarCollapsed ? (
            <span className="text-sm font-medium">Settings</span>
          ) : (
            <div className="absolute left-full ml-2 px-2 py-1 bg-popover text-popover-foreground text-sm rounded-md shadow-md opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
              Settings
            </div>
          )}
        </button>
      </div>
    </div>
  );
}