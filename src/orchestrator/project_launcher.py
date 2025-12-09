"""
Project Launcher Service

Manages the complete lifecycle of project processes including starting, stopping,
restarting, and monitoring project health across different technology stacks.
"""

import asyncio
import os
import signal
import subprocess
import json
import logging
import psutil
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ProjectStatus(Enum):
    """Project execution status enumeration."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    CRASHED = "crashed"
    UNKNOWN = "unknown"


class ProjectType(Enum):
    """Supported project types."""
    PYTHON = "python"
    NODE = "node"
    DOCKER = "docker"
    GO = "go"
    RUST = "rust"
    PHP = "php"
    JAVA = "java"
    DOTNET = "dotnet"
    STATIC = "static"
    UNKNOWN = "unknown"


@dataclass
class ProcessInfo:
    """Information about a running process."""
    pid: int
    name: str
    status: str
    cpu_percent: float
    memory_rss: int
    memory_percent: float
    ports: List[int] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    command: Optional[str] = None
    environment: Optional[str] = None
    logs_path: Optional[str] = None


@dataclass
class RunningProject:
    """Information about a running project."""
    project_id: str
    name: str
    path: str
    project_type: ProjectType
    status: ProjectStatus
    processes: List[ProcessInfo] = field(default_factory=list)
    primary_port: Optional[int] = None
    health_url: Optional[str] = None
    started_at: Optional[datetime] = None
    environment: str = "development"
    resource_limits: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StartupConfig:
    """Configuration for starting a project."""
    command: Optional[str] = None
    environment: str = "development"
    ports: List[int] = field(default_factory=list)
    env_vars: Dict[str, str] = field(default_factory=dict)
    working_dir: Optional[str] = None
    health_check_url: Optional[str] = None
    health_check_timeout: int = 30
    startup_timeout: int = 60
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    auto_restart: bool = False
    log_file: Optional[str] = None


class ProjectLauncher:
    """
    Manages project lifecycle operations including start, stop, restart, and monitoring.
    
    Supports multiple project types and provides comprehensive process management
    with health checking, resource monitoring, and automatic recovery.
    """
    
    def __init__(self, base_projects_path: str = "/Users/nathanial.smalley/projects"):
        """
        Initialize the ProjectLauncher.
        
        Args:
            base_projects_path: Base directory containing all projects
        """
        self.base_projects_path = Path(base_projects_path)
        self.running_projects: Dict[str, RunningProject] = {}
        self.startup_configs: Dict[str, StartupConfig] = {}
        
        # Port management
        self.allocated_ports: Dict[int, str] = {}  # port -> project_id
        self.port_range_start = 3000
        self.port_range_end = 9999
        
        # Process monitoring
        self.monitor_interval = 5  # seconds
        self.health_check_interval = 30  # seconds
        
        logger.info(f"ProjectLauncher initialized with base path: {self.base_projects_path}")
    
    async def start_project(
        self, 
        project_id: str, 
        environment: str = "development",
        custom_config: Optional[StartupConfig] = None
    ) -> ProcessInfo:
        """
        Start a project with the specified environment.
        
        Args:
            project_id: Unique identifier for the project
            environment: Target environment (development, staging, production)
            custom_config: Optional custom startup configuration
            
        Returns:
            ProcessInfo: Information about the started process
            
        Raises:
            ValueError: If project not found or configuration invalid
            RuntimeError: If startup fails
        """
        logger.info(f"Starting project {project_id} in {environment} environment")
        
        try:
            # Get or create startup configuration
            config = custom_config or await self._get_startup_config(project_id, environment)
            
            # Detect project path and type
            project_path = await self._find_project_path(project_id)
            project_type = await self._detect_project_type(project_path)
            
            # Check if already running
            if project_id in self.running_projects:
                current_status = await self.get_project_status(project_id)
                if current_status.status in [ProjectStatus.RUNNING, ProjectStatus.STARTING]:
                    logger.warning(f"Project {project_id} is already running")
                    return self.running_projects[project_id].processes[0]
            
            # Allocate ports
            allocated_ports = await self._allocate_ports(project_id, config.ports)
            
            # Prepare environment variables
            env_vars = await self._prepare_environment(project_path, environment, config)
            
            # Build startup command
            startup_command = await self._build_startup_command(
                project_path, project_type, config, allocated_ports
            )
            
            # Create log file
            log_file = await self._setup_logging(project_id, environment)
            
            # Start the process
            process_info = await self._start_process(
                project_id, 
                startup_command, 
                project_path,
                env_vars,
                log_file,
                config
            )
            
            # Register running project
            await self._register_running_project(
                project_id, 
                project_path, 
                project_type, 
                process_info, 
                environment,
                allocated_ports,
                config
            )
            
            # Start health monitoring
            asyncio.create_task(self._monitor_project_health(project_id))
            
            logger.info(f"Successfully started project {project_id} with PID {process_info.pid}")
            return process_info
            
        except Exception as e:
            logger.error(f"Failed to start project {project_id}: {str(e)}")
            # Cleanup on failure
            await self._cleanup_failed_start(project_id)
            raise RuntimeError(f"Failed to start project {project_id}: {str(e)}")
    
    async def stop_project(self, project_id: str, graceful: bool = True) -> bool:
        """
        Stop a running project.
        
        Args:
            project_id: Project to stop
            graceful: Whether to attempt graceful shutdown first
            
        Returns:
            bool: True if successfully stopped
        """
        logger.info(f"Stopping project {project_id} (graceful={graceful})")
        
        if project_id not in self.running_projects:
            logger.warning(f"Project {project_id} is not running")
            return True
        
        try:
            project = self.running_projects[project_id]
            project.status = ProjectStatus.STOPPING
            
            # Stop all processes
            success = True
            for process_info in project.processes:
                if not await self._stop_process(process_info, graceful):
                    success = False
            
            # Release ports
            await self._release_ports(project_id)
            
            # Update status
            project.status = ProjectStatus.STOPPED
            
            # Remove from running projects
            del self.running_projects[project_id]
            
            logger.info(f"Successfully stopped project {project_id}")
            return success
            
        except Exception as e:
            logger.error(f"Failed to stop project {project_id}: {str(e)}")
            return False
    
    async def restart_project(self, project_id: str, environment: Optional[str] = None) -> ProcessInfo:
        """
        Restart a project with optional environment change.
        
        Args:
            project_id: Project to restart
            environment: New environment (if different)
            
        Returns:
            ProcessInfo: Information about the restarted process
        """
        logger.info(f"Restarting project {project_id}")
        
        # Determine environment
        current_env = "development"
        if project_id in self.running_projects:
            current_env = self.running_projects[project_id].environment
        
        target_env = environment or current_env
        
        # Stop if running
        if project_id in self.running_projects:
            await self.stop_project(project_id, graceful=True)
        
        # Wait a moment for cleanup
        await asyncio.sleep(2)
        
        # Start with new configuration
        return await self.start_project(project_id, target_env)
    
    async def get_project_status(self, project_id: str) -> RunningProject:
        """
        Get current status of a project.
        
        Args:
            project_id: Project to check
            
        Returns:
            RunningProject: Current project status
        """
        if project_id not in self.running_projects:
            # Check if process exists but not tracked
            return RunningProject(
                project_id=project_id,
                name=project_id,
                path="",
                project_type=ProjectType.UNKNOWN,
                status=ProjectStatus.STOPPED
            )
        
        project = self.running_projects[project_id]
        
        # Update process status
        updated_processes = []
        for process_info in project.processes:
            try:
                process = psutil.Process(process_info.pid)
                if process.is_running():
                    # Update metrics
                    process_info.cpu_percent = process.cpu_percent()
                    process_info.memory_rss = process.memory_info().rss
                    process_info.memory_percent = process.memory_percent()
                    process_info.last_seen = datetime.now()
                    process_info.status = "running"
                    updated_processes.append(process_info)
                else:
                    process_info.status = "stopped"
            except psutil.NoSuchProcess:
                process_info.status = "crashed"
            except Exception as e:
                logger.error(f"Error checking process {process_info.pid}: {e}")
                process_info.status = "unknown"
        
        project.processes = updated_processes
        
        # Update project status based on processes
        if not project.processes:
            project.status = ProjectStatus.STOPPED
        elif all(p.status == "running" for p in project.processes):
            project.status = ProjectStatus.RUNNING
        elif any(p.status == "crashed" for p in project.processes):
            project.status = ProjectStatus.CRASHED
        else:
            project.status = ProjectStatus.UNKNOWN
        
        return project
    
    async def list_running_projects(self) -> List[RunningProject]:
        """
        Get list of all running projects with current status.
        
        Returns:
            List[RunningProject]: All running projects
        """
        result = []
        
        for project_id in list(self.running_projects.keys()):
            try:
                project_status = await self.get_project_status(project_id)
                if project_status.status != ProjectStatus.STOPPED:
                    result.append(project_status)
            except Exception as e:
                logger.error(f"Error getting status for project {project_id}: {e}")
        
        return result
    
    async def kill_project(self, project_id: str) -> bool:
        """
        Forcefully kill a project (non-graceful).
        
        Args:
            project_id: Project to kill
            
        Returns:
            bool: True if successfully killed
        """
        logger.warning(f"Force killing project {project_id}")
        return await self.stop_project(project_id, graceful=False)
    
    async def get_project_logs(self, project_id: str, lines: int = 100) -> List[str]:
        """
        Get recent log lines for a project.
        
        Args:
            project_id: Project to get logs for
            lines: Number of recent lines to return
            
        Returns:
            List[str]: Recent log lines
        """
        if project_id not in self.running_projects:
            return []
        
        project = self.running_projects[project_id]
        log_files = []
        
        for process_info in project.processes:
            if process_info.logs_path and os.path.exists(process_info.logs_path):
                log_files.append(process_info.logs_path)
        
        if not log_files:
            return []
        
        # Read from the first log file (primary process)
        try:
            with open(log_files[0], 'r') as f:
                return f.readlines()[-lines:]
        except Exception as e:
            logger.error(f"Error reading logs for {project_id}: {e}")
            return []
    
    # Private helper methods
    
    async def _find_project_path(self, project_id: str) -> Path:
        """Find the filesystem path for a project."""
        project_path = self.base_projects_path / project_id
        if project_path.exists():
            return project_path
        
        # Search for project in subdirectories
        for item in self.base_projects_path.iterdir():
            if item.is_dir() and item.name.lower() == project_id.lower():
                return item
        
        raise ValueError(f"Project {project_id} not found in {self.base_projects_path}")
    
    async def _detect_project_type(self, project_path: Path) -> ProjectType:
        """Detect the project type based on files present."""
        if (project_path / "package.json").exists():
            return ProjectType.NODE
        elif (project_path / "requirements.txt").exists() or (project_path / "pyproject.toml").exists():
            return ProjectType.PYTHON
        elif (project_path / "Dockerfile").exists() or (project_path / "docker-compose.yml").exists():
            return ProjectType.DOCKER
        elif (project_path / "go.mod").exists():
            return ProjectType.GO
        elif (project_path / "Cargo.toml").exists():
            return ProjectType.RUST
        elif (project_path / "composer.json").exists():
            return ProjectType.PHP
        elif (project_path / "pom.xml").exists() or (project_path / "build.gradle").exists():
            return ProjectType.JAVA
        elif (project_path / "*.csproj").glob("*.csproj"):
            return ProjectType.DOTNET
        elif (project_path / "index.html").exists():
            return ProjectType.STATIC
        else:
            return ProjectType.UNKNOWN
    
    async def _get_startup_config(self, project_id: str, environment: str) -> StartupConfig:
        """Get or create startup configuration for a project."""
        if project_id in self.startup_configs:
            return self.startup_configs[project_id]
        
        # Try to load from project directory
        project_path = await self._find_project_path(project_id)
        config_file = project_path / "optimus.yml"
        
        if config_file.exists():
            try:
                with open(config_file) as f:
                    config_data = yaml.safe_load(f)
                    env_config = config_data.get("environments", {}).get(environment, {})
                    
                    config = StartupConfig(
                        command=env_config.get("command"),
                        environment=environment,
                        ports=env_config.get("ports", []),
                        env_vars=env_config.get("env_vars", {}),
                        working_dir=env_config.get("working_dir"),
                        health_check_url=env_config.get("health_check_url"),
                        health_check_timeout=env_config.get("health_check_timeout", 30),
                        startup_timeout=env_config.get("startup_timeout", 60),
                        resource_limits=env_config.get("resource_limits", {}),
                        auto_restart=env_config.get("auto_restart", False)
                    )
                    
                    self.startup_configs[project_id] = config
                    return config
            except Exception as e:
                logger.warning(f"Failed to load config file for {project_id}: {e}")
        
        # Default configuration
        config = StartupConfig(environment=environment)
        self.startup_configs[project_id] = config
        return config
    
    async def _allocate_ports(self, project_id: str, requested_ports: List[int]) -> List[int]:
        """Allocate ports for a project, avoiding conflicts."""
        allocated = []
        
        for port in requested_ports:
            if port in self.allocated_ports:
                if self.allocated_ports[port] != project_id:
                    # Find alternative port
                    port = await self._find_free_port()
            
            if await self._is_port_free(port):
                self.allocated_ports[port] = project_id
                allocated.append(port)
            else:
                # Find alternative port
                free_port = await self._find_free_port()
                self.allocated_ports[free_port] = project_id
                allocated.append(free_port)
        
        # If no ports requested, allocate one
        if not requested_ports:
            free_port = await self._find_free_port()
            self.allocated_ports[free_port] = project_id
            allocated.append(free_port)
        
        return allocated
    
    async def _find_free_port(self) -> int:
        """Find a free port in the configured range."""
        for port in range(self.port_range_start, self.port_range_end + 1):
            if await self._is_port_free(port):
                return port
        
        raise RuntimeError("No free ports available in range")
    
    async def _is_port_free(self, port: int) -> bool:
        """Check if a port is free."""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return True
        except socket.error:
            return False
    
    async def _prepare_environment(
        self, 
        project_path: Path, 
        environment: str, 
        config: StartupConfig
    ) -> Dict[str, str]:
        """Prepare environment variables for the process."""
        env_vars = os.environ.copy()
        
        # Load .env file if exists
        env_file = project_path / f".env.{environment}"
        if not env_file.exists():
            env_file = project_path / ".env"
        
        if env_file.exists():
            try:
                with open(env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            key, value = line.split("=", 1)
                            env_vars[key.strip()] = value.strip()
            except Exception as e:
                logger.warning(f"Failed to load environment file {env_file}: {e}")
        
        # Add config environment variables
        env_vars.update(config.env_vars)
        
        # Add Optimus-specific variables
        env_vars["OPTIMUS_ENVIRONMENT"] = environment
        env_vars["OPTIMUS_PROJECT_PATH"] = str(project_path)
        
        return env_vars
    
    async def _build_startup_command(
        self, 
        project_path: Path, 
        project_type: ProjectType, 
        config: StartupConfig,
        allocated_ports: List[int]
    ) -> List[str]:
        """Build the startup command based on project type."""
        if config.command:
            # Use custom command
            command = config.command.replace("$PORT", str(allocated_ports[0]) if allocated_ports else "3000")
            return command.split()
        
        # Default commands based on project type
        if project_type == ProjectType.NODE:
            if (project_path / "package.json").exists():
                with open(project_path / "package.json") as f:
                    package_data = json.load(f)
                    scripts = package_data.get("scripts", {})
                    
                    if "start" in scripts:
                        return ["npm", "start"]
                    elif "dev" in scripts and config.environment == "development":
                        return ["npm", "run", "dev"]
                    else:
                        return ["node", "index.js"]
            return ["node", "index.js"]
        
        elif project_type == ProjectType.PYTHON:
            # Check for common Python entry points
            if (project_path / "main.py").exists():
                return ["python", "main.py"]
            elif (project_path / "app.py").exists():
                return ["python", "app.py"]
            elif (project_path / "manage.py").exists():
                return ["python", "manage.py", "runserver", f"0.0.0.0:{allocated_ports[0] if allocated_ports else 8000}"]
            else:
                return ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", f"--port", str(allocated_ports[0] if allocated_ports else 8000)]
        
        elif project_type == ProjectType.DOCKER:
            if (project_path / "docker-compose.yml").exists():
                return ["docker-compose", "up"]
            else:
                return ["docker", "run", "-p", f"{allocated_ports[0] if allocated_ports else 3000}:3000", "."]
        
        elif project_type == ProjectType.GO:
            return ["go", "run", "."]
        
        elif project_type == ProjectType.RUST:
            return ["cargo", "run"]
        
        else:
            raise ValueError(f"Unsupported project type: {project_type}")
    
    async def _setup_logging(self, project_id: str, environment: str) -> str:
        """Setup log file for the project."""
        logs_dir = Path("logs") / project_id
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        log_file = logs_dir / f"{environment}.log"
        return str(log_file)
    
    async def _start_process(
        self,
        project_id: str,
        command: List[str],
        working_dir: Path,
        env_vars: Dict[str, str],
        log_file: str,
        config: StartupConfig
    ) -> ProcessInfo:
        """Start the actual process."""
        logger.info(f"Starting process: {' '.join(command)} in {working_dir}")
        
        try:
            # Open log file
            log_handle = open(log_file, "a")
            
            # Start process
            process = subprocess.Popen(
                command,
                cwd=working_dir,
                env=env_vars,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
            
            # Wait a moment to ensure process started
            await asyncio.sleep(1)
            
            if process.poll() is not None:
                raise RuntimeError(f"Process exited immediately with code {process.returncode}")
            
            # Get process info
            psutil_process = psutil.Process(process.pid)
            
            process_info = ProcessInfo(
                pid=process.pid,
                name=command[0],
                status="starting",
                cpu_percent=0.0,
                memory_rss=psutil_process.memory_info().rss,
                memory_percent=psutil_process.memory_percent(),
                command=" ".join(command),
                environment=config.environment,
                logs_path=log_file
            )
            
            return process_info
            
        except Exception as e:
            logger.error(f"Failed to start process: {e}")
            raise
    
    async def _register_running_project(
        self,
        project_id: str,
        project_path: Path,
        project_type: ProjectType,
        process_info: ProcessInfo,
        environment: str,
        allocated_ports: List[int],
        config: StartupConfig
    ):
        """Register a project as running."""
        project = RunningProject(
            project_id=project_id,
            name=project_id,
            path=str(project_path),
            project_type=project_type,
            status=ProjectStatus.STARTING,
            processes=[process_info],
            primary_port=allocated_ports[0] if allocated_ports else None,
            health_url=config.health_check_url,
            started_at=datetime.now(),
            environment=environment,
            resource_limits=config.resource_limits
        )
        
        self.running_projects[project_id] = project
    
    async def _monitor_project_health(self, project_id: str):
        """Background task to monitor project health."""
        while project_id in self.running_projects:
            try:
                project = self.running_projects[project_id]
                
                # Update process status
                await self.get_project_status(project_id)
                
                # Check health endpoint if configured
                if project.health_url:
                    try:
                        import aiohttp
                        async with aiohttp.ClientSession() as session:
                            async with session.get(project.health_url, timeout=5) as response:
                                if response.status == 200:
                                    project.status = ProjectStatus.RUNNING
                                else:
                                    logger.warning(f"Health check failed for {project_id}: {response.status}")
                    except Exception as e:
                        logger.warning(f"Health check error for {project_id}: {e}")
                
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Error monitoring project {project_id}: {e}")
                await asyncio.sleep(self.health_check_interval)
    
    async def _stop_process(self, process_info: ProcessInfo, graceful: bool) -> bool:
        """Stop a single process."""
        try:
            process = psutil.Process(process_info.pid)
            
            if graceful:
                # Try graceful shutdown first
                process.terminate()
                try:
                    process.wait(timeout=10)
                except psutil.TimeoutExpired:
                    logger.warning(f"Process {process_info.pid} did not terminate gracefully, killing")
                    process.kill()
            else:
                process.kill()
            
            return True
            
        except psutil.NoSuchProcess:
            logger.info(f"Process {process_info.pid} already stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping process {process_info.pid}: {e}")
            return False
    
    async def _release_ports(self, project_id: str):
        """Release all ports allocated to a project."""
        ports_to_release = [port for port, pid in self.allocated_ports.items() if pid == project_id]
        for port in ports_to_release:
            del self.allocated_ports[port]
        logger.info(f"Released ports {ports_to_release} for project {project_id}")
    
    async def _cleanup_failed_start(self, project_id: str):
        """Clean up resources after a failed start."""
        try:
            # Release ports
            await self._release_ports(project_id)
            
            # Remove from running projects if present
            if project_id in self.running_projects:
                del self.running_projects[project_id]
                
        except Exception as e:
            logger.error(f"Error during cleanup for {project_id}: {e}")