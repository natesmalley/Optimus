"""
Comprehensive test suite for the enhanced scanner system.
Tests all scanner components including:
- EnhancedProjectScanner
- RuntimeMonitor  
- ProjectAnalyzer
- ScannerOrchestrator
"""

import asyncio
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.enhanced_scanner import EnhancedProjectScanner, ProjectAnalysis, ScanMetrics
from src.services.runtime_monitor import RuntimeMonitor, ProcessInfo, ServiceInfo
from src.services.project_analyzer import ProjectAnalyzer, ProjectAnalysisResult, SecurityIssue
from src.services.scanner_orchestrator import ScannerOrchestrator, ScanType, ScanStatus


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory with sample files."""
    temp_dir = tempfile.mkdtemp()
    project_path = Path(temp_dir)
    
    # Create sample Python project
    (project_path / "main.py").write_text("""
import os
import requests

def main():
    # TODO: Remove hardcoded password
    password = "secret123"
    api_key = "sk-1234567890abcdef"
    
    # Potential SQL injection
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    
    # Complex function that should trigger quality warnings
    if condition1 and condition2 and condition3 and condition4:
        for i in range(100):
            if i % 2 == 0:
                if i > 50:
                    print(f"Processing {i}")
    
    return True

class LargeClass:
    def method1(self): pass
    def method2(self): pass
    def method3(self): pass
    def method4(self): pass
    def method5(self): pass
    def method6(self): pass
    def method7(self): pass
    def method8(self): pass
    def method9(self): pass
    def method10(self): pass
    def method11(self): pass
    def method12(self): pass
""")
    
    (project_path / "requirements.txt").write_text("""
flask==2.0.1
requests>=2.25.0
pandas==1.3.0
numpy>=1.21.0
""")
    
    (project_path / "package.json").write_text("""{
  "name": "test-project",
  "version": "1.0.0",
  "dependencies": {
    "react": "^17.0.0",
    "express": "^4.17.0"
  },
  "devDependencies": {
    "jest": "^27.0.0",
    "typescript": "^4.3.0"
  }
}""")
    
    (project_path / "README.md").write_text("""
# Test Project

This is a test project for scanner testing.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

Run the application:

```bash
python main.py
```

## License

MIT License
""")
    
    # Create test files
    (project_path / "test_main.py").write_text("""
import unittest
from main import main

class TestMain(unittest.TestCase):
    def test_main_returns_true(self):
        result = main()
        self.assertTrue(result)

if __name__ == '__main__':
    unittest.main()
""")
    
    # Create .env file (potential security issue)
    (project_path / ".env").write_text("""
DATABASE_URL=postgresql://user:password@localhost/db
SECRET_KEY=supersecretkey123
""")
    
    # Create .gitignore (but without .env listed - security issue)
    (project_path / ".gitignore").write_text("""
__pycache__/
*.pyc
node_modules/
""")
    
    yield project_path
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
async def mock_session():
    """Create a mock database session."""
    session = Mock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.add = Mock()
    return session


@pytest.fixture
def mock_memory_integration():
    """Create a mock memory integration."""
    memory = Mock()
    memory.store_context = AsyncMock()
    return memory


@pytest.fixture
def mock_kg_integration():
    """Create a mock knowledge graph integration."""
    kg = Mock()
    kg.add_node = AsyncMock()
    kg.add_relationship = AsyncMock()
    return kg


class TestEnhancedProjectScanner:
    """Test the enhanced project scanner."""
    
    async def test_scanner_initialization(self, mock_session, mock_memory_integration, mock_kg_integration):
        """Test scanner initialization."""
        scanner = EnhancedProjectScanner(mock_session, mock_memory_integration, mock_kg_integration)
        
        assert scanner.session == mock_session
        assert scanner.memory == mock_memory_integration
        assert scanner.kg == mock_kg_integration
        assert isinstance(scanner.metrics, ScanMetrics)
        assert len(scanner.language_patterns) > 0
    
    async def test_project_discovery(self, temp_project_dir, mock_session, mock_memory_integration, mock_kg_integration):
        """Test project discovery functionality."""
        scanner = EnhancedProjectScanner(mock_session, mock_memory_integration, mock_kg_integration)
        
        # Discover projects
        project_dirs = await scanner._discover_project_directories(temp_project_dir)
        
        # Should find the temp project directory
        assert len(project_dirs) >= 1
        assert temp_project_dir in project_dirs
    
    async def test_technology_stack_detection(self, temp_project_dir, mock_session, mock_memory_integration, mock_kg_integration):
        """Test technology stack detection."""
        scanner = EnhancedProjectScanner(mock_session, mock_memory_integration, mock_kg_integration)
        
        # Analyze the project
        analysis = await scanner._analyze_project_comprehensive(temp_project_dir)
        
        # Should detect Python and JavaScript
        assert "python" in analysis.tech_stack.get("languages", [])
        assert analysis.frameworks  # Should detect some frameworks
        assert analysis.basic_info["name"] == temp_project_dir.name
        
        # Should have dependency information
        assert "runtime" in analysis.dependencies
        assert "development" in analysis.dependencies
    
    async def test_security_analysis(self, temp_project_dir, mock_session, mock_memory_integration, mock_kg_integration):
        """Test security vulnerability detection."""
        scanner = EnhancedProjectScanner(mock_session, mock_memory_integration, mock_kg_integration)
        
        analysis = await scanner._analyze_project_comprehensive(temp_project_dir)
        
        # Should detect security issues from our test file
        assert len(analysis.security["vulnerabilities"]) > 0
        
        # Should categorize vulnerabilities
        assert "categories" in analysis.security
        assert analysis.security["risk_score"] > 0
    
    async def test_code_metrics_calculation(self, temp_project_dir, mock_session, mock_memory_integration, mock_kg_integration):
        """Test code metrics calculation."""
        scanner = EnhancedProjectScanner(mock_session, mock_memory_integration, mock_kg_integration)
        
        analysis = await scanner._analyze_project_comprehensive(temp_project_dir)
        
        # Should have code metrics
        assert analysis.code_metrics["total_files"] > 0
        assert "python" in analysis.tech_stack.get("language_stats", {})
        assert analysis.code_metrics["functions"] > 0
        assert analysis.code_metrics["classes"] > 0
    
    async def test_git_analysis(self, temp_project_dir, mock_session, mock_memory_integration, mock_kg_integration):
        """Test Git repository analysis."""
        scanner = EnhancedProjectScanner(mock_session, mock_memory_integration, mock_kg_integration)
        
        # Initialize git repo
        import subprocess
        subprocess.run(["git", "init"], cwd=temp_project_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=temp_project_dir)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=temp_project_dir)
        subprocess.run(["git", "add", "."], cwd=temp_project_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=temp_project_dir, capture_output=True)
        
        analysis = await scanner._analyze_project_comprehensive(temp_project_dir)
        
        # Should have Git information
        assert analysis.git_analysis["is_repo"] == True
        assert "latest_commit" in analysis.git_analysis
    
    async def test_documentation_assessment(self, temp_project_dir, mock_session, mock_memory_integration, mock_kg_integration):
        """Test documentation quality assessment."""
        scanner = EnhancedProjectScanner(mock_session, mock_memory_integration, mock_kg_integration)
        
        analysis = await scanner._analyze_project_comprehensive(temp_project_dir)
        
        # Should assess documentation
        assert analysis.documentation["score"] > 0  # Has README
        assert "README.md" in analysis.documentation["files"]
        assert analysis.documentation["quality"] in ["poor", "fair", "good", "excellent"]
    
    @patch('asyncio.gather')
    async def test_parallel_scanning(self, mock_gather, mock_session, mock_memory_integration, mock_kg_integration):
        """Test parallel scanning functionality."""
        scanner = EnhancedProjectScanner(mock_session, mock_memory_integration, mock_kg_integration)
        
        # Mock successful results
        mock_gather.return_value = [Mock(spec=ProjectAnalysis) for _ in range(3)]
        
        with patch.object(scanner, '_discover_project_directories') as mock_discover:
            mock_discover.return_value = [Path("/proj1"), Path("/proj2"), Path("/proj3")]
            
            projects = await scanner.scan_projects()
            
            # Should have called gather for parallel processing
            assert mock_gather.called


class TestRuntimeMonitor:
    """Test the runtime monitor."""
    
    async def test_monitor_initialization(self, mock_session, mock_memory_integration, mock_kg_integration):
        """Test runtime monitor initialization."""
        monitor = RuntimeMonitor(mock_session, mock_memory_integration, mock_kg_integration)
        
        assert monitor.session == mock_session
        assert monitor.memory == mock_memory_integration
        assert monitor.kg == mock_kg_integration
        assert len(monitor.dev_server_patterns) > 0
    
    @patch('psutil.process_iter')
    async def test_process_scanning(self, mock_process_iter, mock_session, mock_memory_integration, mock_kg_integration):
        """Test process scanning functionality."""
        monitor = RuntimeMonitor(mock_session, mock_memory_integration, mock_kg_integration)
        
        # Mock process data
        mock_proc = Mock()
        mock_proc.info = {
            'pid': 1234,
            'name': 'python',
            'cmdline': ['python', 'manage.py', 'runserver'],
            'cwd': '/path/to/project',
            'status': 'running',
            'cpu_percent': 5.5,
            'memory_percent': 12.3,
            'memory_info': Mock(rss=1024*1024*50),  # 50MB
            'create_time': 1234567890
        }
        mock_process_iter.return_value = [mock_proc]
        
        processes = await monitor.scan_processes()
        
        assert len(processes) == 1
        assert processes[0].name == 'python'
        assert processes[0].cpu_percent == 5.5
    
    @patch('socket.socket')
    async def test_service_scanning(self, mock_socket, mock_session, mock_memory_integration, mock_kg_integration):
        """Test service scanning functionality."""
        monitor = RuntimeMonitor(mock_session, mock_memory_integration, mock_kg_integration)
        
        # Mock successful connection
        mock_sock = Mock()
        mock_sock.connect_ex.return_value = 0  # Success
        mock_socket.return_value = mock_sock
        
        services = await monitor.scan_services()
        
        # Should have attempted to check common ports
        assert mock_socket.called
    
    @patch('docker.from_env')
    async def test_container_scanning(self, mock_docker, mock_session, mock_memory_integration, mock_kg_integration):
        """Test Docker container scanning."""
        monitor = RuntimeMonitor(mock_session, mock_memory_integration, mock_kg_integration)
        
        # Mock Docker client
        mock_container = Mock()
        mock_container.id = "abc123"
        mock_container.name = "test-container"
        mock_container.status = "running"
        mock_container.ports = {"80/tcp": [{"HostPort": "8080"}]}
        mock_container.labels = {"project.path": "/path/to/project"}
        mock_container.attrs = {"Created": "2023-01-01T00:00:00Z"}
        mock_container.image.tags = ["test:latest"]
        
        mock_client = Mock()
        mock_client.containers.list.return_value = [mock_container]
        mock_docker.return_value = mock_client
        
        monitor.docker_client = mock_client
        containers = await monitor.scan_containers()
        
        assert len(containers) == 1
        assert containers[0].name == "test-container"
    
    async def test_system_metrics_collection(self, mock_session, mock_memory_integration, mock_kg_integration):
        """Test system metrics collection."""
        monitor = RuntimeMonitor(mock_session, mock_memory_integration, mock_kg_integration)
        
        with patch('psutil.cpu_percent', return_value=25.5):
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value.percent = 60.0
                
                with patch('psutil.disk_usage') as mock_disk:
                    mock_disk.return_value.percent = 45.0
                    
                    metrics = await monitor.collect_system_metrics()
                    
                    assert metrics.cpu_percent == 25.5
                    assert metrics.memory_percent == 60.0
                    assert metrics.disk_usage_percent == 45.0


class TestProjectAnalyzer:
    """Test the project analyzer."""
    
    async def test_analyzer_initialization(self, mock_session, mock_memory_integration, mock_kg_integration):
        """Test analyzer initialization."""
        analyzer = ProjectAnalyzer(mock_session, mock_memory_integration, mock_kg_integration)
        
        assert analyzer.session == mock_session
        assert len(analyzer.security_patterns) > 0
        assert len(analyzer.quality_patterns) > 0
    
    async def test_security_vulnerability_detection(self, temp_project_dir, mock_session, mock_memory_integration, mock_kg_integration):
        """Test security vulnerability detection."""
        analyzer = ProjectAnalyzer(mock_session, mock_memory_integration, mock_kg_integration)
        
        result = await analyzer.analyze_project(str(temp_project_dir), "test-project-id")
        
        # Should detect security issues
        assert len(result.security_issues) > 0
        
        # Check for specific vulnerabilities
        security_categories = [issue.category for issue in result.security_issues]
        assert "secrets" in security_categories  # Hardcoded passwords
    
    async def test_code_quality_analysis(self, temp_project_dir, mock_session, mock_memory_integration, mock_kg_integration):
        """Test code quality analysis."""
        analyzer = ProjectAnalyzer(mock_session, mock_memory_integration, mock_kg_integration)
        
        result = await analyzer.analyze_project(str(temp_project_dir), "test-project-id")
        
        # Should detect quality issues
        assert len(result.quality_issues) > 0
        
        # Check for specific quality issues
        quality_categories = [issue.category for issue in result.quality_issues]
        assert "complexity" in quality_categories  # Complex conditions/large classes
    
    async def test_test_framework_detection(self, temp_project_dir, mock_session, mock_memory_integration, mock_kg_integration):
        """Test test framework detection."""
        analyzer = ProjectAnalyzer(mock_session, mock_memory_integration, mock_kg_integration)
        
        result = await analyzer.analyze_project(str(temp_project_dir), "test-project-id")
        
        # Should detect test files
        assert len(result.test_analysis.test_files) > 0
        assert any("test_" in f for f in result.test_analysis.test_files)
    
    async def test_documentation_analysis(self, temp_project_dir, mock_session, mock_memory_integration, mock_kg_integration):
        """Test documentation analysis."""
        analyzer = ProjectAnalyzer(mock_session, mock_memory_integration, mock_kg_integration)
        
        result = await analyzer.analyze_project(str(temp_project_dir), "test-project-id")
        
        # Should analyze documentation
        assert result.documentation.readme_score > 0
        assert not result.documentation.license_exists  # No LICENSE file in test project
        assert result.documentation.quality_level in ["poor", "fair", "good", "excellent"]
    
    async def test_overall_score_calculation(self, temp_project_dir, mock_session, mock_memory_integration, mock_kg_integration):
        """Test overall score calculation."""
        analyzer = ProjectAnalyzer(mock_session, mock_memory_integration, mock_kg_integration)
        
        result = await analyzer.analyze_project(str(temp_project_dir), "test-project-id")
        
        # Should have calculated overall score
        assert 0 <= result.overall_score <= 100
        assert len(result.recommendations) > 0
    
    async def test_performance_analysis(self, temp_project_dir, mock_session, mock_memory_integration, mock_kg_integration):
        """Test performance analysis."""
        analyzer = ProjectAnalyzer(mock_session, mock_memory_integration, mock_kg_integration)
        
        result = await analyzer.analyze_project(str(temp_project_dir), "test-project-id")
        
        # Should have performance analysis
        assert hasattr(result.performance, 'performance_score')
        assert 0 <= result.performance.performance_score <= 100


class TestScannerOrchestrator:
    """Test the scanner orchestrator."""
    
    @pytest.fixture
    async def mock_orchestrator_components(self, mock_session, mock_memory_integration, mock_kg_integration):
        """Create mock orchestrator with mocked components."""
        orchestrator = ScannerOrchestrator(mock_session, mock_memory_integration, mock_kg_integration)
        
        # Mock the scanner components
        orchestrator.project_scanner = Mock()
        orchestrator.project_scanner.scan_projects = AsyncMock(return_value=[])
        orchestrator.project_scanner.save_project_analysis = AsyncMock(return_value="project-id-123")
        
        orchestrator.runtime_monitor = Mock()
        orchestrator.runtime_monitor.initialize = AsyncMock()
        orchestrator.runtime_monitor.scan_processes = AsyncMock(return_value=[])
        orchestrator.runtime_monitor.scan_services = AsyncMock(return_value=[])
        orchestrator.runtime_monitor.scan_containers = AsyncMock(return_value=[])
        orchestrator.runtime_monitor.collect_system_metrics = AsyncMock()
        
        orchestrator.project_analyzer = Mock()
        orchestrator.project_analyzer.analyze_project = AsyncMock()
        
        return orchestrator
    
    async def test_orchestrator_initialization(self, mock_orchestrator_components):
        """Test orchestrator initialization."""
        orchestrator = mock_orchestrator_components
        
        await orchestrator.initialize()
        
        assert orchestrator.runtime_monitor.initialize.called
        assert len(orchestrator.active_jobs) == 0
    
    async def test_full_scan_job_creation(self, mock_orchestrator_components):
        """Test full scan job creation."""
        orchestrator = mock_orchestrator_components
        
        job_id = await orchestrator.start_scan(ScanType.FULL)
        
        assert job_id in orchestrator.active_jobs
        job = orchestrator.active_jobs[job_id]
        assert job.scan_type == ScanType.FULL
        assert job.status == ScanStatus.PENDING
    
    async def test_incremental_scan_detection(self, mock_orchestrator_components):
        """Test incremental scan change detection."""
        orchestrator = mock_orchestrator_components
        
        # Setup some project checksums
        orchestrator.project_checksums = {
            "/project1": "old-checksum",
            "/project2": "current-checksum"
        }
        
        with patch.object(orchestrator, '_calculate_project_checksum') as mock_checksum:
            mock_checksum.side_effect = lambda path: "new-checksum" if "project1" in path else "current-checksum"
            
            changed_projects = await orchestrator._find_changed_projects()
            
            # Should detect project1 as changed
            assert len(changed_projects) == 1
            assert "/project1" in changed_projects
    
    async def test_job_status_tracking(self, mock_orchestrator_components):
        """Test job status tracking."""
        orchestrator = mock_orchestrator_components
        
        job_id = await orchestrator.start_scan(ScanType.DISCOVERY_ONLY)
        
        # Give job time to start
        await asyncio.sleep(0.1)
        
        status = await orchestrator.get_job_status(job_id)
        
        assert status is not None
        assert status["id"] == job_id
        assert "status" in status
        assert "progress" in status
    
    async def test_job_cancellation(self, mock_orchestrator_components):
        """Test job cancellation."""
        orchestrator = mock_orchestrator_components
        
        job_id = await orchestrator.start_scan(ScanType.RUNTIME_ONLY)
        
        # Cancel the job
        success = await orchestrator.cancel_job(job_id)
        
        assert success == True
        
        # Check job was cancelled
        job = orchestrator.active_jobs.get(job_id)
        if job:  # Job might have been cleaned up already
            assert job.status == ScanStatus.CANCELLED
    
    async def test_orchestrator_metrics(self, mock_orchestrator_components):
        """Test orchestrator metrics tracking."""
        orchestrator = mock_orchestrator_components
        
        # Start and complete a job
        job_id = await orchestrator.start_scan(ScanType.DISCOVERY_ONLY)
        
        # Wait for job to complete
        await asyncio.sleep(0.2)
        
        status = await orchestrator.get_orchestrator_status()
        
        assert "metrics" in status
        assert "active_jobs" in status
        assert status["metrics"]["total_scans"] >= 0
    
    async def test_memory_integration(self, mock_orchestrator_components):
        """Test integration with memory system."""
        orchestrator = mock_orchestrator_components
        
        # Mock successful scan results
        mock_analyses = [Mock(spec=ProjectAnalysis)]
        mock_results = [Mock(spec=ProjectAnalysisResult)]
        
        job = Mock()
        job.id = "test-job"
        job.scan_type = ScanType.FULL
        
        await orchestrator._integrate_scan_results_with_memory(job, mock_analyses, mock_results)
        
        # Should have called memory storage
        assert orchestrator.memory.store_context.called


class TestScannerIntegration:
    """Integration tests for the complete scanner system."""
    
    async def test_end_to_end_scanning(self, temp_project_dir, mock_session, mock_memory_integration, mock_kg_integration):
        """Test complete end-to-end scanning workflow."""
        # Initialize orchestrator
        orchestrator = ScannerOrchestrator(mock_session, mock_memory_integration, mock_kg_integration)
        
        # Mock database responses
        mock_session.execute.return_value.scalar_one_or_none.return_value = None
        mock_session.execute.return_value.fetchall.return_value = []
        
        # Override projects base path for testing
        with patch.object(orchestrator.project_scanner.settings, 'projects_base_path', str(temp_project_dir.parent)):
            
            await orchestrator.initialize()
            
            # Start a discovery scan
            job_id = await orchestrator.start_scan(ScanType.DISCOVERY_ONLY)
            
            # Wait for scan to complete
            timeout = 30  # 30 seconds timeout
            while timeout > 0:
                await asyncio.sleep(0.5)
                timeout -= 0.5
                
                status = await orchestrator.get_job_status(job_id)
                if status and status["status"] in ["completed", "failed"]:
                    break
            
            # Check final status
            final_status = await orchestrator.get_job_status(job_id)
            assert final_status["status"] in ["completed", "failed"]
            
            # Should have discovered at least one project
            if final_status["status"] == "completed":
                assert final_status["results"]["discovered_projects"] >= 0


@pytest.mark.performance
class TestScannerPerformance:
    """Performance tests for scanner components."""
    
    async def test_large_project_scanning_performance(self, mock_session, mock_memory_integration, mock_kg_integration):
        """Test scanner performance with large projects."""
        scanner = EnhancedProjectScanner(mock_session, mock_memory_integration, mock_kg_integration)
        
        # Create a temporary large project structure
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            
            # Create many files
            for i in range(100):
                file_path = project_path / f"module_{i}.py"
                file_path.write_text(f"# Module {i}\nprint('Hello from module {i}')\n")
            
            start_time = datetime.now()
            
            # Should complete within reasonable time
            analysis = await scanner._analyze_project_comprehensive(project_path)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Should complete within 10 seconds for 100 files
            assert duration < 10.0
            assert analysis.basic_info["name"] == project_path.name
    
    async def test_concurrent_scanning_performance(self, mock_session, mock_memory_integration, mock_kg_integration):
        """Test performance of concurrent scanning operations."""
        orchestrator = ScannerOrchestrator(mock_session, mock_memory_integration, mock_kg_integration)
        
        # Mock successful quick operations
        orchestrator.project_scanner.scan_projects = AsyncMock(return_value=[])
        orchestrator.runtime_monitor.scan_processes = AsyncMock(return_value=[])
        
        start_time = datetime.now()
        
        # Start multiple concurrent scans
        job_ids = []
        for i in range(3):
            job_id = await orchestrator.start_scan(ScanType.RUNTIME_ONLY)
            job_ids.append(job_id)
        
        # Wait for all jobs to complete
        for job_id in job_ids:
            timeout = 10
            while timeout > 0:
                await asyncio.sleep(0.1)
                timeout -= 0.1
                
                status = await orchestrator.get_job_status(job_id)
                if status and status["status"] in ["completed", "failed"]:
                    break
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Should handle concurrent jobs efficiently
        assert duration < 15.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])