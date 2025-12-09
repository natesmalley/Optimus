"""
API Test Generator
Automatically generates comprehensive test suites from OpenAPI specifications.
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from ...config import logger


class TestType:
    """Test types."""
    UNIT = "unit"
    INTEGRATION = "integration"
    CONTRACT = "contract"
    LOAD = "load"
    SECURITY = "security"


class APITestGenerator:
    """Generate comprehensive test suites for API endpoints."""
    
    def __init__(self, openapi_spec: Dict[str, Any]):
        self.spec = openapi_spec
        self.base_url = self._extract_base_url()
        self.auth_schemes = self._extract_auth_schemes()
        
    def _extract_base_url(self) -> str:
        """Extract base URL from spec."""
        servers = self.spec.get("servers", [])
        if servers:
            return servers[0]["url"]
        return "http://localhost:8000"
    
    def _extract_auth_schemes(self) -> List[str]:
        """Extract authentication schemes."""
        components = self.spec.get("components", {})
        security_schemes = components.get("securitySchemes", {})
        return list(security_schemes.keys())
    
    def generate_pytest_tests(self, output_dir: str = "tests/api") -> Dict[str, str]:
        """Generate pytest test files."""
        test_files = {}
        
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Generate conftest.py
        test_files["conftest.py"] = self._generate_conftest()
        
        # Generate test files for each tag/module
        paths = self.spec.get("paths", {})
        grouped_endpoints = self._group_endpoints_by_tag(paths)
        
        for tag, endpoints in grouped_endpoints.items():
            filename = f"test_{tag}.py"
            test_content = self._generate_test_module(tag, endpoints)
            test_files[filename] = test_content
        
        # Generate common test utilities
        test_files["test_utils.py"] = self._generate_test_utils()
        
        # Generate integration tests
        test_files["test_integration.py"] = self._generate_integration_tests()
        
        # Generate security tests
        test_files["test_security.py"] = self._generate_security_tests()
        
        # Write files to disk
        for filename, content in test_files.items():
            file_path = Path(output_dir) / filename
            with open(file_path, 'w') as f:
                f.write(content)
        
        logger.info(f"Generated {len(test_files)} test files in {output_dir}")
        return test_files
    
    def _generate_conftest(self) -> str:
        """Generate pytest conftest.py file."""
        return f'''"""
Pytest configuration and fixtures for API tests.
Generated from OpenAPI specification.
"""

import pytest
import asyncio
import httpx
from typing import Dict, Any, AsyncGenerator

# Test configuration
BASE_URL = "{self.base_url}"
TIMEOUT = 30.0


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create HTTP client for testing."""
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=TIMEOUT,
        follow_redirects=True
    ) as client:
        yield client


@pytest.fixture(scope="session")
async def auth_token(client: httpx.AsyncClient) -> str:
    """Get authentication token for testing."""
    # This would typically authenticate with test credentials
    # For now, return a mock token
    return "test-token-123"


@pytest.fixture(scope="session")
async def authenticated_client(client: httpx.AsyncClient, auth_token: str) -> httpx.AsyncClient:
    """Create authenticated HTTP client."""
    client.headers.update({{"Authorization": f"Bearer {{auth_token}}"}})
    return client


@pytest.fixture
def sample_project_data() -> Dict[str, Any]:
    """Sample project data for testing."""
    return {{
        "name": "test-project",
        "description": "A test project",
        "repository_url": "https://github.com/test/project",
        "language": "python",
        "framework": "fastapi",
        "tags": ["test", "api"]
    }}


@pytest.fixture
def sample_council_data() -> Dict[str, Any]:
    """Sample council deliberation data for testing."""
    return {{
        "topic": "Should we implement feature X?",
        "context": {{"urgency": "medium", "resources": "available"}},
        "required_personas": ["strategist", "analyst"],
        "priority": 7
    }}


@pytest.fixture
def sample_deployment_data() -> Dict[str, Any]:
    """Sample deployment data for testing."""
    return {{
        "project_id": "test-project-123",
        "environment": "staging",
        "strategy": "blue_green",
        "git_ref": "main",
        "replicas": 2
    }}


class APITestHelper:
    """Helper class for common API testing patterns."""
    
    @staticmethod
    async def assert_valid_response(response: httpx.Response, expected_status: int = 200):
        """Assert response is valid."""
        assert response.status_code == expected_status, f"Expected {{expected_status}}, got {{response.status_code}}: {{response.text}}"
        
        if response.headers.get("content-type", "").startswith("application/json"):
            data = response.json()
            assert isinstance(data, dict), "Response should be valid JSON object"
            return data
        
        return response.text
    
    @staticmethod
    async def assert_error_response(response: httpx.Response, expected_status: int):
        """Assert error response format."""
        assert response.status_code == expected_status
        
        if response.headers.get("content-type", "").startswith("application/json"):
            data = response.json()
            assert "error" in data or "success" in data
            if "success" in data:
                assert data["success"] is False
    
    @staticmethod
    def validate_pagination(data: Dict[str, Any]):
        """Validate pagination response."""
        assert "data" in data
        assert "meta" in data or "pagination" in data
        
        meta = data.get("meta") or data.get("pagination")
        assert "page" in meta
        assert "size" in meta
        assert "total_count" in meta


@pytest.fixture
def api_helper() -> APITestHelper:
    """API test helper fixture."""
    return APITestHelper()
'''
    
    def _group_endpoints_by_tag(self, paths: Dict[str, Any]) -> Dict[str, List[Tuple[str, str, Dict]]]:
        """Group endpoints by OpenAPI tags."""
        grouped = {}
        
        for path, methods in paths.items():
            for method, operation in methods.items():
                if isinstance(operation, dict):
                    tags = operation.get("tags", ["default"])
                    tag = tags[0] if tags else "default"
                    
                    if tag not in grouped:
                        grouped[tag] = []
                    
                    grouped[tag].append((path, method, operation))
        
        return grouped
    
    def _generate_test_module(self, tag: str, endpoints: List[Tuple[str, str, Dict]]) -> str:
        """Generate test module for a specific tag."""
        test_class_name = f"Test{tag.title()}API"
        
        imports = '''"""
Test suite for {tag} API endpoints.
Generated from OpenAPI specification.
"""

import pytest
import httpx
from typing import Dict, Any

from .conftest import APITestHelper

'''.format(tag=tag)
        
        class_header = f'''
class {test_class_name}:
    """Test cases for {tag} endpoints."""
    
'''
        
        test_methods = []
        
        for path, method, operation in endpoints:
            test_method = self._generate_test_method(path, method, operation)
            test_methods.append(test_method)
        
        return imports + class_header + '\n'.join(test_methods)
    
    def _generate_test_method(self, path: str, method: str, operation: Dict[str, Any]) -> str:
        """Generate individual test method."""
        operation_id = operation.get("operationId", f"{method}_{path.replace('/', '_')}")
        method_name = f"test_{operation_id}".replace('-', '_').lower()
        
        # Extract expected responses
        responses = operation.get("responses", {})
        success_codes = [code for code in responses.keys() if code.startswith("2")]
        error_codes = [code for code in responses.keys() if code.startswith(("4", "5"))]
        
        # Generate method signature
        params = ["self", "authenticated_client: httpx.AsyncClient", "api_helper: APITestHelper"]
        
        # Add fixtures for request body
        if "requestBody" in operation:
            if "project" in path.lower():
                params.append("sample_project_data: Dict[str, Any]")
            elif "council" in path.lower():
                params.append("sample_council_data: Dict[str, Any]")
            elif "deployment" in path.lower():
                params.append("sample_deployment_data: Dict[str, Any]")
        
        method_signature = f"    async def {method_name}({', '.join(params)}):"
        
        # Generate test body
        test_body = self._generate_test_body(path, method, operation, success_codes, error_codes)
        
        docstring = f'''        """Test {operation.get("summary", f"{method.upper()} {path}")}."""'''
        
        return f'''
{method_signature}
{docstring}
{test_body}
'''
    
    def _generate_test_body(self, path: str, method: str, operation: Dict[str, Any], 
                           success_codes: List[str], error_codes: List[str]) -> str:
        """Generate test method body."""
        lines = []
        
        # Prepare request data
        if "requestBody" in operation:
            if "project" in path.lower():
                lines.append("        request_data = sample_project_data")
            elif "council" in path.lower():
                lines.append("        request_data = sample_council_data")
            elif "deployment" in path.lower():
                lines.append("        request_data = sample_deployment_data")
            else:
                lines.append("        request_data = {}")
        
        # Prepare URL with path parameters
        url_line = f'        url = "{path}"'
        if "{" in path:
            lines.append("        # Replace path parameters with test values")
            test_path = path
            # Simple replacement for common path parameters
            test_path = test_path.replace("{id}", "test-id-123")
            test_path = test_path.replace("{project_id}", "test-project-123")
            test_path = test_path.replace("{deliberation_id}", "test-delib-123")
            test_path = test_path.replace("{deployment_id}", "test-deploy-123")
            url_line = f'        url = "{test_path}"'
        
        lines.append(url_line)
        lines.append("")
        
        # Make request
        if method.upper() in ["GET", "DELETE"]:
            lines.append(f'        response = await authenticated_client.{method.lower()}(url)')
        else:
            if "requestBody" in operation:
                lines.append(f'        response = await authenticated_client.{method.lower()}(url, json=request_data)')
            else:
                lines.append(f'        response = await authenticated_client.{method.lower()}(url)')
        
        lines.append("")
        
        # Assert successful response
        expected_status = success_codes[0] if success_codes else "200"
        lines.append(f"        # Test successful response")
        lines.append(f"        await api_helper.assert_valid_response(response, {expected_status})")
        
        # Add specific assertions based on endpoint type
        if method.upper() == "GET":
            if "list" in operation.get("operationId", "").lower() or "/projects" in path:
                lines.append("")
                lines.append("        data = response.json()")
                lines.append("        if 'meta' in data or 'pagination' in data:")
                lines.append("            api_helper.validate_pagination(data)")
        
        if method.upper() == "POST":
            lines.append("")
            lines.append("        data = response.json()")
            lines.append("        assert 'data' in data or 'id' in data")
        
        return '\n'.join(lines)
    
    def _generate_test_utils(self) -> str:
        """Generate test utilities."""
        return '''"""
Utility functions for API testing.
"""

import random
import string
from typing import Dict, Any
import httpx


class TestDataFactory:
    """Factory for generating test data."""
    
    @staticmethod
    def random_string(length: int = 8) -> str:
        """Generate random string."""
        return ''.join(random.choices(string.ascii_lowercase, k=length))
    
    @staticmethod
    def create_project_data(**overrides) -> Dict[str, Any]:
        """Create test project data."""
        data = {
            "name": f"test-project-{TestDataFactory.random_string()}",
            "description": "Test project description",
            "repository_url": "https://github.com/test/repo",
            "language": "python",
            "framework": "fastapi",
            "tags": ["test"]
        }
        data.update(overrides)
        return data
    
    @staticmethod
    def create_council_data(**overrides) -> Dict[str, Any]:
        """Create test council deliberation data."""
        data = {
            "topic": f"Test topic {TestDataFactory.random_string()}?",
            "context": {"test": True},
            "required_personas": ["strategist"],
            "priority": random.randint(1, 10)
        }
        data.update(overrides)
        return data
    
    @staticmethod
    def create_deployment_data(project_id: str = None, **overrides) -> Dict[str, Any]:
        """Create test deployment data."""
        data = {
            "project_id": project_id or f"test-project-{TestDataFactory.random_string()}",
            "environment": "staging", 
            "strategy": "rolling",
            "git_ref": "main",
            "replicas": 1
        }
        data.update(overrides)
        return data


async def wait_for_async_operation(
    client: httpx.AsyncClient,
    operation_url: str,
    max_attempts: int = 30,
    wait_seconds: float = 1.0
) -> Dict[str, Any]:
    """Wait for async operation to complete."""
    for _ in range(max_attempts):
        response = await client.get(operation_url)
        data = response.json()
        
        status = data.get("status", "")
        if status in ["completed", "failed", "cancelled"]:
            return data
        
        await asyncio.sleep(wait_seconds)
    
    raise TimeoutError(f"Operation did not complete within {max_attempts * wait_seconds} seconds")


class MockWebSocketClient:
    """Mock WebSocket client for testing."""
    
    def __init__(self):
        self.messages = []
        self.connected = False
    
    async def connect(self, url: str):
        """Mock WebSocket connection."""
        self.connected = True
    
    async def send(self, message: Dict[str, Any]):
        """Mock send message."""
        self.messages.append(message)
    
    async def receive(self) -> Dict[str, Any]:
        """Mock receive message."""
        if self.messages:
            return self.messages.pop(0)
        return {"type": "ping"}
    
    async def disconnect(self):
        """Mock disconnect."""
        self.connected = False
'''
    
    def _generate_integration_tests(self) -> str:
        """Generate integration test suite."""
        return '''"""
Integration tests for API workflows.
Tests complete workflows across multiple endpoints.
"""

import pytest
import httpx
from typing import Dict, Any

from .test_utils import TestDataFactory, wait_for_async_operation
from .conftest import APITestHelper


class TestAPIWorkflows:
    """Test complete API workflows."""
    
    async def test_project_lifecycle(self, authenticated_client: httpx.AsyncClient, api_helper: APITestHelper):
        """Test complete project lifecycle."""
        # 1. Create project
        project_data = TestDataFactory.create_project_data()
        response = await authenticated_client.post("/api/v1/projects", json=project_data)
        await api_helper.assert_valid_response(response, 201)
        
        project = response.json()["data"]
        project_id = project["id"]
        
        try:
            # 2. Get project
            response = await authenticated_client.get(f"/api/v1/projects/{project_id}")
            await api_helper.assert_valid_response(response)
            
            # 3. Update project
            update_data = {"description": "Updated description"}
            response = await authenticated_client.put(f"/api/v1/projects/{project_id}", json=update_data)
            await api_helper.assert_valid_response(response)
            
            # 4. Start orchestration
            orchestration_data = {
                "project_id": project_id,
                "action": "start",
                "params": {"environment": "development"}
            }
            response = await authenticated_client.post("/api/v1/orchestration/requests", json=orchestration_data)
            await api_helper.assert_valid_response(response, 202)
            
            # 5. Monitor orchestration
            request_id = response.json()["data"]["request_id"]
            operation_data = await wait_for_async_operation(
                authenticated_client,
                f"/api/v1/orchestration/requests/{request_id}/status"
            )
            
            assert operation_data["status"] in ["completed", "failed"]
            
        finally:
            # Cleanup: Delete project
            await authenticated_client.delete(f"/api/v1/projects/{project_id}")
    
    async def test_council_deliberation_workflow(self, authenticated_client: httpx.AsyncClient, api_helper: APITestHelper):
        """Test council deliberation workflow."""
        # 1. Start deliberation
        council_data = TestDataFactory.create_council_data()
        response = await authenticated_client.post("/api/v1/council/deliberations", json=council_data)
        await api_helper.assert_valid_response(response, 202)
        
        deliberation = response.json()["data"] 
        deliberation_id = deliberation["deliberation_id"]
        
        try:
            # 2. Monitor deliberation progress
            response = await authenticated_client.get(f"/api/v1/council/deliberations/{deliberation_id}/status")
            await api_helper.assert_valid_response(response)
            
            # 3. Get persona responses (if available)
            response = await authenticated_client.get(f"/api/v1/council/deliberations/{deliberation_id}/responses")
            await api_helper.assert_valid_response(response)
            
            # 4. Wait for completion (with timeout)
            deliberation_result = await wait_for_async_operation(
                authenticated_client,
                f"/api/v1/council/deliberations/{deliberation_id}/status",
                max_attempts=60,  # Longer timeout for deliberations
                wait_seconds=2.0
            )
            
            assert deliberation_result["status"] in ["completed", "failed", "timeout"]
            
        except Exception:
            # Cancel deliberation if something goes wrong
            await authenticated_client.post(f"/api/v1/council/deliberations/{deliberation_id}/cancel")
            raise
    
    async def test_deployment_workflow(self, authenticated_client: httpx.AsyncClient, api_helper: APITestHelper):
        """Test deployment workflow."""
        # 1. Create project first
        project_data = TestDataFactory.create_project_data()
        response = await authenticated_client.post("/api/v1/projects", json=project_data)
        project = response.json()["data"]
        project_id = project["id"]
        
        try:
            # 2. Start deployment
            deployment_data = TestDataFactory.create_deployment_data(project_id=project_id)
            response = await authenticated_client.post("/api/v1/deployments", json=deployment_data)
            await api_helper.assert_valid_response(response, 202)
            
            deployment = response.json()["data"]
            deployment_id = deployment["deployment_id"]
            
            # 3. Monitor deployment
            deployment_result = await wait_for_async_operation(
                authenticated_client,
                f"/api/v1/deployments/{deployment_id}/status",
                max_attempts=120,  # Longer timeout for deployments
                wait_seconds=5.0
            )
            
            assert deployment_result["status"] in ["completed", "failed", "cancelled"]
            
            # 4. Get deployment logs
            response = await authenticated_client.get(f"/api/v1/deployments/{deployment_id}/logs")
            await api_helper.assert_valid_response(response)
            
        finally:
            # Cleanup
            await authenticated_client.delete(f"/api/v1/projects/{project_id}")
    
    async def test_backup_and_restore_workflow(self, authenticated_client: httpx.AsyncClient, api_helper: APITestHelper):
        """Test backup and restore workflow."""
        # 1. Create project
        project_data = TestDataFactory.create_project_data()
        response = await authenticated_client.post("/api/v1/projects", json=project_data)
        project = response.json()["data"]
        project_id = project["id"]
        
        try:
            # 2. Create backup
            backup_data = {
                "project_id": project_id,
                "backup_type": "full",
                "compression": True
            }
            response = await authenticated_client.post("/api/v1/backups", json=backup_data)
            await api_helper.assert_valid_response(response, 202)
            
            backup = response.json()["data"]
            backup_id = backup["backup_id"]
            
            # 3. Wait for backup completion
            backup_result = await wait_for_async_operation(
                authenticated_client,
                f"/api/v1/backups/{backup_id}/status"
            )
            
            assert backup_result["status"] == "completed"
            
            # 4. Test restore
            restore_data = {
                "backup_id": backup_id,
                "destination_path": f"/tmp/restore-{project_id}"
            }
            response = await authenticated_client.post("/api/v1/backups/restore", json=restore_data)
            await api_helper.assert_valid_response(response, 202)
            
            # 5. Clean up backup
            await authenticated_client.delete(f"/api/v1/backups/{backup_id}")
            
        finally:
            # Cleanup
            await authenticated_client.delete(f"/api/v1/projects/{project_id}")
'''
    
    def _generate_security_tests(self) -> str:
        """Generate security test suite."""
        return '''"""
Security tests for API endpoints.
Tests authentication, authorization, and security vulnerabilities.
"""

import pytest
import httpx
from typing import Dict, Any

from .test_utils import TestDataFactory
from .conftest import APITestHelper


class TestAPISecurity:
    """Security tests for API."""
    
    async def test_unauthenticated_access_denied(self, client: httpx.AsyncClient):
        """Test that unauthenticated requests are denied."""
        protected_endpoints = [
            ("GET", "/api/v1/projects"),
            ("POST", "/api/v1/projects"),
            ("GET", "/api/v1/council/deliberations"),
            ("POST", "/api/v1/orchestration/requests"),
        ]
        
        for method, endpoint in protected_endpoints:
            response = await client.request(method, endpoint)
            assert response.status_code == 401, f"{method} {endpoint} should require authentication"
    
    async def test_invalid_token_rejected(self, client: httpx.AsyncClient):
        """Test that invalid tokens are rejected."""
        headers = {"Authorization": "Bearer invalid-token"}
        
        response = await client.get("/api/v1/projects", headers=headers)
        assert response.status_code == 401
        
        data = response.json()
        assert "error" in data
    
    async def test_malformed_token_rejected(self, client: httpx.AsyncClient):
        """Test that malformed tokens are rejected."""
        malformed_tokens = [
            "Bearer",  # No token
            "Bearer ",  # Empty token
            "Invalid token-format",  # Wrong format
            "Bearer not.a.jwt",  # Invalid JWT
        ]
        
        for token in malformed_tokens:
            headers = {"Authorization": token}
            response = await client.get("/api/v1/projects", headers=headers)
            assert response.status_code == 401
    
    async def test_sql_injection_protection(self, authenticated_client: httpx.AsyncClient):
        """Test protection against SQL injection."""
        malicious_inputs = [
            "'; DROP TABLE projects; --",
            "1' OR '1'='1",
            "admin'; DELETE FROM users; --",
            "' UNION SELECT * FROM users --"
        ]
        
        for malicious_input in malicious_inputs:
            # Test in query parameters
            response = await authenticated_client.get(f"/api/v1/projects?search={malicious_input}")
            assert response.status_code in [200, 400, 422], "Should not cause server error"
            
            # Test in request body
            project_data = TestDataFactory.create_project_data(name=malicious_input)
            response = await authenticated_client.post("/api/v1/projects", json=project_data)
            assert response.status_code in [201, 400, 422], "Should not cause server error"
    
    async def test_xss_protection(self, authenticated_client: httpx.AsyncClient):
        """Test protection against XSS attacks."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//"
        ]
        
        for payload in xss_payloads:
            project_data = TestDataFactory.create_project_data(
                name=f"test-{payload}",
                description=payload
            )
            
            response = await authenticated_client.post("/api/v1/projects", json=project_data)
            
            if response.status_code == 201:
                # If created, verify the payload is properly escaped
                project = response.json()["data"]
                project_id = project["id"]
                
                # Get the project back
                response = await authenticated_client.get(f"/api/v1/projects/{project_id}")
                data = response.json()["data"]
                
                # Verify dangerous characters are escaped or removed
                assert "<script>" not in data.get("description", "")
                assert "javascript:" not in data.get("description", "")
                
                # Cleanup
                await authenticated_client.delete(f"/api/v1/projects/{project_id}")
    
    async def test_rate_limiting(self, authenticated_client: httpx.AsyncClient):
        """Test rate limiting protection."""
        # Make many requests quickly
        responses = []
        for i in range(150):  # Exceed typical rate limits
            response = await authenticated_client.get("/api/v1/projects")
            responses.append(response.status_code)
            
            # Stop if we hit rate limit
            if response.status_code == 429:
                break
        
        # Should eventually hit rate limit
        assert 429 in responses, "Rate limiting should be enforced"
    
    async def test_input_validation(self, authenticated_client: httpx.AsyncClient, api_helper: APITestHelper):
        """Test input validation and sanitization."""
        # Test oversized inputs
        large_string = "x" * 10000
        project_data = TestDataFactory.create_project_data(
            name=large_string,
            description=large_string
        )
        
        response = await authenticated_client.post("/api/v1/projects", json=project_data)
        assert response.status_code in [400, 422], "Should reject oversized inputs"
        
        # Test invalid data types
        invalid_data = {
            "name": 12345,  # Should be string
            "description": ["array", "instead", "of", "string"],
            "tags": "string instead of array"
        }
        
        response = await authenticated_client.post("/api/v1/projects", json=invalid_data)
        assert response.status_code in [400, 422], "Should reject invalid data types"
    
    async def test_path_traversal_protection(self, authenticated_client: httpx.AsyncClient):
        """Test protection against path traversal attacks."""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2f",  # URL encoded
            "....//....//....//etc/passwd"
        ]
        
        for path in malicious_paths:
            # Test in URL path (where applicable)
            response = await authenticated_client.get(f"/api/v1/projects/{path}")
            assert response.status_code in [400, 404, 422], "Should not allow path traversal"
            
            # Test in request body
            backup_data = {
                "project_id": "test-project",
                "backup_type": "files",
                "include_patterns": [path]
            }
            
            response = await authenticated_client.post("/api/v1/backups", json=backup_data)
            assert response.status_code in [400, 422], "Should not allow path traversal in patterns"
    
    async def test_cors_headers(self, client: httpx.AsyncClient):
        """Test CORS headers are properly configured."""
        response = await client.options("/api/v1/projects")
        
        # Check CORS headers
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers
        assert "Access-Control-Allow-Headers" in response.headers
'''
    
    def generate_load_tests(self, output_dir: str = "tests/load") -> Dict[str, str]:
        """Generate load test scripts using locust."""
        test_files = {}
        
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Generate locustfile
        test_files["locustfile.py"] = self._generate_locustfile()
        
        # Generate load test configuration
        test_files["load_test_config.py"] = self._generate_load_test_config()
        
        # Write files
        for filename, content in test_files.items():
            file_path = Path(output_dir) / filename
            with open(file_path, 'w') as f:
                f.write(content)
        
        return test_files
    
    def _generate_locustfile(self) -> str:
        """Generate Locust load test file."""
        return f'''"""
Load tests for Optimus API using Locust.
Generated from OpenAPI specification.
"""

import json
import random
from locust import HttpUser, task, between


class OptimusAPIUser(HttpUser):
    """Load test user for Optimus API."""
    
    wait_time = between(1, 5)  # Wait 1-5 seconds between requests
    
    def on_start(self):
        """Called when user starts."""
        # Authenticate
        self.auth_token = self.authenticate()
        self.headers = {{"Authorization": f"Bearer {{self.auth_token}}"}}
    
    def authenticate(self):
        """Authenticate and get token."""
        # In a real scenario, you'd authenticate properly
        return "test-load-token"
    
    @task(3)
    def list_projects(self):
        """List projects (high frequency)."""
        with self.client.get("/api/v1/projects", headers=self.headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status {{response.status_code}}")
    
    @task(2)
    def get_project_details(self):
        """Get project details (medium frequency)."""
        project_id = f"test-project-{{random.randint(1, 100)}}"
        with self.client.get(f"/api/v1/projects/{{project_id}}", headers=self.headers, catch_response=True) as response:
            if response.status_code in [200, 404]:  # 404 is expected for non-existent projects
                response.success()
            else:
                response.failure(f"Got status {{response.status_code}}")
    
    @task(1)
    def create_project(self):
        """Create project (low frequency)."""
        project_data = {{
            "name": f"load-test-project-{{random.randint(1, 10000)}}",
            "description": "Load test project",
            "language": random.choice(["python", "javascript", "java", "go"]),
            "framework": random.choice(["fastapi", "express", "spring", "gin"])
        }}
        
        with self.client.post("/api/v1/projects", json=project_data, headers=self.headers, catch_response=True) as response:
            if response.status_code in [201, 409]:  # 409 for conflicts is acceptable
                response.success()
                
                # Try to delete the created project
                if response.status_code == 201:
                    project_id = response.json().get("data", {{}}).get("id")
                    if project_id:
                        self.client.delete(f"/api/v1/projects/{{project_id}}", headers=self.headers)
            else:
                response.failure(f"Got status {{response.status_code}}")
    
    @task(1)
    def get_metrics(self):
        """Get system metrics (low frequency)."""
        with self.client.get("/api/v1/metrics/system", headers=self.headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status {{response.status_code}}")
    
    @task(1)
    def start_council_deliberation(self):
        """Start council deliberation (low frequency)."""
        deliberation_data = {{
            "topic": f"Load test question {{random.randint(1, 1000)}}?",
            "context": {{"test": True}},
            "priority": random.randint(1, 10)
        }}
        
        with self.client.post("/api/v1/council/deliberations", json=deliberation_data, headers=self.headers, catch_response=True) as response:
            if response.status_code in [202, 429]:  # 429 for rate limiting is acceptable
                response.success()
            else:
                response.failure(f"Got status {{response.status_code}}")


class AdminUser(HttpUser):
    """Admin user with different usage patterns."""
    
    weight = 1  # Less frequent than regular users
    wait_time = between(10, 30)
    
    def on_start(self):
        self.auth_token = "admin-token"
        self.headers = {{"Authorization": f"Bearer {{self.auth_token}}"}}
    
    @task
    def admin_dashboard(self):
        """Access admin dashboard."""
        with self.client.get("/api/v1/dashboard/admin", headers=self.headers, catch_response=True) as response:
            if response.status_code in [200, 403]:  # 403 for unauthorized access
                response.success()
            else:
                response.failure(f"Got status {{response.status_code}}")
    
    @task
    def system_health(self):
        """Check system health."""
        with self.client.get("/api/v1/monitoring/health", headers=self.headers, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status {{response.status_code}}")
'''
    
    def _generate_load_test_config(self) -> str:
        """Generate load test configuration."""
        return '''"""
Load test configuration and utilities.
"""

# Load test scenarios
SCENARIOS = {
    "light": {
        "users": 10,
        "spawn_rate": 2,
        "duration": "5m"
    },
    "normal": {
        "users": 50,
        "spawn_rate": 5,
        "duration": "10m"
    },
    "heavy": {
        "users": 200,
        "spawn_rate": 10,
        "duration": "15m"
    },
    "stress": {
        "users": 500,
        "spawn_rate": 20,
        "duration": "10m"
    }
}

# Performance thresholds
PERFORMANCE_THRESHOLDS = {
    "response_time_95th": 2000,  # 2 seconds
    "response_time_99th": 5000,  # 5 seconds
    "error_rate": 0.01,  # 1%
    "requests_per_second": 100
}

# Commands to run different scenarios
COMMANDS = {
    "light": "locust --headless -u 10 -r 2 -t 5m --host=http://localhost:8000",
    "normal": "locust --headless -u 50 -r 5 -t 10m --host=http://localhost:8000",
    "heavy": "locust --headless -u 200 -r 10 -t 15m --host=http://localhost:8000",
    "stress": "locust --headless -u 500 -r 20 -t 10m --host=http://localhost:8000"
}
'''
    
    def export_all_tests(self, output_dir: str = "tests/generated"):
        """Export all test types."""
        # Generate pytest tests
        pytest_tests = self.generate_pytest_tests(f"{output_dir}/api")
        
        # Generate load tests
        load_tests = self.generate_load_tests(f"{output_dir}/load")
        
        logger.info(f"Exported all tests to {output_dir}")
        return {
            "pytest_tests": pytest_tests,
            "load_tests": load_tests
        }


def generate_test_suite(openapi_spec: Dict[str, Any], output_dir: str = "tests") -> Dict[str, Any]:
    """Generate complete test suite from OpenAPI specification."""
    generator = APITestGenerator(openapi_spec)
    return generator.export_all_tests(output_dir)
'''