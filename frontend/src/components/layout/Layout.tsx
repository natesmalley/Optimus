import { Outlet } from 'react-router-dom';
import { useDashboardStore } from '@/store';
import { cn } from '@/lib/utils';
import Sidebar from './Sidebar';
import Header from './Header';

export default function Layout() {
  const { sidebarCollapsed } = useDashboardStore();

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <Sidebar />
      
      {/* Main content area */}
      <div 
        className={cn(
          "flex-1 flex flex-col overflow-hidden transition-all duration-300",
          sidebarCollapsed ? "ml-16" : "ml-64"
        )}
      >
        {/* Header */}
        <Header />
        
        {/* Page content */}
        <main className="flex-1 overflow-auto">
          <div className="container mx-auto px-6 py-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}