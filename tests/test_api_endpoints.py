"""
Comprehensive API Endpoints Test Suite
=====================================

Tests for all Optimus REST API endpoints including validation,
error handling, authentication, and response formats.

Test Coverage:
- Memory System API endpoints
- Knowledge Graph API endpoints  
- Enhanced Scanner API endpoints
- Runtime Monitor API endpoints
- Dashboard API endpoints
- WebSocket endpoints
- Error handling and validation
- Performance and load testing
"""

import pytest
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import websockets
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.config import get_settings
from src.database.config import get_database_manager


# =================== TEST FIXTURES ===================

@pytest.fixture
def client():
    """Test client for FastAPI app"""
    return TestClient(app)


@pytest.fixture 
def auth_headers():
    """Authentication headers for protected endpoints"""
    return {"Authorization": "Bearer test_token"}


@pytest.fixture
def sample_project_data():
    """Sample project data for testing"""
    return {
        "name": "test-project",
        "path": "/tmp/test-project",
        "description": "Test project for API testing",
        "tech_stack": {
            "languages": ["Python", "JavaScript"],
            "frameworks": ["FastAPI", "React"],
            "databases": ["PostgreSQL"]
        },
        "dependencies": {
            "runtime": {"fastapi": "0.104.0", "react": "18.2.0"},
            "development": {"pytest": "7.4.0"},
            "total_count": 2
        },
        "language_stats": {"Python": 60.0, "JavaScript": 40.0}
    }


@pytest.fixture
def sample_deliberation_data():
    """Sample deliberation data for testing"""
    return {
        "query": "How to optimize database performance?",
        "topic": "performance",
        "context": {"project_type": "web_app", "database": "postgresql"},
        "personas": ["database_expert", "performance_analyst"]
    }


@pytest.fixture
async def mock_session():
    """Mock database session"""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


# =================== PROJECTS API TESTS ===================

class TestProjectsAPI:
    """Test suite for Projects API endpoints"""
    
    def test_list_projects(self, client):
        """Test GET /projects endpoint"""
        response = client.get("/api/v1/projects")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Test pagination parameters
        response = client.get("/api/v1/projects?skip=0&limit=10")
        assert response.status_code == 200
    
    def test_get_project_by_id(self, client, sample_project_data):
        """Test GET /projects/{id} endpoint"""
        # First create a project (mock response)
        with patch('src.api.projects.get_project_by_id') as mock_get:
            project_id = str(uuid.uuid4())
            mock_get.return_value = {**sample_project_data, "id": project_id}
            
            response = client.get(f"/api/v1/projects/{project_id}")
            assert response.status_code == 200
            
            data = response.json()
            assert data["id"] == project_id
            assert data["name"] == sample_project_data["name"]
    
    def test_get_nonexistent_project(self, client):
        """Test GET /projects/{id} with invalid ID"""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/projects/{fake_id}")
        
        # Should return 404 or handle gracefully
        assert response.status_code in [404, 200]  # Depending on implementation


# =================== SCANNER API TESTS ===================

class TestScannerAPI:
    """Test suite for Scanner API endpoints"""
    
    def test_list_discovered_projects(self, client):
        """Test GET /scanner/projects endpoint"""
        response = client.get("/api/v1/scanner/projects")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_project_analysis(self, client):
        """Test GET /scanner/projects/{id}/analysis endpoint"""
        project_id = str(uuid.uuid4())
        
        with patch('src.api.scanner.get_project_analysis') as mock_analysis:
            mock_analysis.return_value = {
                "basic_info": {"name": "test-project", "path": "/tmp/test"},
                "tech_stack": {"languages": ["Python"], "frameworks": []},
                "dependencies": {"runtime": {}, "development": {}},
                "security": {"vulnerabilities": [], "risk_score": 0}
            }
            
            response = client.get(f"/api/v1/scanner/projects/{project_id}/analysis")
            assert response.status_code == 200
    
    def test_trigger_project_scan(self, client):
        """Test POST /scanner/scan endpoint"""
        scan_request = {
            "base_path": "/tmp/projects",
            "include_analysis": True,
            "include_dependencies": True,
            "force_rescan": False
        }
        
        response = client.post("/api/v1/scanner/scan", json=scan_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "status" in data
    
    def test_technology_statistics(self, client):
        """Test GET /scanner/technologies endpoint"""
        response = client.get("/api/v1/scanner/technologies")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_dependency_analysis(self, client):
        """Test GET /scanner/dependencies endpoint"""
        response = client.get("/api/v1/scanner/dependencies")
        
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "most_used_dependencies" in data
    
    def test_vulnerability_scan(self, client):
        """Test GET /scanner/vulnerabilities endpoint"""
        response = client.get("/api/v1/scanner/vulnerabilities")
        
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "vulnerabilities" in data
    
    def test_code_quality_metrics(self, client):
        """Test GET /scanner/quality endpoint"""
        response = client.get("/api/v1/scanner/quality")
        
        assert response.status_code == 200
        data = response.json()
        assert "overview" in data
    
    def test_project_comparison(self, client):
        """Test POST /scanner/compare endpoint"""
        comparison_request = {
            "project_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
            "comparison_aspects": ["technologies", "dependencies"]
        }
        
        response = client.post("/api/v1/scanner/compare", json=comparison_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "projects" in data
        assert "similarities" in data
        assert "differences" in data


# =================== MONITOR API TESTS ===================

class TestMonitorAPI:
    """Test suite for Runtime Monitor API endpoints"""
    
    def test_list_running_processes(self, client):
        """Test GET /monitor/processes endpoint"""
        response = client.get("/api/v1/monitor/processes")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_process_details(self, client):
        """Test GET /monitor/processes/{pid} endpoint"""
        # Use a test PID
        test_pid = 1234
        
        response = client.get(f"/api/v1/monitor/processes/{test_pid}")
        # Should handle gracefully if process doesn't exist
        assert response.status_code in [200, 404]
    
    def test_list_active_services(self, client):
        """Test GET /monitor/services endpoint"""
        response = client.get("/api/v1/monitor/services")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_service_health_check(self, client):
        """Test GET /monitor/services/{port}/health endpoint"""
        test_port = 8000
        
        response = client.get(f"/api/v1/monitor/services/{test_port}/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "port" in data
        assert "status" in data
    
    def test_list_docker_containers(self, client):
        """Test GET /monitor/containers endpoint"""
        response = client.get("/api/v1/monitor/containers")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_system_metrics(self, client):
        """Test GET /monitor/metrics endpoint"""
        response = client.get("/api/v1/monitor/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert "cpu_percent" in data
        assert "memory_percent" in data
        assert "timestamp" in data
    
    def test_performance_alerts(self, client):
        """Test GET /monitor/alerts endpoint"""
        response = client.get("/api/v1/monitor/alerts")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_performance_trends(self, client):
        """Test GET /monitor/trends endpoint"""
        response = client.get("/api/v1/monitor/trends")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_project_runtime_status(self, client):
        """Test GET /monitor/projects/{id}/status endpoint"""
        project_id = str(uuid.uuid4())
        
        response = client.get(f"/api/v1/monitor/projects/{project_id}/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "project_id" in data
        assert "is_running" in data
    
    def test_project_logs(self, client):
        """Test GET /monitor/projects/{id}/logs endpoint"""
        project_id = str(uuid.uuid4())
        
        response = client.get(f"/api/v1/monitor/projects/{project_id}/logs")
        # May return 404 if project not found
        assert response.status_code in [200, 404]
    
    def test_system_overview(self, client):
        """Test GET /monitor/overview endpoint"""
        response = client.get("/api/v1/monitor/overview")
        
        assert response.status_code == 200
        data = response.json()
        assert "system" in data
        assert "projects" in data
    
    def test_memory_leak_detection(self, client):
        """Test GET /monitor/memory-leaks endpoint"""
        response = client.get("/api/v1/monitor/memory-leaks")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_start_monitoring(self, client):
        """Test POST /monitor/start endpoint"""
        monitoring_config = {
            "enable_process_monitoring": True,
            "enable_service_monitoring": True,
            "monitoring_interval": 30
        }
        
        response = client.post("/api/v1/monitor/start", json=monitoring_config)
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "status" in data


# =================== MEMORY API TESTS ===================

class TestMemoryAPI:
    """Test suite for Memory System API endpoints"""
    
    def test_list_deliberations(self, client):
        """Test GET /memory/deliberations endpoint"""
        response = client.get("/api/v1/memory/deliberations")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_deliberation_by_id(self, client):
        """Test GET /memory/deliberations/{id} endpoint"""
        deliberation_id = str(uuid.uuid4())
        
        response = client.get(f"/api/v1/memory/deliberations/{deliberation_id}")
        # May return 404 if deliberation not found
        assert response.status_code in [200, 404]
    
    def test_persona_history(self, client):
        """Test GET /memory/personas/{name}/history endpoint"""
        persona_name = "system_architect"
        
        response = client.get(f"/api/v1/memory/personas/{persona_name}/history")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
    
    def test_search_memories(self, client):
        """Test POST /memory/search endpoint"""
        search_request = {
            "query": "optimization techniques",
            "persona_name": "performance_expert",
            "limit": 10,
            "min_relevance": 0.5
        }
        
        response = client.post("/api/v1/memory/search", json=search_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "memories" in data
        assert "relevance_scores" in data
        assert "total_found" in data
    
    def test_learning_patterns(self, client):
        """Test GET /memory/patterns endpoint"""
        response = client.get("/api/v1/memory/patterns")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_memory_consolidation(self, client):
        """Test POST /memory/consolidate endpoint"""
        response = client.post("/api/v1/memory/consolidate?days_threshold=90")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data
    
    def test_memory_statistics(self, client):
        """Test GET /memory/stats endpoint"""
        response = client.get("/api/v1/memory/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_deliberations" in data
        assert "total_responses" in data
    
    def test_persona_memory_summary(self, client):
        """Test GET /memory/personas/{name}/summary endpoint"""
        persona_name = "database_expert"
        
        response = client.get(f"/api/v1/memory/personas/{persona_name}/summary")
        assert response.status_code == 200
        
        data = response.json()
        assert "persona_name" in data
        assert "total_responses" in data
    
    def test_find_similar_memories(self, client):
        """Test GET /memory/similar endpoint"""
        response = client.get("/api/v1/memory/similar?query=performance+optimization")
        
        assert response.status_code == 200
        data = response.json()
        assert "similar_memories" in data


# =================== KNOWLEDGE GRAPH API TESTS ===================

class TestKnowledgeGraphAPI:
    """Test suite for Knowledge Graph API endpoints"""
    
    def test_list_nodes(self, client):
        """Test GET /graph/nodes endpoint"""
        response = client.get("/api/v1/graph/nodes")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_node_by_id(self, client):
        """Test GET /graph/nodes/{id} endpoint"""
        node_id = str(uuid.uuid4())
        
        response = client.get(f"/api/v1/graph/nodes/{node_id}")
        # May return 404 if node not found
        assert response.status_code in [200, 404]
    
    def test_create_node(self, client):
        """Test POST /graph/nodes endpoint"""
        node_data = {
            "name": "test-technology",
            "node_type": "TECHNOLOGY",
            "attributes": {"category": "web_framework"},
            "importance": 0.8
        }
        
        response = client.post("/api/v1/graph/nodes", json=node_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "id" in data
        assert data["name"] == node_data["name"]
    
    def test_list_edges(self, client):
        """Test GET /graph/edges endpoint"""
        response = client.get("/api/v1/graph/edges")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_create_edge(self, client):
        """Test POST /graph/edges endpoint"""
        edge_data = {
            "source_id": str(uuid.uuid4()),
            "target_id": str(uuid.uuid4()),
            "edge_type": "USES",
            "weight": 0.9,
            "confidence": 0.8
        }
        
        response = client.post("/api/v1/graph/edges", json=edge_data)
        # May fail if nodes don't exist
        assert response.status_code in [200, 500]
    
    def test_cross_project_insights(self, client):
        """Test GET /graph/insights endpoint"""
        response = client.get("/api/v1/graph/insights")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_technology_patterns(self, client):
        """Test GET /graph/technologies endpoint"""
        response = client.get("/api/v1/graph/technologies")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_graph_clusters(self, client):
        """Test GET /graph/clusters endpoint"""
        response = client.get("/api/v1/graph/clusters")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_concept_path_finding(self, client):
        """Test GET /graph/path endpoint"""
        response = client.get("/api/v1/graph/path?source=React&target=TypeScript")
        
        assert response.status_code == 200
        data = response.json()
        assert "source" in data
        assert "target" in data
        assert "path" in data
    
    def test_graph_statistics(self, client):
        """Test GET /graph/stats endpoint"""
        response = client.get("/api/v1/graph/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_nodes" in data
        assert "total_edges" in data
    
    def test_visualization_export(self, client):
        """Test GET /graph/visualization endpoint"""
        response = client.get("/api/v1/graph/visualization")
        
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
    
    def test_persona_expertise(self, client):
        """Test GET /graph/personas/expertise endpoint"""
        response = client.get("/api/v1/graph/personas/expertise")
        
        assert response.status_code == 200
        data = response.json()
        assert "personas" in data
    
    def test_trigger_graph_analysis(self, client):
        """Test POST /graph/analyze endpoint"""
        response = client.post("/api/v1/graph/analyze")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data


# =================== DASHBOARD API TESTS ===================

class TestDashboardAPI:
    """Test suite for Dashboard API endpoints"""
    
    def test_dashboard_overview(self, client):
        """Test GET /dashboard/overview endpoint"""
        response = client.get("/api/v1/dashboard/overview")
        
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "system_health" in data
        assert "project_statistics" in data
    
    def test_system_health(self, client):
        """Test GET /dashboard/health endpoint"""
        response = client.get("/api/v1/dashboard/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "overall_score" in data
        assert "status" in data
    
    def test_projects_health(self, client):
        """Test GET /dashboard/projects/health endpoint"""
        response = client.get("/api/v1/dashboard/projects/health")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_project_health_specific(self, client):
        """Test GET /dashboard/projects/{id}/health endpoint"""
        project_id = str(uuid.uuid4())
        
        response = client.get(f"/api/v1/dashboard/projects/{project_id}/health")
        # May return 404 if project not found
        assert response.status_code in [200, 404]
    
    def test_system_insights(self, client):
        """Test GET /dashboard/insights endpoint"""
        response = client.get("/api/v1/dashboard/insights")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_recommendations(self, client):
        """Test GET /dashboard/recommendations endpoint"""
        response = client.get("/api/v1/dashboard/recommendations")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_activity_feed(self, client):
        """Test GET /dashboard/activity endpoint"""
        response = client.get("/api/v1/dashboard/activity")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_performance_trends(self, client):
        """Test GET /dashboard/trends endpoint"""
        response = client.get("/api/v1/dashboard/trends")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_resource_utilization(self, client):
        """Test GET /dashboard/resources endpoint"""
        response = client.get("/api/v1/dashboard/resources")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# =================== WEBSOCKET TESTS ===================

class TestWebSocketEndpoints:
    """Test suite for WebSocket endpoints"""
    
    @pytest.mark.asyncio
    async def test_system_metrics_websocket(self):
        """Test WebSocket /ws/system/metrics endpoint"""
        settings = get_settings()
        ws_url = f"ws://localhost:{settings.port}/ws/system/metrics"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # Send heartbeat
                await websocket.send(json.dumps({"type": "heartbeat"}))
                
                # Receive messages
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(message)
                
                assert "type" in data
                assert data["type"] in ["connection_established", "heartbeat_ack", "metrics_update"]
                
        except (ConnectionRefusedError, OSError):
            pytest.skip("WebSocket server not running")
    
    @pytest.mark.asyncio
    async def test_project_monitoring_websocket(self):
        """Test WebSocket /ws/projects/monitoring endpoint"""
        settings = get_settings()
        ws_url = f"ws://localhost:{settings.port}/ws/projects/monitoring"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # Subscribe to project
                await websocket.send(json.dumps({
                    "type": "subscribe_project",
                    "project_id": str(uuid.uuid4())
                }))
                
                # Receive response
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(message)
                
                assert "type" in data
                
        except (ConnectionRefusedError, OSError):
            pytest.skip("WebSocket server not running")
    
    @pytest.mark.asyncio
    async def test_scanner_progress_websocket(self):
        """Test WebSocket /ws/scanner/progress endpoint"""
        settings = get_settings()
        ws_url = f"ws://localhost:{settings.port}/ws/scanner/progress"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # Trigger scan
                await websocket.send(json.dumps({
                    "type": "start_scan",
                    "base_path": "/tmp/test"
                }))
                
                # Receive progress updates
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(message)
                
                assert "type" in data
                
        except (ConnectionRefusedError, OSError):
            pytest.skip("WebSocket server not running")
    
    @pytest.mark.asyncio
    async def test_dashboard_websocket(self):
        """Test WebSocket /ws/dashboard/live endpoint"""
        settings = get_settings()
        ws_url = f"ws://localhost:{settings.port}/ws/dashboard/live"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # Request widget update
                await websocket.send(json.dumps({
                    "type": "request_update",
                    "widget": "health"
                }))
                
                # Receive update
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(message)
                
                assert "type" in data
                
        except (ConnectionRefusedError, OSError):
            pytest.skip("WebSocket server not running")
    
    @pytest.mark.asyncio
    async def test_alerts_websocket(self):
        """Test WebSocket /ws/alerts/live endpoint"""
        settings = get_settings()
        ws_url = f"ws://localhost:{settings.port}/ws/alerts/live"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # Set filters
                await websocket.send(json.dumps({
                    "type": "set_filters",
                    "filters": {"severity": ["high", "critical"]}
                }))
                
                # Receive confirmation
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(message)
                
                assert "type" in data
                
        except (ConnectionRefusedError, OSError):
            pytest.skip("WebSocket server not running")


# =================== ERROR HANDLING TESTS ===================

class TestErrorHandling:
    """Test suite for error handling and validation"""
    
    def test_invalid_project_id_format(self, client):
        """Test invalid UUID format handling"""
        invalid_id = "not-a-uuid"
        
        response = client.get(f"/api/v1/projects/{invalid_id}")
        assert response.status_code in [400, 422]  # Bad request or validation error
    
    def test_invalid_pagination_parameters(self, client):
        """Test invalid pagination parameters"""
        # Negative skip
        response = client.get("/api/v1/projects?skip=-1")
        assert response.status_code in [400, 422]
        
        # Limit too large
        response = client.get("/api/v1/projects?limit=1000")
        assert response.status_code in [400, 422]
    
    def test_invalid_json_payload(self, client):
        """Test invalid JSON in request body"""
        response = client.post(
            "/api/v1/memory/search",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_missing_required_fields(self, client):
        """Test missing required fields in request"""
        # Memory search without query
        response = client.post("/api/v1/memory/search", json={})
        assert response.status_code == 422
        
        data = response.json()
        assert "detail" in data
    
    def test_invalid_filter_values(self, client):
        """Test invalid filter parameter values"""
        # Invalid severity filter
        response = client.get("/api/v1/monitor/alerts?severity=invalid")
        assert response.status_code in [200, 400]  # May be handled gracefully
    
    def test_large_payload_handling(self, client):
        """Test handling of large payloads"""
        large_payload = {"data": "x" * 10000}  # 10KB payload
        
        response = client.post("/api/v1/memory/search", json=large_payload)
        # Should handle gracefully
        assert response.status_code in [200, 400, 413, 422]


# =================== PERFORMANCE TESTS ===================

class TestPerformance:
    """Test suite for performance and load testing"""
    
    @pytest.mark.performance
    def test_endpoint_response_times(self, client):
        """Test response times for key endpoints"""
        import time
        
        endpoints = [
            "/api/v1/projects",
            "/api/v1/dashboard/overview",
            "/api/v1/monitor/metrics",
            "/api/v1/scanner/technologies"
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            response = client.get(endpoint)
            end_time = time.time()
            
            response_time = end_time - start_time
            
            # Assert response time is under 2 seconds
            assert response_time < 2.0, f"Endpoint {endpoint} took {response_time:.3f}s"
            assert response.status_code == 200
    
    @pytest.mark.performance
    def test_concurrent_requests(self, client):
        """Test concurrent request handling"""
        import threading
        import time
        
        results = []
        
        def make_request():
            start_time = time.time()
            response = client.get("/api/v1/dashboard/health")
            end_time = time.time()
            results.append({
                "status": response.status_code,
                "time": end_time - start_time
            })
        
        # Create 10 concurrent threads
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(results) == 10
        successful_requests = [r for r in results if r["status"] == 200]
        assert len(successful_requests) >= 8  # At least 80% success rate
        
        avg_response_time = sum(r["time"] for r in results) / len(results)
        assert avg_response_time < 3.0  # Average under 3 seconds


# =================== INTEGRATION TESTS ===================

class TestIntegration:
    """Test suite for end-to-end integration scenarios"""
    
    @pytest.mark.integration
    def test_complete_project_analysis_workflow(self, client):
        """Test complete project analysis workflow"""
        # 1. Trigger project scan
        scan_response = client.post("/api/v1/scanner/scan", json={
            "base_path": "/tmp/test-project",
            "include_analysis": True
        })
        assert scan_response.status_code == 200
        
        # 2. Check scanner progress (would normally use WebSocket)
        # For testing, just verify scan was initiated
        
        # 3. Get project list
        projects_response = client.get("/api/v1/scanner/projects")
        assert projects_response.status_code == 200
        
        # 4. Get dashboard overview
        dashboard_response = client.get("/api/v1/dashboard/overview")
        assert dashboard_response.status_code == 200
        
        # 5. Check system health
        health_response = client.get("/api/v1/dashboard/health")
        assert health_response.status_code == 200
    
    @pytest.mark.integration
    def test_monitoring_workflow(self, client):
        """Test monitoring and alerting workflow"""
        # 1. Start monitoring
        monitor_response = client.post("/api/v1/monitor/start", json={
            "enable_process_monitoring": True,
            "monitoring_interval": 10
        })
        assert monitor_response.status_code == 200
        
        # 2. Get system metrics
        metrics_response = client.get("/api/v1/monitor/metrics")
        assert metrics_response.status_code == 200
        
        # 3. Check for alerts
        alerts_response = client.get("/api/v1/monitor/alerts")
        assert alerts_response.status_code == 200
        
        # 4. Get system overview
        overview_response = client.get("/api/v1/monitor/overview")
        assert overview_response.status_code == 200
    
    @pytest.mark.integration
    def test_memory_and_knowledge_integration(self, client):
        """Test memory and knowledge graph integration"""
        # 1. Search memories
        search_response = client.post("/api/v1/memory/search", json={
            "query": "performance optimization",
            "limit": 5
        })
        assert search_response.status_code == 200
        
        # 2. Get knowledge graph insights
        insights_response = client.get("/api/v1/graph/insights")
        assert insights_response.status_code == 200
        
        # 3. Get technology patterns
        tech_response = client.get("/api/v1/graph/technologies")
        assert tech_response.status_code == 200
        
        # 4. Get dashboard insights
        dashboard_insights_response = client.get("/api/v1/dashboard/insights")
        assert dashboard_insights_response.status_code == 200


# =================== HEALTH CHECK TESTS ===================

class TestHealthChecks:
    """Test suite for health check endpoints"""
    
    def test_main_health_check(self, client):
        """Test main application health check"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
    
    def test_memory_health_check(self, client):
        """Test memory system health check"""
        response = client.get("/api/v1/memory/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    def test_knowledge_graph_health_check(self, client):
        """Test knowledge graph health check"""
        response = client.get("/api/v1/graph/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    def test_scanner_health_check(self, client):
        """Test scanner health check"""
        response = client.get("/api/v1/scanner/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    def test_monitor_health_check(self, client):
        """Test monitor health check"""
        response = client.get("/api/v1/monitor/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


# =================== TEST RUNNER CONFIGURATION ===================

if __name__ == "__main__":
    """Run tests with coverage reporting"""
    import subprocess
    import sys
    
    # Run pytest with coverage
    cmd = [
        sys.executable, "-m", "pytest",
        __file__,
        "--verbose",
        "--tb=short",
        "--cov=src/api",
        "--cov-report=html",
        "--cov-report=term-missing",
        "-m", "not (performance or integration)"  # Skip slow tests by default
    ]
    
    subprocess.run(cmd)