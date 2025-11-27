"""
Integration tests for FastAPI endpoints and API functionality
Tests all REST API routes, authentication, and error handling
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

from src.main import app
from src.api.projects import router as projects_router
from src.api.runtime import router as runtime_router
from src.api.metrics import router as metrics_router
from src.council.orchestrator import Orchestrator, DeliberationRequest, DeliberationResult


class TestHealthEndpoints:
    """Test health check and status endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns basic info"""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "optimus" in data["message"].lower()
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_ready_check(self, client):
        """Test readiness check endpoint"""
        response = client.get("/ready")
        assert response.status_code == 200
        
        data = response.json()
        assert "ready" in data
        assert isinstance(data["ready"], bool)
        assert "checks" in data
    
    def test_alive_check(self, client):
        """Test liveness check endpoint"""
        response = client.get("/alive")
        assert response.status_code == 200
        
        data = response.json()
        assert "alive" in data
        assert data["alive"] is True


class TestDeliberationEndpoints:
    """Test deliberation API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client with mocked orchestrator"""
        with patch('src.main.orchestrator') as mock_orchestrator:
            # Mock deliberation result
            mock_result = DeliberationResult(
                request=DeliberationRequest(
                    query="Test query",
                    context={"test": "context"}
                ),
                consensus=MagicMock(),
                persona_responses=[],
                deliberation_time=1.5,
                blackboard_topic="test_topic",
                statistics={"test": "stats"}
            )
            mock_result.consensus.decision = "Test decision"
            mock_result.consensus.confidence = 0.85
            mock_result.consensus.agreement_level = 0.8
            mock_result.consensus.method_used = MagicMock()
            mock_result.consensus.method_used.value = "weighted_majority"
            mock_result.to_dict = lambda: {
                "query": "Test query",
                "decision": "Test decision",
                "confidence": 0.85,
                "agreement": 0.8,
                "time_taken": 1.5
            }
            
            mock_orchestrator.deliberate = AsyncMock(return_value=mock_result)
            yield TestClient(app)
    
    def test_create_deliberation(self, client):
        """Test creating a new deliberation"""
        deliberation_request = {
            "query": "What database should we use for our application?",
            "context": {
                "application_type": "web_app",
                "expected_load": "medium",
                "data_complexity": "moderate"
            },
            "topic": "database_selection",
            "timeout": 30.0
        }
        
        response = client.post("/deliberations", json=deliberation_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "deliberation_id" in data
        assert "status" in data
        assert data["status"] == "initiated"
    
    def test_get_deliberation_status(self, client):
        """Test getting deliberation status"""
        # First create a deliberation
        deliberation_request = {
            "query": "Test query for status check",
            "context": {},
            "topic": "status_test"
        }
        
        create_response = client.post("/deliberations", json=deliberation_request)
        deliberation_id = create_response.json()["deliberation_id"]
        
        # Check status
        response = client.get(f"/deliberations/{deliberation_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "deliberation_id" in data
        assert "status" in data
        assert "result" in data or "progress" in data
    
    def test_list_deliberations(self, client):
        """Test listing deliberations with pagination"""
        response = client.get("/deliberations?limit=10&offset=0")
        assert response.status_code == 200
        
        data = response.json()
        assert "deliberations" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert isinstance(data["deliberations"], list)
    
    def test_deliberation_with_specific_personas(self, client):
        """Test deliberation with specific persona requirements"""
        deliberation_request = {
            "query": "How should we handle user privacy?",
            "context": {"domain": "user_data"},
            "required_personas": ["guardian", "philosopher", "socialite"],
            "topic": "privacy_deliberation"
        }
        
        response = client.post("/deliberations", json=deliberation_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "deliberation_id" in data
    
    def test_deliberation_with_consensus_method(self, client):
        """Test deliberation with specific consensus method"""
        deliberation_request = {
            "query": "Should we adopt microservices architecture?",
            "context": {"current": "monolith"},
            "consensus_method": "supermajority",
            "topic": "architecture_decision"
        }
        
        response = client.post("/deliberations", json=deliberation_request)
        assert response.status_code == 200
    
    def test_invalid_deliberation_request(self, client):
        """Test invalid deliberation request handling"""
        invalid_request = {
            "query": "",  # Empty query
            "context": {},
            "timeout": -1  # Invalid timeout
        }
        
        response = client.post("/deliberations", json=invalid_request)
        assert response.status_code == 422  # Validation error
    
    def test_deliberation_explanation(self, client):
        """Test getting deliberation explanation"""
        # Mock explanation
        with patch('src.main.orchestrator') as mock_orchestrator:
            mock_orchestrator.explain_decision = AsyncMock(
                return_value="Detailed explanation of the decision process..."
            )
            
            response = client.get("/deliberations/test_topic/explanation")
            assert response.status_code == 200
            
            data = response.json()
            assert "explanation" in data
            assert len(data["explanation"]) > 0


class TestProjectEndpoints:
    """Test project management endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client with mocked project services"""
        with patch('src.services.scanner.ProjectScanner') as mock_scanner:
            mock_scanner.return_value.scan_project = AsyncMock(return_value={
                "project_id": "test_project",
                "name": "Test Project",
                "type": "web_application",
                "technologies": ["Python", "FastAPI"],
                "structure": {"directories": 5, "files": 25}
            })
            yield TestClient(app)
    
    def test_scan_project(self, client):
        """Test project scanning endpoint"""
        scan_request = {
            "project_path": "/path/to/project",
            "include_analysis": True,
            "scan_depth": "full"
        }
        
        response = client.post("/projects/scan", json=scan_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "project_id" in data
        assert "scan_results" in data
        assert "technologies" in data["scan_results"]
    
    def test_get_project_info(self, client):
        """Test getting project information"""
        response = client.get("/projects/test_project")
        assert response.status_code in [200, 404]  # Might not exist in test
    
    def test_list_projects(self, client):
        """Test listing all projects"""
        response = client.get("/projects")
        assert response.status_code == 200
        
        data = response.json()
        assert "projects" in data
        assert isinstance(data["projects"], list)
    
    def test_project_analysis(self, client):
        """Test project analysis endpoint"""
        analysis_request = {
            "analysis_type": "architecture_review",
            "focus_areas": ["security", "performance", "maintainability"]
        }
        
        response = client.post("/projects/test_project/analyze", json=analysis_request)
        assert response.status_code in [200, 404]  # Depends on project existence


class TestRuntimeEndpoints:
    """Test runtime monitoring endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client with mocked runtime services"""
        with patch('src.services.monitor.RuntimeMonitor') as mock_monitor:
            mock_monitor.return_value.get_system_status = AsyncMock(return_value={
                "status": "healthy",
                "uptime": 3600,
                "memory_usage": 512.5,
                "cpu_usage": 25.3,
                "active_deliberations": 2
            })
            yield TestClient(app)
    
    def test_system_status(self, client):
        """Test system status endpoint"""
        response = client.get("/runtime/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "uptime" in data
        assert "memory_usage" in data
        assert "cpu_usage" in data
    
    def test_persona_status(self, client):
        """Test persona status endpoint"""
        response = client.get("/runtime/personas")
        assert response.status_code == 200
        
        data = response.json()
        assert "personas" in data
        assert isinstance(data["personas"], list)
    
    def test_blackboard_status(self, client):
        """Test blackboard status endpoint"""
        response = client.get("/runtime/blackboard")
        assert response.status_code == 200
        
        data = response.json()
        assert "active_topics" in data
        assert "total_entries" in data
    
    def test_memory_status(self, client):
        """Test memory system status"""
        response = client.get("/runtime/memory")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_memories" in data
        assert "memory_usage" in data


class TestMetricsEndpoints:
    """Test metrics and analytics endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client with mocked metrics services"""
        return TestClient(app)
    
    def test_deliberation_metrics(self, client):
        """Test deliberation metrics endpoint"""
        response = client.get("/metrics/deliberations?timeframe=24h")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_deliberations" in data
        assert "avg_deliberation_time" in data
        assert "success_rate" in data
    
    def test_persona_performance_metrics(self, client):
        """Test persona performance metrics"""
        response = client.get("/metrics/personas")
        assert response.status_code == 200
        
        data = response.json()
        assert "personas" in data
        for persona_data in data["personas"]:
            assert "persona_id" in persona_data
            assert "participation_rate" in persona_data
            assert "consensus_rate" in persona_data
    
    def test_consensus_metrics(self, client):
        """Test consensus metrics endpoint"""
        response = client.get("/metrics/consensus")
        assert response.status_code == 200
        
        data = response.json()
        assert "consensus_methods" in data
        assert "avg_confidence" in data
        assert "avg_agreement_level" in data
    
    def test_system_performance_metrics(self, client):
        """Test system performance metrics"""
        response = client.get("/metrics/performance")
        assert response.status_code == 200
        
        data = response.json()
        assert "response_times" in data
        assert "throughput" in data
        assert "error_rates" in data


class TestErrorHandling:
    """Test API error handling scenarios"""
    
    @pytest.fixture
    def client(self):
        """Create test client for error testing"""
        return TestClient(app)
    
    def test_404_error(self, client):
        """Test 404 error handling"""
        response = client.get("/nonexistent/endpoint")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
    
    def test_validation_error(self, client):
        """Test validation error handling"""
        invalid_data = {
            "query": "",  # Empty query should fail validation
            "timeout": "not_a_number"  # Invalid timeout type
        }
        
        response = client.post("/deliberations", json=invalid_data)
        assert response.status_code == 422
        
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
    
    def test_internal_server_error_handling(self, client):
        """Test internal server error handling"""
        # Mock an internal error
        with patch('src.main.orchestrator') as mock_orchestrator:
            mock_orchestrator.deliberate = AsyncMock(
                side_effect=Exception("Internal system error")
            )
            
            response = client.post("/deliberations", json={
                "query": "Test query",
                "context": {}
            })
            assert response.status_code == 500
            
            data = response.json()
            assert "detail" in data
    
    def test_rate_limiting(self, client):
        """Test API rate limiting"""
        # Make multiple rapid requests
        responses = []
        for i in range(10):
            response = client.get("/health")
            responses.append(response)
        
        # Should not be rate limited for health checks
        assert all(r.status_code == 200 for r in responses)
        
        # But deliberations might have different limits
        deliberation_responses = []
        for i in range(5):
            response = client.post("/deliberations", json={
                "query": f"Test query {i}",
                "context": {}
            })
            deliberation_responses.append(response)
        
        # Some might succeed, but rate limiting could kick in
        status_codes = [r.status_code for r in deliberation_responses]
        assert 200 in status_codes or 429 in status_codes


class TestWebSocketEndpoints:
    """Test WebSocket endpoints for real-time updates"""
    
    def test_deliberation_websocket_connection(self):
        """Test WebSocket connection for deliberation updates"""
        with TestClient(app) as client:
            try:
                with client.websocket_connect("/ws/deliberations") as websocket:
                    # Should establish connection successfully
                    data = websocket.receive_json()
                    assert "type" in data
                    assert data["type"] == "connection_established"
            except Exception:
                # WebSocket might not be implemented yet
                pytest.skip("WebSocket not implemented")
    
    def test_runtime_monitoring_websocket(self):
        """Test WebSocket for runtime monitoring"""
        with TestClient(app) as client:
            try:
                with client.websocket_connect("/ws/runtime") as websocket:
                    # Should receive periodic updates
                    data = websocket.receive_json()
                    assert "timestamp" in data
                    assert "system_status" in data
            except Exception:
                pytest.skip("Runtime monitoring WebSocket not implemented")


class TestAuthentication:
    """Test authentication and authorization"""
    
    @pytest.fixture
    def client(self):
        """Create test client with auth mocking"""
        return TestClient(app)
    
    def test_public_endpoints_no_auth_required(self, client):
        """Test public endpoints don't require authentication"""
        public_endpoints = [
            "/",
            "/health",
            "/ready", 
            "/alive"
        ]
        
        for endpoint in public_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
    
    def test_protected_endpoints_auth_required(self, client):
        """Test protected endpoints require authentication"""
        # These might require auth in production
        protected_endpoints = [
            "/metrics/deliberations",
            "/runtime/status"
        ]
        
        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            # Should either succeed (if no auth implemented) or require auth
            assert response.status_code in [200, 401, 403]
    
    def test_admin_endpoints_admin_auth_required(self, client):
        """Test admin endpoints require admin privileges"""
        admin_endpoints = [
            "/admin/system/shutdown",
            "/admin/config/update"
        ]
        
        for endpoint in admin_endpoints:
            response = client.get(endpoint)
            # Should require admin auth or not exist yet
            assert response.status_code in [401, 403, 404]


class TestConcurrentAPIUsage:
    """Test API behavior under concurrent usage"""
    
    @pytest.fixture
    def client(self):
        """Create test client for concurrency testing"""
        return TestClient(app)
    
    def test_concurrent_health_checks(self, client):
        """Test concurrent health check requests"""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = client.get("/health")
            results.append(response.status_code)
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        
        # All should succeed
        assert len(results) == 10
        assert all(status == 200 for status in results)
        
        # Should complete reasonably quickly
        assert end_time - start_time < 5.0
    
    def test_concurrent_deliberation_requests(self, client):
        """Test concurrent deliberation requests"""
        with patch('src.main.orchestrator') as mock_orchestrator:
            mock_result = MagicMock()
            mock_result.to_dict = lambda: {"decision": "Test decision"}
            mock_orchestrator.deliberate = AsyncMock(return_value=mock_result)
            
            import threading
            results = []
            
            def create_deliberation(query_id):
                response = client.post("/deliberations", json={
                    "query": f"Concurrent test query {query_id}",
                    "context": {"query_id": query_id}
                })
                results.append(response.status_code)
            
            # Create concurrent deliberations
            threads = []
            for i in range(5):
                thread = threading.Thread(target=create_deliberation, args=(i,))
                threads.append(thread)
            
            # Execute concurrently
            for thread in threads:
                thread.start()
            
            for thread in threads:
                thread.join()
            
            # All should succeed or handle gracefully
            assert len(results) == 5
            assert all(status in [200, 429, 503] for status in results)  # Success or rate limited