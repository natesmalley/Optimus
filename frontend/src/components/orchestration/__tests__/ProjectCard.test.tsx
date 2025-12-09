/**
 * Test suite for ProjectCard component
 * Tests project card rendering, status display, and user interactions
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProjectCard } from '../ProjectCard';
import { useProjectActions } from '../../../hooks/useOrchestration';
import type { Project, OrchestrationStatus } from '../../../types/api';

// Mock the hooks
jest.mock('../../../hooks/useOrchestration');
const mockUseProjectActions = useProjectActions as jest.MockedFunction<typeof useProjectActions>;

// Mock project data
const mockProject: Project = {
  id: 'test-project-1',
  name: 'Test Project',
  path: '/test/path',
  description: 'A test project',
  tech_stack: { javascript: true },
  dependencies: {},
  status: 'active',
  git_url: 'https://github.com/test/repo',
  default_branch: 'main',
  language_stats: { javascript: 100 },
  created_at: '2023-01-01T00:00:00Z',
  updated_at: '2023-01-02T00:00:00Z',
  is_running: false,
  process_count: 0,
  running_ports: [],
  latest_quality_score: 85,
  open_issues_count: 2,
  monetization_opportunities: 3,
};

const mockOrchestrationStatus: OrchestrationStatus = {
  project_id: 'test-project-1',
  project_name: 'Test Project',
  is_running: false,
  environment: 'dev',
  pid: undefined,
  port: undefined,
  health_check_url: undefined,
  last_heartbeat: undefined,
  cpu_usage: 0,
  memory_usage: 0,
  status_details: 'Stopped',
};

// Setup query client
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('ProjectCard', () => {
  const mockActions = {
    launch: jest.fn(),
    stop: jest.fn(),
    restart: jest.fn(),
    switchEnvironment: jest.fn(),
    isLaunching: false,
    isStopping: false,
    isSwitchingEnvironment: false,
    isLoading: false,
    error: null,
  };

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseProjectActions.mockReturnValue(mockActions);
  });

  it('renders project information correctly', () => {
    render(
      <ProjectCard
        project={mockProject}
        orchestrationStatus={mockOrchestrationStatus}
        isSelected={false}
        onSelect={jest.fn()}
        viewMode="grid"
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText('Test Project')).toBeInTheDocument();
    expect(screen.getByText('A test project')).toBeInTheDocument();
    expect(screen.getByText('dev')).toBeInTheDocument();
    expect(screen.getByText('Stopped')).toBeInTheDocument();
  });

  it('displays running status when project is running', () => {
    const runningStatus = {
      ...mockOrchestrationStatus,
      is_running: true,
      port: 3000,
      start_time: '2023-01-01T10:00:00Z',
    };

    render(
      <ProjectCard
        project={mockProject}
        orchestrationStatus={runningStatus}
        isSelected={false}
        onSelect={jest.fn()}
        viewMode="grid"
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText('Running')).toBeInTheDocument();
    expect(screen.getByText('3000')).toBeInTheDocument();
  });

  it('shows launch button when project is stopped', () => {
    render(
      <ProjectCard
        project={mockProject}
        orchestrationStatus={mockOrchestrationStatus}
        isSelected={false}
        onSelect={jest.fn()}
        viewMode="grid"
      />,
      { wrapper: createWrapper() }
    );

    const launchButton = screen.getByRole('button', { name: /launch/i });
    expect(launchButton).toBeInTheDocument();
    expect(launchButton).not.toBeDisabled();
  });

  it('shows stop and restart buttons when project is running', () => {
    const runningStatus = {
      ...mockOrchestrationStatus,
      is_running: true,
    };

    render(
      <ProjectCard
        project={mockProject}
        orchestrationStatus={runningStatus}
        isSelected={false}
        onSelect={jest.fn()}
        viewMode="grid"
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByRole('button', { name: /stop/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /restart/i })).toBeInTheDocument();
  });

  it('calls launch action when launch button is clicked', async () => {
    render(
      <ProjectCard
        project={mockProject}
        orchestrationStatus={mockOrchestrationStatus}
        isSelected={false}
        onSelect={jest.fn()}
        viewMode="grid"
      />,
      { wrapper: createWrapper() }
    );

    const launchButton = screen.getByRole('button', { name: /launch/i });
    fireEvent.click(launchButton);

    await waitFor(() => {
      expect(mockActions.launch).toHaveBeenCalledWith({
        environment: 'dev',
        wait_for_health: true,
      });
    });
  });

  it('calls stop action when stop button is clicked', async () => {
    const runningStatus = {
      ...mockOrchestrationStatus,
      is_running: true,
    };

    render(
      <ProjectCard
        project={mockProject}
        orchestrationStatus={runningStatus}
        isSelected={false}
        onSelect={jest.fn()}
        viewMode="grid"
      />,
      { wrapper: createWrapper() }
    );

    const stopButton = screen.getByRole('button', { name: /stop/i });
    fireEvent.click(stopButton);

    await waitFor(() => {
      expect(mockActions.stop).toHaveBeenCalledWith({
        timeout: 30,
      });
    });
  });

  it('shows loading state when action is in progress', () => {
    mockUseProjectActions.mockReturnValue({
      ...mockActions,
      isLaunching: true,
      isLoading: true,
    });

    render(
      <ProjectCard
        project={mockProject}
        orchestrationStatus={mockOrchestrationStatus}
        isSelected={false}
        onSelect={jest.fn()}
        viewMode="grid"
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText('Launching...')).toBeInTheDocument();
    const launchButton = screen.getByRole('button', { name: /launching/i });
    expect(launchButton).toBeDisabled();
  });

  it('displays error message when there is an error', () => {
    const error = new Error('Failed to start project');
    mockUseProjectActions.mockReturnValue({
      ...mockActions,
      error,
    });

    render(
      <ProjectCard
        project={mockProject}
        orchestrationStatus={mockOrchestrationStatus}
        isSelected={false}
        onSelect={jest.fn()}
        viewMode="grid"
      />,
      { wrapper: createWrapper() }
    );

    expect(screen.getByText('Error')).toBeInTheDocument();
    expect(screen.getByText('Failed to start project')).toBeInTheDocument();
  });

  it('renders in list view mode', () => {
    const { container } = render(
      <ProjectCard
        project={mockProject}
        orchestrationStatus={mockOrchestrationStatus}
        isSelected={false}
        onSelect={jest.fn()}
        viewMode="list"
      />,
      { wrapper: createWrapper() }
    );

    // List view should have different layout classes
    expect(container.firstChild).toHaveClass('flex', 'items-center');
  });

  it('calls onSelect when settings button is clicked', () => {
    const onSelect = jest.fn();

    render(
      <ProjectCard
        project={mockProject}
        orchestrationStatus={mockOrchestrationStatus}
        isSelected={false}
        onSelect={onSelect}
        viewMode="grid"
      />,
      { wrapper: createWrapper() }
    );

    const settingsButton = screen.getByRole('button', { name: /settings/i });
    fireEvent.click(settingsButton);

    expect(onSelect).toHaveBeenCalled();
  });

  it('opens project in browser when port is available and external link is clicked', () => {
    const runningStatus = {
      ...mockOrchestrationStatus,
      is_running: true,
      port: 3000,
    };

    // Mock window.open
    const mockOpen = jest.fn();
    Object.defineProperty(window, 'open', {
      writable: true,
      value: mockOpen,
    });

    render(
      <ProjectCard
        project={mockProject}
        orchestrationStatus={runningStatus}
        isSelected={false}
        onSelect={jest.fn()}
        viewMode="grid"
      />,
      { wrapper: createWrapper() }
    );

    const externalLinkButton = screen.getByRole('button', { name: '' }); // External link has no text
    fireEvent.click(externalLinkButton);

    expect(mockOpen).toHaveBeenCalledWith('http://localhost:3000', '_blank');
  });

  it('toggles details visibility when show/hide details is clicked', () => {
    render(
      <ProjectCard
        project={mockProject}
        orchestrationStatus={mockOrchestrationStatus}
        isSelected={false}
        onSelect={jest.fn()}
        viewMode="grid"
      />,
      { wrapper: createWrapper() }
    );

    const detailsButton = screen.getByText('Show Details');
    fireEvent.click(detailsButton);

    expect(screen.getByText('Hide Details')).toBeInTheDocument();
    expect(screen.getByText(/path:/i)).toBeInTheDocument();
    expect(screen.getByText(mockProject.path)).toBeInTheDocument();
  });
});

// Integration test example
describe('ProjectCard Integration', () => {
  it('handles complete launch workflow', async () => {
    const mockActions = {
      launch: jest.fn().mockResolvedValue({}),
      stop: jest.fn(),
      restart: jest.fn(),
      switchEnvironment: jest.fn(),
      isLaunching: false,
      isStopping: false,
      isSwitchingEnvironment: false,
      isLoading: false,
      error: null,
    };

    mockUseProjectActions.mockReturnValue(mockActions);

    render(
      <ProjectCard
        project={mockProject}
        orchestrationStatus={mockOrchestrationStatus}
        isSelected={false}
        onSelect={jest.fn()}
        viewMode="grid"
      />,
      { wrapper: createWrapper() }
    );

    // Click launch
    const launchButton = screen.getByRole('button', { name: /launch/i });
    fireEvent.click(launchButton);

    // Verify launch was called with correct parameters
    await waitFor(() => {
      expect(mockActions.launch).toHaveBeenCalledWith({
        environment: 'dev',
        wait_for_health: true,
      });
    });
  });
});