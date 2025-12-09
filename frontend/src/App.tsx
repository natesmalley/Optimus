import { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useThemeStore } from '@/store';
import Layout from '@/components/layout/Layout';
import Dashboard from '@/pages/Dashboard';
import ProjectDetail from '@/pages/ProjectDetail';
import SystemMonitor from '@/pages/SystemMonitor';
import Analytics from '@/pages/Analytics';
import { Deliberation } from '@/pages/Deliberation';
import Orchestration from '@/pages/Orchestration';
import Deployment from '@/pages/Deployment';
import Resources from '@/pages/Resources';
import Backup from '@/pages/Backup';
import ToastProvider from '@/components/ui/ToastProvider';

function App() {
  const { mode } = useThemeStore();

  // Apply theme to document
  useEffect(() => {
    const root = document.documentElement;
    
    // Remove existing theme classes
    root.classList.remove('light', 'dark');
    
    if (mode === 'system') {
      // Use system preference
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      root.classList.add(mediaQuery.matches ? 'dark' : 'light');
      
      // Listen for system theme changes
      const handleChange = (e: MediaQueryListEvent) => {
        root.classList.remove('light', 'dark');
        root.classList.add(e.matches ? 'dark' : 'light');
      };
      
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    } else {
      // Use explicit theme
      root.classList.add(mode);
    }
  }, [mode]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <ToastProvider />
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="projects/:id" element={<ProjectDetail />} />
          <Route path="monitor" element={<SystemMonitor />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="deliberation" element={<Deliberation />} />
          <Route path="orchestration" element={<Orchestration />} />
          <Route path="deployment" element={<Deployment />} />
          <Route path="resources" element={<Resources />} />
          <Route path="backup" element={<Backup />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </div>
  );
}

export default App;