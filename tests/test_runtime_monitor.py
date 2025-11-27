"""
Comprehensive test suite for runtime monitoring system.
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.runtime_monitor import (
    RuntimeMonitor, ProcessInfo, ServiceInfo, ContainerInfo, 
    SystemMetrics, PerformanceAlert, ProcessTrend
)
from src.services.project_analyzer import ProjectAnalyzer
from src.models.project import Project
from src.models.runtime import RuntimeStatus, ProcessSnapshot, PerformanceAlert as PerformanceAlertModel
from src.council.memory_integration import MemoryIntegration
from src.council.knowledge_graph_integration import KnowledgeGraphIntegration


class TestRuntimeMonitor:
    """Test suite for RuntimeMonitor class."""

    @pytest.fixture
    async def mock_session(self):
        """Create mock async database session."""
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    async def mock_memory(self):
        """Create mock memory integration."""
        memory = AsyncMock(spec=MemoryIntegration)
        memory.store_context = AsyncMock()
        return memory

    @pytest.fixture
    async def mock_kg(self):
        """Create mock knowledge graph integration."""
        kg = AsyncMock(spec=KnowledgeGraphIntegration)
        kg.add_performance_alert = AsyncMock()
        return kg

    @pytest.fixture
    async def runtime_monitor(self, mock_session, mock_memory, mock_kg):
        """Create RuntimeMonitor instance with mocked dependencies."""
        monitor = RuntimeMonitor(mock_session, mock_memory, mock_kg)
        monitor.project_mapping = {
            "/test/project1": "project-1-id",
            "/test/project2": "project-2-id"
        }
        return monitor

    def test_init(self, mock_session, mock_memory, mock_kg):
        """Test RuntimeMonitor initialization."""
        monitor = RuntimeMonitor(mock_session, mock_memory, mock_kg)
        
        assert monitor.session == mock_session
        assert monitor.memory == mock_memory
        assert monitor.kg == mock_kg
        assert isinstance(monitor.known_processes, dict)
        assert isinstance(monitor.known_services, dict)
        assert isinstance(monitor.known_containers, dict)
        assert isinstance(monitor.project_mapping, dict)
        assert isinstance(monitor.performance_history, dict)
        assert isinstance(monitor.process_history, dict)
        assert isinstance(monitor.recent_alerts, dict)

    @pytest.mark.asyncio
    async def test_initialize(self, runtime_monitor, mock_session):
        """Test monitor initialization process."""
        # Mock database query
        mock_result = Mock()
        mock_result.fetchall.return_value = [
            ("project-1-id", "/test/project1"),
            ("project-2-id", "/test/project2")
        ]
        mock_session.execute.return_value = mock_result

        await runtime_monitor.initialize()

        # Verify project mappings were loaded
        assert runtime_monitor.project_mapping["/test/project1"] == "project-1-id"
        assert runtime_monitor.project_mapping["/test/project2"] == "project-2-id"

    @pytest.mark.asyncio
    @patch('psutil.process_iter')
    async def test_scan_processes(self, mock_process_iter, runtime_monitor):
        """Test process scanning functionality."""
        # Mock psutil processes
        mock_proc1 = Mock()
        mock_proc1.info = {
            'pid': 1234,
            'name': 'python',
            'cmdline': ['python', 'app.py'],
            'cwd': '/test/project1',
            'status': 'running',
            'cpu_percent': 15.5,
            'memory_percent': 8.2,
            'memory_info': Mock(rss=104857600),  # 100MB
            'create_time': 1234567890
        }
        
        mock_proc2 = Mock()
        mock_proc2.info = {
            'pid': 5678,
            'name': 'node',
            'cmdline': ['node', 'server.js'],
            'cwd': '/test/project2',
            'status': 'running',
            'cpu_percent': 25.0,
            'memory_percent': 12.1,
            'memory_info': Mock(rss=209715200),  # 200MB
            'create_time': 1234567900
        }

        mock_process_iter.return_value = [mock_proc1, mock_proc2]

        # Mock psutil.Process for port checking
        with patch('psutil.Process') as mock_ps_process:
            mock_ps_instance = Mock()
            mock_ps_instance.connections.return_value = [
                Mock(status='CONN_LISTEN', laddr=Mock(port=3000))
            ]
            mock_ps_process.return_value = mock_ps_instance

            processes = await runtime_monitor.scan_processes()

        assert len(processes) == 2
        assert any(p.name == 'python' and p.pid == 1234 for p in processes)
        assert any(p.name == 'node' and p.pid == 5678 for p in processes)

        # Check project mapping
        python_proc = next(p for p in processes if p.name == 'python')
        assert python_proc.project_id == "project-1-id"
        assert python_proc.project_path == "/test/project1"

    def test_should_skip_process(self, runtime_monitor):
        """Test process filtering logic."""
        # Should skip system processes
        assert runtime_monitor._should_skip_process('kernel_task', 'kernel_task')
        assert runtime_monitor._should_skip_process('launchd', 'launchd')
        
        # Should skip system paths
        assert runtime_monitor._should_skip_process('grep', '/usr/bin/grep pattern')
        assert runtime_monitor._should_skip_process('ps', '/usr/sbin/ps aux')
        
        # Should not skip development processes
        assert not runtime_monitor._should_skip_process('python', 'python app.py')
        assert not runtime_monitor._should_skip_process('node', 'node server.js')

    def test_is_development_process(self, runtime_monitor):
        """Test development process detection."""
        # Should detect development processes
        assert runtime_monitor._is_development_process('python', 'python manage.py runserver')
        assert runtime_monitor._is_development_process('node', 'npm start')
        assert runtime_monitor._is_development_process('cargo', 'cargo run')
        assert runtime_monitor._is_development_process('java', 'java -jar app.jar')
        
        # Should detect by command line patterns
        assert runtime_monitor._is_development_process('uvicorn', 'python -m uvicorn app:main')
        assert runtime_monitor._is_development_process('webpack', 'webpack-dev-server')
        
        # Should not detect non-development processes
        assert not runtime_monitor._is_development_process('Safari', 'Safari')
        assert not runtime_monitor._is_development_process('chrome', 'Google Chrome')

    @pytest.mark.asyncio
    async def test_match_process_to_project(self, runtime_monitor):
        """Test process to project matching logic."""
        process_info = ProcessInfo(
            pid=1234,
            name='python',
            cmdline=['python', 'app.py'],
            cwd='/test/project1/src',
            status='running',
            cpu_percent=15.5,
            memory_percent=8.2,
            memory_rss=104857600,
            create_time=1234567890
        )

        await runtime_monitor._match_process_to_project(process_info)

        # Should match to parent project directory
        assert process_info.project_id == "project-1-id"
        assert process_info.project_path == "/test/project1"

    @pytest.mark.asyncio
    @patch('socket.socket')
    async def test_check_port_service(self, mock_socket, runtime_monitor):
        """Test service port checking."""
        # Mock successful connection
        mock_sock_instance = Mock()
        mock_sock_instance.connect_ex.return_value = 0  # Success
        mock_socket.return_value = mock_sock_instance

        # Add a mock process using this port
        runtime_monitor.known_processes[1234] = ProcessInfo(
            pid=1234,
            name='python',
            cmdline=['python', 'app.py'],
            cwd='/test/project1',
            status='running',
            cpu_percent=15.5,
            memory_percent=8.2,
            memory_rss=104857600,
            create_time=1234567890,
            ports=[3000]
        )

        service = await runtime_monitor._check_port_service(3000)

        assert service is not None
        assert service.port == 3000
        assert service.status == "active"
        assert service.pid == 1234
        assert service.process_name == "python"

    @pytest.mark.asyncio
    async def test_collect_system_metrics(self, runtime_monitor):
        """Test system metrics collection."""
        with patch('psutil.cpu_percent', return_value=45.2), \
             patch('psutil.virtual_memory', return_value=Mock(percent=67.8)), \
             patch('psutil.disk_usage', return_value=Mock(percent=78.5)), \
             patch('psutil.net_io_counters', return_value=Mock(bytes_sent=1048576, bytes_recv=2097152)), \
             patch('psutil.net_connections', return_value=[Mock()] * 150), \
             patch('psutil.pids', return_value=list(range(200))), \
             patch('os.getloadavg', return_value=(1.5, 1.2, 0.8)):

            metrics = await runtime_monitor.collect_system_metrics()

            assert isinstance(metrics, SystemMetrics)
            assert metrics.cpu_percent == 45.2
            assert metrics.memory_percent == 67.8
            assert metrics.disk_usage_percent == 78.5
            assert metrics.network_bytes_sent == 1048576
            assert metrics.network_bytes_recv == 2097152
            assert metrics.active_connections == 150
            assert metrics.processes_count == 200
            assert metrics.load_average == (1.5, 1.2, 0.8)

    @pytest.mark.asyncio
    async def test_analyze_performance_issues(self, runtime_monitor):
        """Test performance issue analysis."""
        # Create system metrics that should trigger alerts
        metrics = SystemMetrics(
            timestamp=datetime.now(timezone.utc),
            cpu_percent=98.5,  # Critical
            memory_percent=90.0,  # Warning
            disk_usage_percent=95.5,  # Critical
            network_bytes_sent=1048576,
            network_bytes_recv=2097152,
            load_average=(2.5, 2.2, 1.8),
            processes_count=250,
            active_connections=150
        )

        alerts = await runtime_monitor._analyze_performance_issues(metrics)

        # Should generate alerts for critical CPU and disk usage
        assert len(alerts) >= 2
        
        cpu_alert = next((a for a in alerts if a.alert_type == "cpu_critical"), None)
        assert cpu_alert is not None
        assert cpu_alert.severity == "critical"
        assert cpu_alert.current_value == 98.5

        disk_alert = next((a for a in alerts if a.alert_type == "disk_critical"), None)
        assert disk_alert is not None
        assert disk_alert.severity == "critical"
        assert disk_alert.current_value == 95.5

    def test_calculate_trend(self, runtime_monitor):
        """Test trend calculation algorithm."""
        # Test increasing trend
        increasing_values = [10, 12, 14, 16, 18, 20, 22]
        trend = runtime_monitor._calculate_trend(increasing_values)
        
        assert trend['significant'] is True
        assert trend['direction'] == 'increasing'
        assert trend['confidence'] > 0.9

        # Test stable trend (should not be significant)
        stable_values = [50, 51, 49, 50, 52, 48, 50]
        trend = runtime_monitor._calculate_trend(stable_values)
        
        assert trend['significant'] is False

        # Test decreasing trend
        decreasing_values = [100, 90, 80, 70, 60, 50, 40]
        trend = runtime_monitor._calculate_trend(decreasing_values)
        
        assert trend['significant'] is True
        assert trend['direction'] == 'decreasing'
        assert trend['confidence'] > 0.9

    @pytest.mark.asyncio
    async def test_detect_memory_leaks(self, runtime_monitor):
        """Test memory leak detection."""
        # Create a process with increasing memory usage
        process_info = ProcessInfo(
            pid=1234,
            name='python',
            cmdline=['python', 'app.py'],
            cwd='/test/project1',
            status='running',
            cpu_percent=15.5,
            memory_percent=8.2,
            memory_rss=104857600,  # 100MB
            create_time=1234567890,
            project_id="project-1-id"
        )

        # Simulate 20 snapshots with steadily increasing memory
        runtime_monitor.process_history[1234] = []
        base_memory = 100 * 1024 * 1024  # 100MB base
        for i in range(20):
            snapshot = ProcessInfo(
                pid=1234,
                name='python',
                cmdline=['python', 'app.py'],
                cwd='/test/project1',
                status='running',
                cpu_percent=15.5,
                memory_percent=8.2,
                memory_rss=base_memory + (i * 5 * 1024 * 1024),  # +5MB each snapshot
                create_time=1234567890 - (19 - i) * 30,  # 30 seconds apart
                project_id="project-1-id"
            )
            runtime_monitor.process_history[1234].append(snapshot)

        runtime_monitor.known_processes[1234] = process_info

        leaks = await runtime_monitor.detect_memory_leaks()

        assert len(leaks) == 1
        leak = leaks[0]
        assert leak['process_name'] == 'python'
        assert leak['pid'] == 1234
        assert leak['project_id'] == "project-1-id"
        assert leak['growth_mb_per_minute'] > 0

    @pytest.mark.asyncio
    async def test_get_performance_summary(self, runtime_monitor):
        """Test performance summary generation."""
        # Add some system performance history
        runtime_monitor.performance_history['system'] = [
            {
                'timestamp': datetime.now(timezone.utc) - timedelta(minutes=30),
                'cpu_percent': 45.0,
                'memory_percent': 60.0,
                'disk_percent': 70.0,
                'process_count': 150,
                'connections': 100
            },
            {
                'timestamp': datetime.now(timezone.utc) - timedelta(minutes=15),
                'cpu_percent': 50.0,
                'memory_percent': 65.0,
                'disk_percent': 72.0,
                'process_count': 155,
                'connections': 110
            }
        ]

        summary = await runtime_monitor.get_performance_summary(hours=1)

        assert 'system_summary' in summary
        assert 'period_hours' in summary
        assert summary['period_hours'] == 1
        
        system_summary = summary['system_summary']
        assert 'avg_cpu_percent' in system_summary
        assert 'max_cpu_percent' in system_summary
        assert 'data_points' in system_summary


class TestProjectAnalyzer:
    """Test suite for ProjectAnalyzer runtime performance features."""

    @pytest.fixture
    async def project_analyzer(self):
        """Create ProjectAnalyzer instance."""
        session = AsyncMock(spec=AsyncSession)
        memory = AsyncMock(spec=MemoryIntegration)
        kg = AsyncMock(spec=KnowledgeGraphIntegration)
        return ProjectAnalyzer(session, memory, kg)

    @pytest.mark.asyncio
    async def test_analyze_runtime_performance(self, project_analyzer):
        """Test runtime performance analysis."""
        # Create mock runtime data showing performance issues
        runtime_data = [
            {'cpu_percent': 30.0, 'memory_rss': 100 * 1024 * 1024, 'timestamp': '2023-01-01T10:00:00Z'},
            {'cpu_percent': 40.0, 'memory_rss': 120 * 1024 * 1024, 'timestamp': '2023-01-01T10:01:00Z'},
            {'cpu_percent': 50.0, 'memory_rss': 140 * 1024 * 1024, 'timestamp': '2023-01-01T10:02:00Z'},
            {'cpu_percent': 60.0, 'memory_rss': 160 * 1024 * 1024, 'timestamp': '2023-01-01T10:03:00Z'},
            {'cpu_percent': 70.0, 'memory_rss': 180 * 1024 * 1024, 'timestamp': '2023-01-01T10:04:00Z'},
            {'cpu_percent': 85.0, 'memory_rss': 200 * 1024 * 1024, 'timestamp': '2023-01-01T10:05:00Z'},
        ]

        analysis = await project_analyzer.analyze_runtime_performance('/test/project', runtime_data)

        assert 'bottlenecks' in analysis
        assert 'trends' in analysis
        assert 'recommendations' in analysis
        assert 'resource_efficiency' in analysis
        assert 'performance_score' in analysis

        # Should detect CPU and memory trends
        assert len(analysis['trends']) > 0
        
        # Should have performance recommendations
        assert len(analysis['recommendations']) > 0

    def test_analyze_metric_trend(self, project_analyzer):
        """Test metric trend analysis."""
        # Test significant increasing CPU trend
        cpu_values = [30, 40, 50, 60, 70, 85]
        trend = project_analyzer._analyze_metric_trend(cpu_values, 'CPU')

        assert trend['significant'] is True
        assert trend['metric'] == 'CPU'
        assert trend['direction'] == 'increasing'
        assert trend['severity'] in ['medium', 'high', 'critical']

        # Test insufficient data
        small_dataset = [30, 40]
        trend = project_analyzer._analyze_metric_trend(small_dataset, 'CPU')
        assert trend['significant'] is False

    def test_get_cpu_recommendation(self, project_analyzer):
        """Test CPU recommendation generation."""
        # Test critical CPU trend
        critical_trend = {
            'direction': 'increasing',
            'current_value': 95.0,
            'confidence': 0.9
        }
        recommendation = project_analyzer._get_cpu_recommendation(critical_trend)
        assert 'Immediate action required' in recommendation

        # Test moderate CPU trend
        moderate_trend = {
            'direction': 'increasing',
            'current_value': 75.0,
            'confidence': 0.8
        }
        recommendation = project_analyzer._get_cpu_recommendation(moderate_trend)
        assert 'Consider optimizing' in recommendation

        # Test decreasing trend
        good_trend = {
            'direction': 'decreasing',
            'current_value': 40.0,
            'confidence': 0.7
        }
        recommendation = project_analyzer._get_cpu_recommendation(good_trend)
        assert 'Good:' in recommendation

    def test_calculate_resource_efficiency(self, project_analyzer):
        """Test resource efficiency calculation."""
        runtime_data = [
            {'cpu_percent': 45.0, 'memory_rss': 100 * 1024 * 1024, 'response_time_ms': 150},
            {'cpu_percent': 50.0, 'memory_rss': 105 * 1024 * 1024, 'response_time_ms': 160},
            {'cpu_percent': 48.0, 'memory_rss': 110 * 1024 * 1024, 'response_time_ms': 140},
        ]

        efficiency = project_analyzer._calculate_resource_efficiency(runtime_data)

        assert 'cpu_stability' in efficiency
        assert 'cpu_utilization' in efficiency
        assert 'memory_growth_rate' in efficiency
        assert 'response_time_score' in efficiency

        # CPU stability should be reasonable for low variance
        assert efficiency['cpu_stability'] > 50

    def test_calculate_performance_score_runtime(self, project_analyzer):
        """Test runtime performance score calculation."""
        # Test with no issues
        good_analysis = {
            'bottlenecks': [],
            'trends': [],
            'resource_efficiency': {
                'cpu_stability': 90,
                'memory_growth_rate': 85
            }
        }
        score = project_analyzer._calculate_performance_score_runtime(good_analysis)
        assert score > 100  # Should get bonus points

        # Test with critical issues
        bad_analysis = {
            'bottlenecks': [
                {'severity': 'critical'},
                {'severity': 'high'}
            ],
            'trends': [
                {'direction': 'increasing', 'metric': 'CPU', 'severity': 'critical'}
            ],
            'resource_efficiency': {}
        }
        score = project_analyzer._calculate_performance_score_runtime(bad_analysis)
        assert score < 50  # Should be heavily penalized

    def test_generate_performance_recommendations(self, project_analyzer):
        """Test performance recommendation generation."""
        analysis = {
            'bottlenecks': [
                {'type': 'memory_leak', 'severity': 'high'},
                {'type': 'cpu_bottleneck', 'severity': 'medium'}
            ],
            'trends': [],
            'resource_efficiency': {
                'cpu_stability': 60,
                'response_time_score': 50
            }
        }

        recommendations = project_analyzer._generate_performance_recommendations(analysis)

        assert len(recommendations) > 0
        
        # Should include memory-specific recommendations
        memory_rec = any('memory' in rec.lower() for rec in recommendations)
        assert memory_rec

        # Should include CPU-specific recommendations
        cpu_rec = any('cpu' in rec.lower() for rec in recommendations)
        assert cpu_rec

        # Should include monitoring recommendation
        monitoring_rec = any('monitoring' in rec.lower() for rec in recommendations)
        assert monitoring_rec


@pytest.mark.integration
class TestRuntimeMonitoringIntegration:
    """Integration tests for the complete runtime monitoring system."""

    @pytest.mark.asyncio
    async def test_full_monitoring_cycle(self):
        """Test a complete monitoring cycle with mocked components."""
        # This would be a full integration test in a real scenario
        # For now, we'll test the coordination between components
        
        session = AsyncMock(spec=AsyncSession)
        memory = AsyncMock(spec=MemoryIntegration)
        kg = AsyncMock(spec=KnowledgeGraphIntegration)
        
        monitor = RuntimeMonitor(session, memory, kg)
        analyzer = ProjectAnalyzer(session, memory, kg)

        # Mock some project mappings
        monitor.project_mapping = {"/test/project": "test-project-id"}

        # Test that the components can work together
        # In a real integration test, this would involve actual process scanning
        # and database operations
        
        assert monitor.session == session
        assert analyzer.session == session
        assert monitor.memory == memory
        assert analyzer.memory == memory


if __name__ == "__main__":
    pytest.main([__file__, "-v"])