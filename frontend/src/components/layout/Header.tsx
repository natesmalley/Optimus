import { useState } from 'react';
import { 
  Search, 
  Bell, 
  Sun, 
  Moon, 
  Monitor,
  RefreshCw,
  Settings,
  User,
  Wifi,
  WifiOff
} from 'lucide-react';
import { useThemeStore, useDashboardStore, useRealtimeStore } from '@/store';
import { cn, formatRelativeTime } from '@/lib/utils';

export default function Header() {
  const [searchOpen, setSearchOpen] = useState(false);
  const { mode, setMode } = useThemeStore();
  const { autoRefresh, refreshInterval, setAutoRefresh } = useDashboardStore();
  const { connected, lastHeartbeat } = useRealtimeStore();

  const getThemeIcon = () => {
    switch (mode) {
      case 'light':
        return Sun;
      case 'dark':
        return Moon;
      default:
        return Monitor;
    }
  };

  const cycleTheme = () => {
    const themes: Array<typeof mode> = ['light', 'dark', 'system'];
    const currentIndex = themes.indexOf(mode);
    const nextIndex = (currentIndex + 1) % themes.length;
    setMode(themes[nextIndex]);
  };

  const ThemeIcon = getThemeIcon();

  return (
    <header className="h-16 bg-card border-b border-border px-6 flex items-center justify-between">
      {/* Left side - Search */}
      <div className="flex items-center space-x-4 flex-1">
        <div className="relative max-w-md w-full">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search projects, processes, or metrics..."
            className="input pl-10 w-full"
            onFocus={() => setSearchOpen(true)}
            onBlur={() => setTimeout(() => setSearchOpen(false), 200)}
          />
          
          {searchOpen && (
            <div className="absolute top-full mt-1 w-full bg-popover border border-border rounded-md shadow-lg z-50 animate-in">
              <div className="p-3">
                <div className="text-sm text-muted-foreground mb-2">Recent searches</div>
                <div className="space-y-1">
                  <div className="text-sm hover:bg-accent rounded px-2 py-1 cursor-pointer">
                    React projects
                  </div>
                  <div className="text-sm hover:bg-accent rounded px-2 py-1 cursor-pointer">
                    Running processes
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right side - Controls */}
      <div className="flex items-center space-x-2">
        {/* Connection Status */}
        <div 
          className={cn(
            "flex items-center space-x-2 px-2 py-1 rounded-md text-xs",
            connected 
              ? "text-green-600 bg-green-50 dark:bg-green-900/20" 
              : "text-red-600 bg-red-50 dark:bg-red-900/20"
          )}
          title={lastHeartbeat ? `Last update: ${formatRelativeTime(lastHeartbeat.toISOString())}` : 'Not connected'}
        >
          {connected ? (
            <Wifi className="w-3 h-3" />
          ) : (
            <WifiOff className="w-3 h-3" />
          )}
          <span>{connected ? 'Live' : 'Offline'}</span>
        </div>

        {/* Auto-refresh toggle */}
        <button
          onClick={() => setAutoRefresh(!autoRefresh)}
          className={cn(
            "btn btn-ghost btn-sm",
            autoRefresh && "text-green-600"
          )}
          title={autoRefresh ? `Auto-refresh every ${refreshInterval / 1000}s` : 'Auto-refresh disabled'}
        >
          <RefreshCw className={cn("w-4 h-4", autoRefresh && "animate-spin-slow")} />
        </button>

        {/* Theme toggle */}
        <button
          onClick={cycleTheme}
          className="btn btn-ghost btn-sm"
          title={`Current theme: ${mode}`}
        >
          <ThemeIcon className="w-4 h-4" />
        </button>

        {/* Notifications */}
        <button className="btn btn-ghost btn-sm relative">
          <Bell className="w-4 h-4" />
          <div className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full text-xs text-white flex items-center justify-center">
            3
          </div>
        </button>

        {/* Settings */}
        <button className="btn btn-ghost btn-sm">
          <Settings className="w-4 h-4" />
        </button>

        {/* User menu */}
        <div className="flex items-center space-x-2 pl-2 border-l border-border">
          <button className="btn btn-ghost btn-sm">
            <User className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
}