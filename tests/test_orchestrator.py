"""
Comprehensive test suite for Optimus Orchestrator Services.

Tests all orchestrator components including ProjectLauncher, EnvironmentManager,
ResourceAllocator, DeploymentAssistant, and BackupCoordinator.
"""

import pytest
import asyncio
import tempfile
import shutil
import json
import os
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# Import orchestrator components
from src.orchestrator.project_launcher import (
    ProjectLauncher, ProjectStatus, ProjectType, ProcessInfo, RunningProject, StartupConfig
)
from src.orchestrator.environment_manager import (
    EnvironmentManager, EnvironmentType, EnvironmentVariable, Environment
)
from src.orchestrator.resource_allocator import (
    ResourceAllocator, ResourceType, ResourcePriority, ResourceLimits, 
    ResourceMetrics, ResourceRequirements, Allocation
)
from src.orchestrator.deployment_assistant import (
    DeploymentAssistant, DeploymentStatus, DeploymentTarget, DeploymentConfig, 
    DeploymentResult, Pipeline, HealthStatus
)
from src.orchestrator.backup_coordinator import (
    BackupCoordinator, BackupType, BackupStatus, CompressionType, 
    BackupMetadata, Backup, BackupConfig, ScheduledJob
)


class TestProjectLauncher:
    """Test suite for ProjectLauncher component."""
    
    @pytest.fixture
    async def launcher(self):
        """Create a ProjectLauncher instance for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield ProjectLauncher(base_projects_path=temp_dir)
    
    @pytest.fixture
    def mock_project(self):
        """Create a mock project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()
            
            # Create package.json for Node.js project
            package_json = {
                "name": "test_project",
                "scripts": {
                    "start": "node index.js",
                    "dev": "nodemon index.js"
                }
            }
            with open(project_path / "package.json", "w") as f:
                json.dump(package_json, f)
            
            # Create index.js
            with open(project_path / "index.js", "w") as f:
                f.write("console.log('Hello World');\n")
            
            yield str(project_path)
    
    @pytest.mark.asyncio
    async def test_detect_project_type(self, launcher, mock_project):
        """Test project type detection."""
        project_path = Path(mock_project)
        project_type = await launcher._detect_project_type(project_path)
        assert project_type == ProjectType.NODE
    
    @pytest.mark.asyncio
    async def test_find_free_port(self, launcher):
        """Test port allocation."""
        port = await launcher._find_free_port()
        assert 3000 <= port <= 9999
        
        # Test port allocation tracking
        allocated_ports = await launcher._allocate_ports("test_project", [port])
        assert port in allocated_ports
        assert launcher.allocated_ports[port] == "test_project"
    
    @pytest.mark.asyncio
    async def test_startup_config(self, launcher, mock_project):
        """Test startup configuration creation."""
        project_path = Path(mock_project)
        
        # Create optimus.yml config
        config_data = {
            "environments": {
                "development": {
                    "command": "npm run dev",
                    "ports": [3000],
                    "env_vars": {"NODE_ENV": "development"},
                    "health_check_url": "http://localhost:3000/health"
                }
            }
        }
        
        import yaml
        with open(project_path / "optimus.yml", "w") as f:
            yaml.dump(config_data, f)
        
        # Update launcher to use mock project path
        launcher.base_projects_path = project_path.parent
        
        config = await launcher._get_startup_config("test_project", "development")
        assert config.command == "npm run dev"
        assert config.ports == [3000]
        assert config.env_vars["NODE_ENV"] == "development"
    
    @pytest.mark.asyncio
    @patch('subprocess.Popen')
    @patch('psutil.Process')
    async def test_start_process(self, mock_psutil_process, mock_popen, launcher, mock_project):
        """Test process startup."""
        # Mock subprocess
        mock_process = Mock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process
        
        # Mock psutil process
        mock_psutil_instance = Mock()
        mock_psutil_instance.memory_info.return_value.rss = 1024 * 1024 * 10  # 10MB
        mock_psutil_instance.memory_percent.return_value = 5.0
        mock_psutil_process.return_value = mock_psutil_instance
        
        project_path = Path(mock_project)
        command = ["node", "index.js"]
        env_vars = {"NODE_ENV": "development"}
        log_file = "/tmp/test.log"
        config = StartupConfig()
        
        # Create log file
        Path(log_file).touch()
        
        process_info = await launcher._start_process(
            "test_project", command, project_path, env_vars, log_file, config
        )
        
        assert process_info.pid == 12345
        assert process_info.name == "node"
        assert process_info.status == "starting"
    
    @pytest.mark.asyncio
    @patch('psutil.process_iter')
    async def test_find_project_processes(self, mock_process_iter, launcher):
        """Test finding processes related to a project."""
        # Mock processes
        mock_proc1 = Mock()
        mock_proc1.info = {
            'pid': 123,
            'name': 'node',
            'cmdline': ['node', '/projects/test_project/index.js'],
            'cwd': '/projects/test_project'
        }
        
        mock_proc2 = Mock()
        mock_proc2.info = {
            'pid': 124,
            'name': 'python',
            'cmdline': ['python', '/projects/other/app.py'],
            'cwd': '/projects/other'
        }
        
        mock_process_iter.return_value = [mock_proc1, mock_proc2]
        
        processes = await launcher._find_project_processes("test_project")
        assert len(processes) == 1
        assert processes[0].info['pid'] == 123
    
    @pytest.mark.asyncio
    async def test_build_startup_command(self, launcher, mock_project):
        """Test startup command generation."""
        project_path = Path(mock_project)
        project_type = ProjectType.NODE
        config = StartupConfig()
        allocated_ports = [3000]
        
        command = await launcher._build_startup_command(
            project_path, project_type, config, allocated_ports
        )
        
        assert command == ["npm", "start"]


class TestEnvironmentManager:
    """Test suite for EnvironmentManager component."""
    
    @pytest.fixture
    async def env_manager(self):
        """Create an EnvironmentManager instance for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield EnvironmentManager(base_projects_path=temp_dir)
    
    @pytest.fixture
    def mock_project_env(self):
        """Create a mock project with environment files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()
            
            # Create .env files
            with open(project_path / ".env", "w") as f:
                f.write("APP_NAME=test_app\n")
                f.write("DEBUG=true\n")
            
            with open(project_path / ".env.production", "w") as f:
                f.write("APP_NAME=test_app\n")
                f.write("DEBUG=false\n")
                f.write("DATABASE_URL=postgresql://prod_db\n")
            
            yield str(project_path)
    
    @pytest.mark.asyncio
    async def test_load_env_file(self, env_manager, mock_project_env):
        """Test loading environment variables from file."""
        env_manager.base_projects_path = Path(mock_project_env).parent
        
        variables = await env_manager.load_env_file("test_project", ".env")
        assert variables["APP_NAME"] == "test_app"
        assert variables["DEBUG"] == "true"
    
    @pytest.mark.asyncio
    async def test_is_secret_variable(self, env_manager):
        """Test secret variable detection."""
        assert await env_manager._is_secret_variable("API_KEY", "secret123")
        assert await env_manager._is_secret_variable("PASSWORD", "mypass")
        assert await env_manager._is_secret_variable("JWT_SECRET", "token123")
        assert not await env_manager._is_secret_variable("APP_NAME", "myapp")
        assert not await env_manager._is_secret_variable("DEBUG", "true")
    
    @pytest.mark.asyncio
    async def test_set_variables(self, env_manager, mock_project_env):
        """Test setting environment variables."""
        env_manager.base_projects_path = Path(mock_project_env).parent
        
        variables = {
            "NEW_VAR": "value123",
            "API_SECRET": "secret456"
        }
        
        success = await env_manager.set_variables("test_project", variables, "development")
        assert success
        
        # Verify variables were stored
        environment = await env_manager.get_environment("test_project", "development")
        assert environment is not None
        assert "NEW_VAR" in environment.variables
        assert "API_SECRET" in environment.variables
        assert environment.variables["API_SECRET"].is_secret
    
    @pytest.mark.asyncio
    async def test_create_env_template(self, env_manager, mock_project_env):
        """Test environment template creation."""
        env_manager.base_projects_path = Path(mock_project_env).parent
        
        template_path = await env_manager.create_env_template("test_project", "web_application")
        assert Path(template_path).exists()
        
        # Verify template content
        with open(template_path) as f:
            content = f.read()
            assert "PORT=" in content
            assert "DATABASE_URL=" in content
            assert "JWT_SECRET=" in content


class TestResourceAllocator:
    """Test suite for ResourceAllocator component."""
    
    @pytest.fixture
    async def resource_allocator(self):
        """Create a ResourceAllocator instance for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield ResourceAllocator(base_projects_path=temp_dir)
    
    @pytest.mark.asyncio
    @patch('psutil.cpu_count')
    @patch('psutil.virtual_memory')
    async def test_system_info_initialization(self, mock_memory, mock_cpu, resource_allocator):
        """Test system information gathering."""
        mock_cpu.return_value = 8
        mock_memory.return_value.total = 16 * 1024 * 1024 * 1024  # 16GB
        
        allocator = ResourceAllocator()
        assert allocator.total_cpu_cores == 8
        assert allocator.total_memory_mb == 16 * 1024
    
    @pytest.mark.asyncio
    async def test_calculate_resource_limits(self, resource_allocator):
        """Test resource limit calculation."""
        requirements = ResourceRequirements(
            min_cpu_percent=10.0,
            max_cpu_percent=50.0,
            min_memory_mb=256,
            max_memory_mb=1024,
            priority=ResourcePriority.NORMAL
        )
        
        with patch('psutil.cpu_percent', return_value=30.0), \
             patch('psutil.virtual_memory') as mock_memory:
            
            mock_memory.return_value.percent = 50.0
            
            limits = await resource_allocator._calculate_resource_limits("test_project", requirements)
            assert limits.cpu_percent >= requirements.min_cpu_percent
            assert limits.memory_mb >= requirements.min_memory_mb
    
    @pytest.mark.asyncio
    @patch('psutil.process_iter')
    async def test_find_project_processes(self, mock_process_iter, resource_allocator):
        """Test finding project processes."""
        # Mock process
        mock_proc = Mock()
        mock_proc.info = {
            'pid': 123,
            'name': 'node',
            'cmdline': ['node', '/projects/test_project/app.js'],
            'cwd': '/projects/test_project'
        }
        mock_process_iter.return_value = [mock_proc]
        
        processes = await resource_allocator._find_project_processes("test_project")
        assert len(processes) == 1
    
    @pytest.mark.asyncio
    async def test_calculate_trend(self, resource_allocator):
        """Test trend calculation."""
        # Increasing trend
        values = [10, 15, 20, 25, 30]
        trend = resource_allocator._calculate_trend(values)
        assert trend > 0
        
        # Decreasing trend
        values = [30, 25, 20, 15, 10]
        trend = resource_allocator._calculate_trend(values)
        assert trend < 0
        
        # Stable trend
        values = [20, 20, 20, 20, 20]
        trend = resource_allocator._calculate_trend(values)
        assert abs(trend) < 0.1
    
    @pytest.mark.asyncio
    async def test_resource_metrics(self, resource_allocator):
        """Test resource metrics creation."""
        with patch.object(resource_allocator, '_find_project_processes') as mock_find:
            # Mock process
            mock_process = Mock()
            mock_process.cpu_percent.return_value = 25.0
            mock_process.memory_info.return_value.rss = 100 * 1024 * 1024  # 100MB
            mock_process.memory_percent.return_value = 10.0
            mock_process.io_counters.return_value.read_bytes = 1024 * 1024
            mock_process.io_counters.return_value.write_bytes = 512 * 1024
            mock_process.num_fds.return_value = 50
            
            mock_find.return_value = [mock_process]
            
            metrics = await resource_allocator.monitor_usage("test_project")
            assert metrics.project_id == "test_project"
            assert metrics.cpu_percent == 25.0
            assert metrics.memory_mb == 100.0
            assert metrics.process_count == 1


class TestDeploymentAssistant:
    """Test suite for DeploymentAssistant component."""
    
    @pytest.fixture
    async def deployment_assistant(self):
        """Create a DeploymentAssistant instance for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield DeploymentAssistant(base_projects_path=temp_dir)
    
    @pytest.fixture
    def mock_git_project(self):
        """Create a mock project with git repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()
            
            # Initialize git repo
            os.system(f"cd {project_path} && git init")
            os.system(f"cd {project_path} && git config user.email 'test@example.com'")
            os.system(f"cd {project_path} && git config user.name 'Test User'")
            
            # Create files
            with open(project_path / "package.json", "w") as f:
                json.dump({"name": "test_project", "scripts": {"build": "echo 'building'"}}, f)
            
            with open(project_path / "Dockerfile", "w") as f:
                f.write("FROM node:14\nCOPY . /app\nWORKDIR /app\nRUN npm install\nCMD npm start\n")
            
            # Create initial commit
            os.system(f"cd {project_path} && git add .")
            os.system(f"cd {project_path} && git commit -m 'Initial commit'")
            
            yield str(project_path)
    
    @pytest.mark.asyncio
    async def test_get_current_commit(self, deployment_assistant, mock_git_project):
        """Test getting current git commit."""
        project_path = Path(mock_git_project)
        deployment_assistant.base_projects_path = project_path.parent
        
        commit_hash = await deployment_assistant._get_current_commit(project_path)
        assert commit_hash is not None
        assert len(commit_hash) == 40  # SHA-1 hash length
    
    @pytest.mark.asyncio
    async def test_create_default_config(self, deployment_assistant, mock_git_project):
        """Test default deployment configuration creation."""
        project_path = Path(mock_git_project)
        
        # Test Node.js project
        config = await deployment_assistant._create_default_config(project_path, "local", "development")
        assert config.build_command == "npm run build"
        assert config.test_command == "npm test"
        assert config.health_check_url == "http://localhost:3000/health"
        
        # Test Docker project
        config = await deployment_assistant._create_default_config(project_path, "docker", "production")
        assert config.target.value == "docker"
        assert config.build_command == "docker build -t app ."
    
    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession.get')
    async def test_execute_health_check(self, mock_get, deployment_assistant):
        """Test health check execution."""
        from src.orchestrator.deployment_assistant import HealthCheck
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value="OK")
        
        mock_get.return_value.__aenter__.return_value = mock_response
        
        health_check = HealthCheck(url="http://localhost:3000/health")
        result = await deployment_assistant._execute_health_check(health_check)
        
        assert result.status.value == "healthy"
        assert result.response_text == "OK"
    
    @pytest.mark.asyncio
    async def test_deployment_config_loading(self, deployment_assistant, mock_git_project):
        """Test deployment configuration loading."""
        project_path = Path(mock_git_project)
        deployment_assistant.base_projects_path = project_path.parent
        
        # Create deployment config file
        config_data = {
            "targets": {
                "docker": {
                    "build_command": "docker build -t myapp .",
                    "deploy_command": "docker run -d -p 80:3000 myapp",
                    "environments": {
                        "production": {
                            "health_check_url": "http://localhost/health",
                            "env_vars": {"NODE_ENV": "production"}
                        }
                    }
                }
            }
        }
        
        import yaml
        with open(project_path / "optimus-deploy.yml", "w") as f:
            yaml.dump(config_data, f)
        
        config = await deployment_assistant._get_deployment_config("test_project", "docker", "production")
        assert config.build_command == "docker build -t myapp ."
        assert config.health_check_url == "http://localhost/health"
        assert config.env_vars["NODE_ENV"] == "production"


class TestBackupCoordinator:
    """Test suite for BackupCoordinator component."""
    
    @pytest.fixture
    async def backup_coordinator(self):
        """Create a BackupCoordinator instance for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            projects_dir = Path(temp_dir) / "projects"
            projects_dir.mkdir()
            backup_dir = Path(temp_dir) / "backups"
            backup_dir.mkdir()
            
            yield BackupCoordinator(
                base_projects_path=str(projects_dir),
                backup_storage_path=str(backup_dir)
            )
    
    @pytest.fixture
    def mock_backup_project(self):
        """Create a mock project for backup testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()
            
            # Create test files
            (project_path / "src").mkdir()
            with open(project_path / "src" / "app.py", "w") as f:
                f.write("print('Hello World')\n")
            
            with open(project_path / "README.md", "w") as f:
                f.write("# Test Project\n")
            
            with open(project_path / "package.json", "w") as f:
                json.dump({"name": "test_project"}, f)
            
            # Create files to exclude
            (project_path / "node_modules").mkdir()
            with open(project_path / "node_modules" / "module.js", "w") as f:
                f.write("// Module file\n")
            
            yield str(project_path)
    
    @pytest.mark.asyncio
    async def test_collect_files(self, backup_coordinator, mock_backup_project):
        """Test file collection for backup."""
        project_path = Path(mock_backup_project)
        backup_coordinator.base_projects_path = project_path.parent
        
        config = BackupConfig(
            project_id="test_project",
            include_patterns=["**/*"],
            exclude_patterns=["**/node_modules/**", "**/*.tmp"]
        )
        
        files = await backup_coordinator._collect_files(project_path, config, None)
        
        # Should include source files but exclude node_modules
        file_names = [Path(f).name for f in files]
        assert "app.py" in file_names
        assert "README.md" in file_names
        assert "package.json" in file_names
        assert "module.js" not in file_names
    
    @pytest.mark.asyncio
    async def test_calculate_file_checksum(self, backup_coordinator):
        """Test file checksum calculation."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_file = f.name
        
        try:
            checksum = await backup_coordinator._calculate_file_checksum(temp_file)
            assert len(checksum) == 64  # SHA-256 hex length
            assert checksum == hashlib.sha256(b"test content").hexdigest()
        finally:
            os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_backup_config_loading(self, backup_coordinator, mock_backup_project):
        """Test backup configuration loading."""
        project_path = Path(mock_backup_project)
        backup_coordinator.base_projects_path = project_path.parent
        
        # Create backup config
        config_dir = project_path / ".optimus"
        config_dir.mkdir()
        
        config_data = {
            "enabled": True,
            "backup_type": "incremental",
            "compression": "gzip",
            "retention_days": 60,
            "exclude_patterns": ["**/*.log", "**/tmp/**"]
        }
        
        with open(config_dir / "backup-config.json", "w") as f:
            json.dump(config_data, f)
        
        config = await backup_coordinator._get_backup_config("test_project")
        assert config.backup_type == BackupType.INCREMENTAL
        assert config.compression == CompressionType.GZIP
        assert config.retention_days == 60
        assert "**/*.log" in config.exclude_patterns
    
    @pytest.mark.asyncio
    async def test_find_changed_files(self, backup_coordinator):
        """Test incremental backup file change detection."""
        # Create mock parent backup with manifest
        parent_backup = Backup(
            metadata=BackupMetadata(
                backup_id="parent_backup",
                project_id="test_project",
                backup_type=BackupType.FULL,
                status=BackupStatus.SUCCESS,
                created_at=datetime.now() - timedelta(days=1)
            )
        )
        
        # Create mock manifest
        manifest_data = {
            "backup_id": "parent_backup",
            "files": [
                {"path": "app.py", "size": 100, "mtime": 1000000},
                {"path": "old_file.txt", "size": 50, "mtime": 2000000}
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(manifest_data, f)
            parent_backup.manifest_path = f.name
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                project_path = Path(temp_dir)
                
                # Create files with different modification times
                with open(project_path / "app.py", "w") as f:
                    f.write("modified content")
                os.utime(project_path / "app.py", (3000000, 3000000))  # Newer
                
                with open(project_path / "new_file.py", "w") as f:
                    f.write("new content")
                
                files = ["app.py", "new_file.py", "old_file.txt"]
                
                changed_files = await backup_coordinator._find_changed_files(
                    files, project_path, parent_backup
                )
                
                assert "app.py" in changed_files  # Modified
                assert "new_file.py" in changed_files  # New file
                assert "old_file.txt" not in changed_files  # Unchanged
        finally:
            os.unlink(parent_backup.manifest_path)
    
    @pytest.mark.asyncio
    async def test_scheduled_job_creation(self, backup_coordinator):
        """Test scheduled backup job creation."""
        from croniter import croniter
        
        config = BackupConfig(project_id="test_project")
        schedule = "0 2 * * *"  # Daily at 2 AM
        
        job = await backup_coordinator.schedule_backup("test_project", schedule, config)
        
        assert job.project_id == "test_project"
        assert job.schedule == schedule
        assert job.next_run is not None
        
        # Verify cron expression is valid
        cron = croniter(schedule)
        next_run = cron.get_next(datetime)
        assert next_run is not None


class TestIntegration:
    """Integration tests for orchestrator components."""
    
    @pytest.fixture
    async def full_orchestrator(self):
        """Create all orchestrator components for integration testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            projects_dir = Path(temp_dir) / "projects"
            projects_dir.mkdir()
            
            # Create mock project
            project_path = projects_dir / "test_integration"
            project_path.mkdir()
            
            with open(project_path / "package.json", "w") as f:
                json.dump({
                    "name": "test_integration",
                    "scripts": {"start": "echo 'started'", "test": "echo 'tested'"}
                }, f)
            
            yield {
                "launcher": ProjectLauncher(base_projects_path=str(projects_dir)),
                "env_manager": EnvironmentManager(base_projects_path=str(projects_dir)),
                "resource_allocator": ResourceAllocator(base_projects_path=str(projects_dir)),
                "deployment_assistant": DeploymentAssistant(base_projects_path=str(projects_dir)),
                "backup_coordinator": BackupCoordinator(
                    base_projects_path=str(projects_dir),
                    backup_storage_path=str(Path(temp_dir) / "backups")
                ),
                "project_path": str(project_path)
            }
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self, full_orchestrator):
        """Test complete orchestration workflow."""
        components = full_orchestrator
        project_id = "test_integration"
        
        # 1. Set up environment
        env_manager = components["env_manager"]
        success = await env_manager.set_variables(
            project_id, 
            {"NODE_ENV": "test", "PORT": "3000"}, 
            "development"
        )
        assert success
        
        # 2. Allocate resources
        resource_allocator = components["resource_allocator"]
        requirements = ResourceRequirements(
            min_cpu_percent=5.0,
            max_cpu_percent=25.0,
            min_memory_mb=128,
            max_memory_mb=512
        )
        allocation = await resource_allocator.allocate_resources(project_id, requirements)
        assert allocation.project_id == project_id
        assert allocation.limits.cpu_percent >= 5.0
        
        # 3. Create backup
        backup_coordinator = components["backup_coordinator"]
        backup = await backup_coordinator.backup_project(project_id, incremental=False)
        assert backup.metadata.project_id == project_id
        assert backup.metadata.backup_type == BackupType.FULL
        
        # 4. Verify components can find project
        launcher = components["launcher"]
        project_path = await launcher._find_project_path(project_id)
        assert project_path.exists()
        assert project_path.name == project_id
    
    @pytest.mark.asyncio 
    async def test_resource_and_environment_integration(self, full_orchestrator):
        """Test resource allocation with environment switching."""
        components = full_orchestrator
        project_id = "test_integration"
        
        # Set up different environments with different resource needs
        env_manager = components["env_manager"]
        
        # Development environment - lower resources
        await env_manager.set_variables(
            project_id,
            {"NODE_ENV": "development", "MAX_MEMORY": "256MB"},
            "development"
        )
        
        # Production environment - higher resources  
        await env_manager.set_variables(
            project_id,
            {"NODE_ENV": "production", "MAX_MEMORY": "1GB"},
            "production"
        )
        
        # Allocate resources for development
        resource_allocator = components["resource_allocator"]
        dev_requirements = ResourceRequirements(
            max_cpu_percent=20.0,
            max_memory_mb=256,
            priority=ResourcePriority.LOW
        )
        
        dev_allocation = await resource_allocator.allocate_resources(project_id, dev_requirements)
        assert dev_allocation.limits.memory_mb <= 256
        
        # Switch to production and reallocate
        await env_manager.switch_environment(project_id, "production")
        
        prod_requirements = ResourceRequirements(
            max_cpu_percent=80.0,
            max_memory_mb=1024,
            priority=ResourcePriority.HIGH
        )
        
        prod_allocation = await resource_allocator.allocate_resources(project_id, prod_requirements)
        assert prod_allocation.limits.memory_mb > dev_allocation.limits.memory_mb


# Performance and stress tests
class TestPerformance:
    """Performance tests for orchestrator components."""
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent orchestrator operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            projects_dir = Path(temp_dir) / "projects"
            projects_dir.mkdir()
            
            # Create multiple test projects
            project_ids = []
            for i in range(5):
                project_id = f"test_project_{i}"
                project_path = projects_dir / project_id
                project_path.mkdir()
                
                with open(project_path / "package.json", "w") as f:
                    json.dump({"name": project_id}, f)
                
                project_ids.append(project_id)
            
            # Test concurrent resource allocation
            resource_allocator = ResourceAllocator(base_projects_path=str(projects_dir))
            
            async def allocate_for_project(pid):
                requirements = ResourceRequirements(
                    max_cpu_percent=20.0,
                    max_memory_mb=256
                )
                return await resource_allocator.allocate_resources(pid, requirements)
            
            # Run concurrent allocations
            tasks = [allocate_for_project(pid) for pid in project_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all allocations succeeded
            successful_allocations = [r for r in results if not isinstance(r, Exception)]
            assert len(successful_allocations) == len(project_ids)
    
    @pytest.mark.asyncio
    async def test_large_file_backup(self):
        """Test backup performance with large files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            projects_dir = Path(temp_dir) / "projects"
            projects_dir.mkdir()
            backup_dir = Path(temp_dir) / "backups"
            backup_dir.mkdir()
            
            # Create project with large files
            project_path = projects_dir / "large_project"
            project_path.mkdir()
            
            # Create multiple files of different sizes
            sizes = [1024, 10*1024, 100*1024]  # 1KB, 10KB, 100KB
            for i, size in enumerate(sizes):
                with open(project_path / f"file_{i}.txt", "w") as f:
                    f.write("x" * size)
            
            backup_coordinator = BackupCoordinator(
                base_projects_path=str(projects_dir),
                backup_storage_path=str(backup_dir)
            )
            
            start_time = datetime.now()
            backup = await backup_coordinator.backup_project("large_project", incremental=False)
            duration = datetime.now() - start_time
            
            assert backup.metadata.status == BackupStatus.SUCCESS
            assert backup.metadata.file_count == len(sizes)
            assert duration.total_seconds() < 30  # Should complete within 30 seconds


# Mock helper functions
async def mock_process_start():
    """Mock process start for testing."""
    await asyncio.sleep(0.1)  # Simulate startup time
    return ProcessInfo(
        pid=12345,
        name="test_process",
        status="running",
        cpu_percent=10.0,
        memory_rss=100*1024*1024,
        memory_percent=5.0,
        ports=[3000],
        started_at=datetime.now(),
        last_seen=datetime.now()
    )


# Test configuration
@pytest.fixture(autouse=True)
def configure_logging():
    """Configure logging for tests."""
    import logging
    logging.basicConfig(level=logging.DEBUG)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])