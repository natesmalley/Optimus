# Optimus Orchestration Dashboard

A comprehensive React dashboard for the Optimus Orchestration Service, providing a powerful, intuitive interface for managing project lifecycle operations, deployments, resources, and backups.

## Features

### 🚀 Project Orchestration
- **Project Management Panel**: View all discovered projects with their current status
- **Launch/Stop Controls**: Start and stop projects with real-time feedback
- **Environment Switching**: Switch between dev, staging, and production environments
- **Resource Usage Monitoring**: Real-time CPU, memory, and storage monitoring
- **Health Checks**: Monitor project health and performance

### 🏗️ Deployment Pipeline
- **Pipeline Visualization**: Visual representation of deployment steps and progress
- **Multi-Environment Deployment**: Deploy to different environments with proper controls
- **Rollback Management**: Easy rollback to previous deployments
- **Deployment History**: Complete history with filtering and comparison
- **Real-time Progress**: Live updates during deployment operations

### 💻 Resource Management
- **Real-time Monitoring**: Live charts showing CPU, memory, storage, and network usage
- **Resource Allocation**: Set limits and priorities for projects
- **Performance Optimization**: AI-powered recommendations for resource optimization
- **System Overview**: Global resource usage across all projects
- **Alert Configuration**: Set up alerts for resource thresholds

### 💾 Backup & Recovery
- **Automated Scheduling**: Create and manage backup schedules with cron expressions
- **Manual Backups**: Create on-demand backups with custom settings
- **Backup History**: Complete backup history with validation and management
- **Restoration Tools**: Easy restoration from any backup point
- **Storage Management**: Monitor backup storage usage and cleanup

## Technology Stack

### Frontend Framework
- **React 18** with TypeScript for type safety
- **Vite** for fast development and optimized builds
- **React Router** for client-side routing
- **Framer Motion** for smooth animations and transitions

### State Management
- **Zustand** for global state management
- **React Query (TanStack Query)** for server state and caching
- **React Hook Form** with Zod validation for forms

### UI Components
- **Tailwind CSS** for consistent, responsive styling
- **Radix UI** primitives for accessible components
- **Lucide React** for consistent iconography
- **Recharts** for interactive data visualizations

### Real-time Communication
- **WebSocket** integration for live updates
- Custom hooks for orchestration, deployment, and backup updates
- Automatic reconnection and error handling

## Project Structure

```
frontend/src/
├── components/
│   ├── orchestration/
│   │   ├── OrchestrationPanel.tsx    # Main project management interface
│   │   ├── ProjectCard.tsx           # Individual project card component
│   │   └── EnvironmentSwitcher.tsx   # Environment switching modal
│   ├── deployment/
│   │   ├── DeploymentDashboard.tsx   # Main deployment interface
│   │   ├── DeploymentPipeline.tsx    # Pipeline visualization
│   │   └── DeploymentHistory.tsx     # Deployment history table
│   ├── resources/
│   │   ├── ResourceMonitor.tsx       # Resource monitoring dashboard
│   │   ├── ResourceChart.tsx         # Interactive charts
│   │   └── ResourceAllocator.tsx     # Resource allocation modal
│   └── backup/
│       ├── BackupManager.tsx         # Backup management interface
│       ├── BackupScheduler.tsx       # Schedule creation/management
│       └── BackupHistory.tsx         # Backup history and restoration
├── hooks/
│   ├── useOrchestration.ts          # Orchestration operations hooks
│   ├── useWebSocket.ts              # WebSocket communication hooks
│   └── useAutoRefresh.ts            # Auto-refresh utilities
├── services/
│   ├── orchestrationService.ts      # API client for orchestration
│   ├── deploymentService.ts         # API client for deployments
│   └── backupService.ts             # API client for backups
├── types/
│   └── api.ts                       # TypeScript type definitions
└── pages/
    ├── Orchestration.tsx            # Orchestration page
    ├── Deployment.tsx               # Deployment page
    ├── Resources.tsx                # Resources page
    └── Backup.tsx                   # Backup page
```

## API Integration

### Backend Endpoints
The dashboard integrates with these backend endpoints:

#### Orchestration
- `POST /api/orchestration/launch/{project_id}` - Launch project
- `POST /api/orchestration/stop/{project_id}` - Stop project
- `POST /api/orchestration/environments/{project_id}/switch` - Switch environment
- `GET /api/orchestration/resources/{project_id}` - Get resource usage

#### Deployment
- `POST /api/orchestration/deploy/{project_id}` - Start deployment
- `GET /api/orchestration/deploy/{project_id}/status` - Get deployment status
- `POST /api/orchestration/deploy/{project_id}/rollback` - Rollback deployment

#### Backup
- `POST /api/orchestration/backups/{project_id}` - Create backup
- `GET /api/orchestration/backups/{project_id}` - List backups
- `POST /api/orchestration/backups/{project_id}/{backup_id}/restore` - Restore backup

### Real-time Updates
WebSocket connections provide real-time updates for:
- Project status changes
- Resource usage updates
- Deployment progress
- Backup operations
- Environment switches

## Key Components

### OrchestrationPanel
Main interface for project management with:
- Project grid/list view toggle
- Real-time status indicators
- Quick action buttons
- System summary cards
- Environment management

### DeploymentDashboard
Comprehensive deployment management with:
- Multi-environment status overview
- Pipeline progress visualization
- Deployment history and comparison
- Real-time deployment logs
- Rollback controls

### ResourceMonitor
Advanced resource monitoring featuring:
- Interactive charts with multiple time ranges
- Resource allocation controls
- Performance recommendations
- System-wide resource summary
- Project-specific usage details

### BackupManager
Complete backup solution with:
- Automated scheduling with cron expressions
- Manual backup creation
- Backup validation and verification
- Storage usage visualization
- Easy restoration workflows

## State Management

### Global State (Zustand)
- Theme preferences
- User interface settings
- Dashboard configurations

### Server State (React Query)
- Project data with automatic caching
- Real-time status updates
- Background refetching
- Optimistic updates
- Error handling and retries

### WebSocket State
- Real-time event handling
- Connection status management
- Automatic reconnection
- Message queuing and processing

## Performance Optimizations

### Code Splitting
- Lazy loading of route components
- Dynamic imports for large dependencies
- Bundle size optimization

### Rendering Optimizations
- React.memo for component memoization
- Proper dependency arrays in hooks
- Virtualization for large lists
- Debounced search and filters

### Network Optimizations
- Query result caching
- Background refetching
- Request deduplication
- Optimistic updates

## Testing Strategy

### Component Testing
- Unit tests for individual components
- Integration tests for complex workflows
- Mock API responses and WebSocket events
- Accessibility testing

### Test Examples
```typescript
// Component testing with React Testing Library
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ProjectCard } from '../ProjectCard';

describe('ProjectCard', () => {
  it('launches project when launch button is clicked', async () => {
    render(<ProjectCard {...props} />);
    
    const launchButton = screen.getByRole('button', { name: /launch/i });
    fireEvent.click(launchButton);

    await waitFor(() => {
      expect(mockLaunchAction).toHaveBeenCalledWith({
        environment: 'dev',
        wait_for_health: true,
      });
    });
  });
});
```

## Development Setup

### Prerequisites
- Node.js 18+ and npm/yarn
- Backend Optimus service running
- WebSocket endpoints configured

### Installation
```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Run tests
npm run test

# Type checking
npm run type-check
```

### Environment Configuration
```bash
# .env.local
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
VITE_ENABLE_DEV_TOOLS=true
```

## Usage Examples

### Launching a Project
1. Navigate to the Orchestration page
2. Select a project from the grid
3. Choose environment (dev/staging/prod)
4. Click "Launch" and monitor progress
5. View real-time logs and status updates

### Creating a Deployment
1. Go to the Deployment page
2. Select target project and environment
3. Configure deployment strategy
4. Monitor pipeline progress in real-time
5. Review deployment status and logs

### Managing Resources
1. Open the Resources page
2. View system-wide resource usage
3. Set resource limits for projects
4. Monitor performance trends
5. Follow optimization recommendations

### Setting Up Backups
1. Visit the Backup page
2. Create backup schedules with cron expressions
3. Configure retention policies
4. Monitor backup status and storage
5. Restore from any backup point

## Integration with Backend

### API Client Architecture
- Type-safe API clients with full TypeScript support
- Automatic error handling and retry logic
- Request/response interceptors for auth and logging
- Centralized API configuration

### WebSocket Integration
- Automatic connection management
- Real-time data synchronization
- Graceful degradation when WebSocket unavailable
- Message queuing during connection loss

### Error Handling
- Global error boundary for crash recovery
- API error handling with user-friendly messages
- Network error detection and retry
- Offline state management

## Accessibility

### WCAG Compliance
- Keyboard navigation support
- Screen reader compatibility
- High contrast mode support
- Focus management in modals

### Responsive Design
- Mobile-first approach
- Tablet and desktop optimizations
- Touch-friendly interface
- Adaptive layouts

## Security Considerations

### Client-Side Security
- XSS prevention with proper sanitization
- CSRF protection for API requests
- Secure WebSocket connections (WSS in production)
- Input validation and sanitization

### Data Protection
- Sensitive data handling
- Secure storage of tokens
- Proper error message sanitization
- No sensitive data in logs

## Future Enhancements

### Planned Features
- Advanced analytics and reporting
- Custom dashboard layouts
- Team collaboration features
- Integration with external monitoring tools
- Mobile application

### Technical Improvements
- Progressive Web App (PWA) capabilities
- Advanced caching strategies
- Performance monitoring integration
- Enhanced accessibility features
- Internationalization (i18n) support

## Contributing

### Development Guidelines
1. Follow TypeScript best practices
2. Write comprehensive tests for new features
3. Update documentation for API changes
4. Follow established component patterns
5. Ensure accessibility compliance

### Code Style
- Use Prettier for code formatting
- Follow ESLint configuration
- Write meaningful commit messages
- Use conventional commit format
- Update CHANGELOG for significant changes

---

This dashboard provides a complete, production-ready interface for the Optimus Orchestration Service, combining powerful functionality with an intuitive user experience. The modular architecture and comprehensive testing ensure maintainability and reliability for complex project management workflows.