# Optimus Dashboard Frontend

A modern React TypeScript dashboard for the Optimus project orchestrator, providing comprehensive project monitoring, runtime analysis, and performance insights.

## Features

### 🎯 Core Functionality
- **Project Dashboard**: Grid and list views with advanced filtering
- **Real-time Monitoring**: Live system resource usage and process tracking
- **Analytics Dashboard**: Health scores, technology trends, and performance metrics
- **Project Details**: Comprehensive runtime status and analysis results

### 🎨 User Experience
- **Responsive Design**: Optimized for desktop, tablet, and mobile
- **Dark/Light Theme**: System preference detection with manual override
- **Real-time Updates**: Auto-refresh with configurable intervals
- **Toast Notifications**: User feedback for actions and errors

### 🏗 Technical Features
- **TypeScript**: Full type safety and excellent developer experience
- **Modern React**: Hooks, Context, and functional components
- **State Management**: Zustand for global state with persistence
- **API Integration**: React Query for server state management
- **Responsive Charts**: Recharts for data visualization

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── layout/         # Layout components (Header, Sidebar)
│   └── ui/             # Base UI components
├── pages/              # Page components
│   ├── Dashboard.tsx   # Main project dashboard
│   ├── ProjectDetail.tsx # Project details view
│   ├── SystemMonitor.tsx # Real-time monitoring
│   └── Analytics.tsx   # Analytics and charts
├── lib/                # Utilities and API client
│   ├── api.ts         # HTTP client for backend
│   └── utils.ts       # Helper functions
├── store/              # Global state management
├── types/              # TypeScript definitions
├── hooks/              # Custom React hooks
└── styles/             # CSS and styling
```

## Getting Started

### Prerequisites
- Node.js 18+ 
- npm or yarn
- Optimus backend running on http://localhost:8000

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Environment Setup

The frontend is configured to proxy API requests to the backend:

- Development: http://localhost:3000 → http://localhost:8000/api/v1
- Production: Configure reverse proxy or environment variables

## API Integration

The frontend integrates with the Optimus FastAPI backend through a typed HTTP client:

### Endpoints Used
- `GET /api/v1/projects` - Project listing and search
- `GET /api/v1/projects/{id}` - Project details
- `GET /api/v1/runtime` - System runtime overview
- `GET /api/v1/metrics` - Performance metrics
- `POST /api/v1/projects/{id}/scan` - Trigger project scan

### Real-time Updates
- Polling-based updates with configurable intervals
- Automatic refresh for critical data (every 5-30 seconds)
- Manual refresh controls

## State Management

### Global State (Zustand)
- **Theme Store**: Dark/light mode preferences
- **Dashboard Store**: View preferences and settings
- **Projects Store**: Project data and filters
- **Runtime Store**: System monitoring data
- **Toast Store**: Notification management

### Server State (React Query)
- Caching and background updates
- Error handling and retry logic
- Optimistic updates for mutations

## Components Architecture

### Layout Components
- **Layout**: Main application shell
- **Sidebar**: Navigation with collapsible design
- **Header**: Search, theme toggle, and user controls

### UI Components
- **StatusBadge**: Project and process status indicators
- **LoadingSpinner**: Consistent loading states
- **ToastProvider**: Notification system

### Page Components
- **Dashboard**: Project cards with filtering and search
- **ProjectDetail**: Runtime processes and health scores
- **SystemMonitor**: Real-time resource monitoring
- **Analytics**: Charts and performance insights

## Responsive Design

### Breakpoints
- Mobile: < 768px
- Tablet: 768px - 1024px
- Desktop: > 1024px

### Mobile Optimizations
- Collapsible sidebar
- Touch-friendly interactions
- Responsive grid layouts
- Mobile-optimized charts

## Development

### Code Quality
- ESLint with TypeScript rules
- Prettier for consistent formatting
- Strict TypeScript configuration
- Component prop validation

### Performance
- React Query for efficient data fetching
- Code splitting for bundle optimization
- Lazy loading for routes
- Optimized re-renders with proper memoization

### Testing Strategy
- Component testing with React Testing Library
- API mocking for integration tests
- Type checking as part of CI/CD

## Deployment

### Build Process
```bash
# Type check
npm run type-check

# Lint code
npm run lint

# Build for production
npm run build
```

### Production Considerations
- Environment variables for API endpoints
- CDN deployment for static assets
- Gzip compression
- Browser caching strategies

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Contributing

1. Follow the existing code style
2. Add TypeScript types for new features
3. Include responsive design considerations
4. Test on multiple screen sizes
5. Update this documentation for significant changes

## Architecture Decisions

### Why Zustand over Redux?
- Simpler API and less boilerplate
- Better TypeScript integration
- Built-in persistence support
- Smaller bundle size

### Why React Query?
- Excellent caching and background updates
- Built-in loading and error states
- Optimistic updates support
- DevTools integration

### Why Tailwind CSS?
- Utility-first approach for rapid development
- Consistent design system
- Excellent responsive utilities
- Small production bundle with purging

## Future Enhancements

- [ ] WebSocket integration for real-time updates
- [ ] Advanced filtering and search
- [ ] Export functionality for reports
- [ ] Keyboard shortcuts
- [ ] Advanced analytics and insights
- [ ] Multi-user support with authentication