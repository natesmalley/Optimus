"""
OpenAPI/Swagger Documentation Generator
Generates comprehensive API documentation with examples and schemas.
"""

import json
import yaml
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.models import OpenAPI, Info, Server, Contact, License, Tag, ExternalDocumentation

from ...config import get_settings, logger


class DocumentationLevel(str, Enum):
    """Documentation detail levels."""
    BASIC = "basic"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"


class OpenAPIGenerator:
    """Advanced OpenAPI specification generator."""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.settings = get_settings()
        self.custom_schemas = {}
        self.examples = {}
        
    def generate_spec(self, level: DocumentationLevel = DocumentationLevel.STANDARD) -> Dict[str, Any]:
        """Generate OpenAPI specification."""
        try:
            # Get base OpenAPI spec from FastAPI
            openapi_spec = get_openapi(
                title="Optimus API",
                version=self.settings.app_version,
                description=self._get_api_description(),
                routes=self.app.routes,
            )
            
            # Enhance the specification
            self._enhance_info(openapi_spec, level)
            self._add_servers(openapi_spec)
            self._add_tags(openapi_spec)
            self._enhance_paths(openapi_spec, level)
            self._add_security_schemes(openapi_spec)
            self._add_custom_schemas(openapi_spec)
            self._add_examples(openapi_spec, level)
            
            if level == DocumentationLevel.COMPREHENSIVE:
                self._add_webhooks(openapi_spec)
                self._add_callbacks(openapi_spec)
            
            return openapi_spec
            
        except Exception as e:
            logger.error(f"Error generating OpenAPI spec: {e}")
            raise
    
    def _get_api_description(self) -> str:
        """Get comprehensive API description."""
        return """
# Optimus API

The Optimus API provides comprehensive project orchestration and management capabilities powered by AI.

## Features

- **Project Management**: Discover, monitor, and orchestrate development projects
- **Council of Minds**: AI-powered decision making with multiple personas
- **Real-time Monitoring**: Live metrics, alerts, and performance tracking
- **Automated Deployment**: Intelligent deployment pipelines with rollback support
- **Backup & Recovery**: Automated backup management with restore capabilities
- **WebSocket Support**: Real-time updates and notifications

## Authentication

The API supports multiple authentication methods:
- JWT Bearer tokens for user sessions
- API Keys for programmatic access
- OAuth2 (coming soon)

## Rate Limiting

API endpoints are rate limited to ensure fair usage:
- 100 requests per minute for authenticated users
- 20 requests per minute for unauthenticated requests
- Higher limits available for premium tiers

## Error Handling

The API uses standard HTTP status codes and provides detailed error responses:
- `4xx` - Client errors (validation, authentication, etc.)
- `5xx` - Server errors (internal errors, service unavailable, etc.)

All error responses include:
- Error message and code
- Request ID for tracking
- Suggested fixes when applicable

## Webhooks

Subscribe to real-time events via webhooks:
- Project status changes
- Deployment events
- System alerts
- Council deliberation results

## SDKs and Libraries

Official SDKs available for:
- Python
- Node.js
- Go
- Rust

## Support

- Documentation: https://docs.optimus.dev
- GitHub: https://github.com/optimus/optimus
- Support: support@optimus.dev
"""
    
    def _enhance_info(self, spec: Dict[str, Any], level: DocumentationLevel):
        """Enhance API info section."""
        info = spec.get("info", {})
        
        # Basic info
        info.update({
            "title": "Optimus API",
            "version": self.settings.app_version,
            "description": self._get_api_description(),
            "termsOfService": "https://optimus.dev/terms",
            "contact": {
                "name": "Optimus API Support",
                "url": "https://optimus.dev/support",
                "email": "api-support@optimus.dev"
            },
            "license": {
                "name": "MIT",
                "url": "https://opensource.org/licenses/MIT"
            }
        })
        
        if level == DocumentationLevel.COMPREHENSIVE:
            info["x-logo"] = {
                "url": "https://optimus.dev/logo.png",
                "altText": "Optimus Logo"
            }
            info["x-api-id"] = "optimus-api"
            info["x-audience"] = "developers"
        
        spec["info"] = info
    
    def _add_servers(self, spec: Dict[str, Any]):
        """Add server configurations."""
        servers = [
            {
                "url": f"http://localhost:{self.settings.api_port}",
                "description": "Development server"
            },
            {
                "url": "https://api.optimus.dev",
                "description": "Production server"
            },
            {
                "url": "https://staging-api.optimus.dev",
                "description": "Staging server"
            }
        ]
        
        # Add variables for configurable servers
        servers[0]["variables"] = {
            "port": {
                "default": str(self.settings.api_port),
                "description": "API port"
            }
        }
        
        spec["servers"] = servers
    
    def _add_tags(self, spec: Dict[str, Any]):
        """Add API tags for organization."""
        tags = [
            {
                "name": "projects",
                "description": "Project management and discovery",
                "externalDocs": {
                    "description": "Project Management Guide",
                    "url": "https://docs.optimus.dev/projects"
                }
            },
            {
                "name": "council",
                "description": "Council of Minds AI deliberation",
                "externalDocs": {
                    "description": "Council Guide",
                    "url": "https://docs.optimus.dev/council"
                }
            },
            {
                "name": "orchestration",
                "description": "Project orchestration and lifecycle management"
            },
            {
                "name": "deployment",
                "description": "Deployment pipelines and management"
            },
            {
                "name": "monitoring",
                "description": "System monitoring and metrics"
            },
            {
                "name": "resources",
                "description": "Resource monitoring and management"
            },
            {
                "name": "backup",
                "description": "Backup and restore operations"
            },
            {
                "name": "auth",
                "description": "Authentication and authorization"
            },
            {
                "name": "websocket",
                "description": "Real-time WebSocket connections"
            }
        ]
        
        spec["tags"] = tags
    
    def _enhance_paths(self, spec: Dict[str, Any], level: DocumentationLevel):
        """Enhance path definitions."""
        paths = spec.get("paths", {})
        
        for path, methods in paths.items():
            for method, operation in methods.items():
                if isinstance(operation, dict):
                    self._enhance_operation(operation, path, method, level)
        
        spec["paths"] = paths
    
    def _enhance_operation(self, operation: Dict[str, Any], path: str, method: str, level: DocumentationLevel):
        """Enhance individual operation."""
        # Add operation ID if missing
        if "operationId" not in operation:
            operation_id = self._generate_operation_id(path, method)
            operation["operationId"] = operation_id
        
        # Add comprehensive responses
        self._add_response_examples(operation, level)
        
        # Add request examples
        if level in [DocumentationLevel.STANDARD, DocumentationLevel.COMPREHENSIVE]:
            self._add_request_examples(operation, path, method)
        
        # Add rate limiting info
        if "x-rate-limit" not in operation:
            operation["x-rate-limit"] = self._get_rate_limit_info(path)
        
        # Add caching info
        if method.upper() == "GET":
            operation["x-cache-ttl"] = self._get_cache_ttl(path)
        
        if level == DocumentationLevel.COMPREHENSIVE:
            # Add detailed metadata
            operation["x-code-samples"] = self._generate_code_samples(path, method)
            operation["x-internal"] = self._is_internal_endpoint(path)
    
    def _generate_operation_id(self, path: str, method: str) -> str:
        """Generate operation ID from path and method."""
        # Clean path and create camelCase operation ID
        path_parts = [part for part in path.split('/') if part and not part.startswith('{')]
        operation_name = method.lower() + ''.join(part.capitalize() for part in path_parts)
        return operation_name
    
    def _add_response_examples(self, operation: Dict[str, Any], level: DocumentationLevel):
        """Add response examples."""
        responses = operation.get("responses", {})
        
        # Add standard response examples
        for status_code, response in responses.items():
            if isinstance(response, dict) and "content" in response:
                content = response["content"]
                
                for media_type, media_info in content.items():
                    if media_type == "application/json":
                        if "examples" not in media_info:
                            media_info["examples"] = {}
                        
                        # Add example based on status code
                        if status_code == "200":
                            media_info["examples"]["success"] = {
                                "summary": "Successful response",
                                "value": self._get_success_example(operation)
                            }
                        elif status_code.startswith("4"):
                            media_info["examples"]["error"] = {
                                "summary": "Client error",
                                "value": self._get_error_example(status_code)
                            }
                        elif status_code.startswith("5"):
                            media_info["examples"]["server_error"] = {
                                "summary": "Server error", 
                                "value": self._get_server_error_example()
                            }
    
    def _add_request_examples(self, operation: Dict[str, Any], path: str, method: str):
        """Add request body examples."""
        if "requestBody" in operation:
            request_body = operation["requestBody"]
            if "content" in request_body:
                content = request_body["content"]
                
                for media_type, media_info in content.items():
                    if media_type == "application/json" and "examples" not in media_info:
                        media_info["examples"] = {
                            "example": {
                                "summary": "Request example",
                                "value": self._get_request_example(path, method)
                            }
                        }
    
    def _get_success_example(self, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Get success response example."""
        operation_id = operation.get("operationId", "")
        
        if "project" in operation_id.lower():
            return {
                "success": True,
                "data": {
                    "id": "proj-123",
                    "name": "sample-project",
                    "status": "active",
                    "created_at": "2023-12-01T10:00:00Z"
                },
                "timestamp": "2023-12-01T10:00:00Z",
                "request_id": "req-456"
            }
        elif "council" in operation_id.lower():
            return {
                "success": True,
                "data": {
                    "deliberation_id": "delib-789",
                    "topic": "Should we implement feature X?",
                    "status": "completed",
                    "consensus": {
                        "decision": "Yes, implement with safeguards",
                        "confidence": 0.85
                    }
                },
                "timestamp": "2023-12-01T10:00:00Z"
            }
        else:
            return {
                "success": True,
                "data": {},
                "timestamp": "2023-12-01T10:00:00Z",
                "request_id": "req-123"
            }
    
    def _get_error_example(self, status_code: str) -> Dict[str, Any]:
        """Get error response example."""
        error_messages = {
            "400": "Invalid request parameters",
            "401": "Authentication required",
            "403": "Insufficient permissions",
            "404": "Resource not found",
            "422": "Validation error",
            "429": "Rate limit exceeded"
        }
        
        return {
            "success": False,
            "error": error_messages.get(status_code, "Client error"),
            "error_code": f"ERR_{status_code}",
            "timestamp": "2023-12-01T10:00:00Z",
            "request_id": "req-123",
            "help_url": "https://docs.optimus.dev/errors"
        }
    
    def _get_server_error_example(self) -> Dict[str, Any]:
        """Get server error response example."""
        return {
            "success": False,
            "error": "Internal server error",
            "error_code": "ERR_INTERNAL",
            "timestamp": "2023-12-01T10:00:00Z",
            "request_id": "req-123"
        }
    
    def _get_request_example(self, path: str, method: str) -> Dict[str, Any]:
        """Get request body example."""
        if "/projects" in path and method.upper() == "POST":
            return {
                "name": "my-awesome-project",
                "description": "An awesome project",
                "repository_url": "https://github.com/user/project",
                "language": "python",
                "framework": "fastapi",
                "tags": ["web", "api"]
            }
        elif "/council" in path and method.upper() == "POST":
            return {
                "topic": "Should we implement automatic scaling?",
                "context": {
                    "current_load": "high",
                    "available_resources": "limited"
                },
                "required_personas": ["strategist", "economist", "guardian"],
                "priority": 8
            }
        elif "/deployment" in path and method.upper() == "POST":
            return {
                "project_id": "proj-123",
                "environment": "staging",
                "strategy": "blue_green",
                "git_ref": "v1.2.3",
                "replicas": 3
            }
        else:
            return {}
    
    def _get_rate_limit_info(self, path: str) -> Dict[str, Any]:
        """Get rate limit information for path."""
        if "/council" in path:
            return {"requests_per_minute": 30, "burst": 10}
        elif "/projects" in path:
            return {"requests_per_minute": 100, "burst": 20}
        else:
            return {"requests_per_minute": 60, "burst": 15}
    
    def _get_cache_ttl(self, path: str) -> int:
        """Get cache TTL for path."""
        if "/projects" in path:
            return 300  # 5 minutes
        elif "/metrics" in path:
            return 30   # 30 seconds
        else:
            return 60   # 1 minute
    
    def _generate_code_samples(self, path: str, method: str) -> List[Dict[str, Any]]:
        """Generate code samples for different languages."""
        samples = []
        
        # Python example
        python_code = self._generate_python_sample(path, method)
        if python_code:
            samples.append({
                "lang": "python",
                "source": python_code
            })
        
        # JavaScript example
        js_code = self._generate_javascript_sample(path, method)
        if js_code:
            samples.append({
                "lang": "javascript",
                "source": js_code
            })
        
        # cURL example
        curl_code = self._generate_curl_sample(path, method)
        if curl_code:
            samples.append({
                "lang": "shell",
                "source": curl_code
            })
        
        return samples
    
    def _generate_python_sample(self, path: str, method: str) -> str:
        """Generate Python code sample."""
        if method.upper() == "GET":
            return f'''import requests

response = requests.get(
    "https://api.optimus.dev{path}",
    headers={{"Authorization": "Bearer YOUR_TOKEN"}}
)

data = response.json()
print(data)'''
        else:
            return f'''import requests

response = requests.{method.lower()}(
    "https://api.optimus.dev{path}",
    headers={{"Authorization": "Bearer YOUR_TOKEN"}},
    json={{"key": "value"}}
)

data = response.json()
print(data)'''
    
    def _generate_javascript_sample(self, path: str, method: str) -> str:
        """Generate JavaScript code sample."""
        if method.upper() == "GET":
            return f'''fetch("https://api.optimus.dev{path}", {{
  headers: {{
    "Authorization": "Bearer YOUR_TOKEN"
  }}
}})
.then(response => response.json())
.then(data => console.log(data));'''
        else:
            return f'''fetch("https://api.optimus.dev{path}", {{
  method: "{method.upper()}",
  headers: {{
    "Content-Type": "application/json",
    "Authorization": "Bearer YOUR_TOKEN"
  }},
  body: JSON.stringify({{key: "value"}})
}})
.then(response => response.json())
.then(data => console.log(data));'''
    
    def _generate_curl_sample(self, path: str, method: str) -> str:
        """Generate cURL code sample."""
        if method.upper() == "GET":
            return f'''curl -X GET "https://api.optimus.dev{path}" \\
  -H "Authorization: Bearer YOUR_TOKEN"'''
        else:
            return f'''curl -X {method.upper()} "https://api.optimus.dev{path}" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -d '{{"key": "value"}}\''''
    
    def _is_internal_endpoint(self, path: str) -> bool:
        """Check if endpoint is internal."""
        internal_prefixes = ["/internal", "/admin", "/debug"]
        return any(path.startswith(prefix) for prefix in internal_prefixes)
    
    def _add_security_schemes(self, spec: Dict[str, Any]):
        """Add security scheme definitions."""
        spec["components"] = spec.get("components", {})
        spec["components"]["securitySchemes"] = {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT bearer token authentication"
            },
            "apiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API key authentication"
            },
            "oauth2": {
                "type": "oauth2",
                "flows": {
                    "authorizationCode": {
                        "authorizationUrl": "https://auth.optimus.dev/oauth/authorize",
                        "tokenUrl": "https://auth.optimus.dev/oauth/token",
                        "scopes": {
                            "read": "Read access",
                            "write": "Write access",
                            "admin": "Administrative access"
                        }
                    }
                }
            }
        }
        
        # Add global security requirement
        spec["security"] = [
            {"bearerAuth": []},
            {"apiKeyAuth": []},
            {"oauth2": ["read"]}
        ]
    
    def _add_custom_schemas(self, spec: Dict[str, Any]):
        """Add custom schema definitions."""
        if "components" not in spec:
            spec["components"] = {}
        
        if "schemas" not in spec["components"]:
            spec["components"]["schemas"] = {}
        
        # Add common schemas
        spec["components"]["schemas"].update({
            "SuccessResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean", "example": True},
                    "data": {"type": "object"},
                    "message": {"type": "string"},
                    "timestamp": {"type": "string", "format": "date-time"},
                    "request_id": {"type": "string"}
                }
            },
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean", "example": False},
                    "error": {"type": "string"},
                    "error_code": {"type": "string"},
                    "details": {"type": "object"},
                    "timestamp": {"type": "string", "format": "date-time"},
                    "request_id": {"type": "string"},
                    "help_url": {"type": "string"}
                }
            },
            "PaginationMeta": {
                "type": "object",
                "properties": {
                    "page": {"type": "integer"},
                    "size": {"type": "integer"},
                    "total_count": {"type": "integer"},
                    "total_pages": {"type": "integer"},
                    "has_next": {"type": "boolean"},
                    "has_previous": {"type": "boolean"}
                }
            }
        })
    
    def _add_examples(self, spec: Dict[str, Any], level: DocumentationLevel):
        """Add global examples."""
        if level != DocumentationLevel.COMPREHENSIVE:
            return
        
        if "components" not in spec:
            spec["components"] = {}
        
        spec["components"]["examples"] = {
            "ProjectExample": {
                "summary": "Sample project",
                "value": {
                    "id": "proj-123",
                    "name": "sample-project",
                    "description": "A sample project",
                    "status": "active",
                    "language": "python",
                    "framework": "fastapi"
                }
            },
            "ErrorExample": {
                "summary": "Error response",
                "value": {
                    "success": False,
                    "error": "Resource not found",
                    "error_code": "RESOURCE_NOT_FOUND",
                    "request_id": "req-123"
                }
            }
        }
    
    def _add_webhooks(self, spec: Dict[str, Any]):
        """Add webhook definitions."""
        spec["webhooks"] = {
            "projectStatusChanged": {
                "post": {
                    "summary": "Project status changed",
                    "description": "Triggered when a project status changes",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "event": {"type": "string", "example": "project.status.changed"},
                                        "project_id": {"type": "string"},
                                        "old_status": {"type": "string"},
                                        "new_status": {"type": "string"},
                                        "timestamp": {"type": "string", "format": "date-time"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    
    def _add_callbacks(self, spec: Dict[str, Any]):
        """Add callback definitions."""
        # Add callbacks for async operations
        pass
    
    def export_yaml(self, spec: Dict[str, Any], filename: str = None) -> str:
        """Export specification as YAML."""
        filename = filename or f"optimus-api-{self.settings.app_version}.yaml"
        
        try:
            yaml_content = yaml.dump(spec, default_flow_style=False, sort_keys=False)
            
            if filename:
                with open(filename, 'w') as f:
                    f.write(yaml_content)
                logger.info(f"OpenAPI spec exported to {filename}")
            
            return yaml_content
        except Exception as e:
            logger.error(f"Error exporting YAML: {e}")
            raise
    
    def export_json(self, spec: Dict[str, Any], filename: str = None) -> str:
        """Export specification as JSON."""
        filename = filename or f"optimus-api-{self.settings.app_version}.json"
        
        try:
            json_content = json.dumps(spec, indent=2)
            
            if filename:
                with open(filename, 'w') as f:
                    f.write(json_content)
                logger.info(f"OpenAPI spec exported to {filename}")
            
            return json_content
        except Exception as e:
            logger.error(f"Error exporting JSON: {e}")
            raise


class PostmanGenerator:
    """Generate Postman collection from OpenAPI spec."""
    
    def __init__(self, openapi_spec: Dict[str, Any]):
        self.spec = openapi_spec
    
    def generate_collection(self) -> Dict[str, Any]:
        """Generate Postman collection."""
        info = self.spec.get("info", {})
        servers = self.spec.get("servers", [])
        paths = self.spec.get("paths", {})
        
        collection = {
            "info": {
                "name": info.get("title", "API Collection"),
                "description": info.get("description", ""),
                "version": info.get("version", "1.0.0"),
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "variable": [
                {
                    "key": "baseUrl",
                    "value": servers[0]["url"] if servers else "{{baseUrl}}",
                    "type": "string"
                },
                {
                    "key": "authToken",
                    "value": "{{authToken}}",
                    "type": "string"
                }
            ],
            "auth": {
                "type": "bearer",
                "bearer": [
                    {
                        "key": "token",
                        "value": "{{authToken}}",
                        "type": "string"
                    }
                ]
            },
            "item": []
        }
        
        # Process paths
        for path, methods in paths.items():
            folder = self._create_folder_for_path(path)
            
            for method, operation in methods.items():
                if isinstance(operation, dict):
                    request = self._create_request(path, method, operation)
                    folder["item"].append(request)
            
            if folder["item"]:
                collection["item"].append(folder)
        
        return collection
    
    def _create_folder_for_path(self, path: str) -> Dict[str, Any]:
        """Create folder for path group."""
        path_parts = [part for part in path.split('/') if part and not part.startswith('{')]
        folder_name = path_parts[0] if path_parts else "root"
        
        return {
            "name": folder_name.capitalize(),
            "item": []
        }
    
    def _create_request(self, path: str, method: str, operation: Dict[str, Any]) -> Dict[str, Any]:
        """Create Postman request from operation."""
        request = {
            "name": operation.get("summary", f"{method.upper()} {path}"),
            "request": {
                "method": method.upper(),
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json"
                    }
                ],
                "url": {
                    "raw": "{{baseUrl}}" + path,
                    "host": ["{{baseUrl}}"],
                    "path": [part for part in path.split('/') if part]
                }
            },
            "response": []
        }
        
        # Add request body if exists
        if "requestBody" in operation:
            request_body = operation["requestBody"]
            if "content" in request_body and "application/json" in request_body["content"]:
                json_content = request_body["content"]["application/json"]
                if "examples" in json_content:
                    example = list(json_content["examples"].values())[0]
                    request["request"]["body"] = {
                        "mode": "raw",
                        "raw": json.dumps(example.get("value", {}), indent=2)
                    }
        
        return request
    
    def export(self, filename: str = None) -> str:
        """Export Postman collection."""
        filename = filename or "optimus-api.postman_collection.json"
        collection = self.generate_collection()
        
        try:
            json_content = json.dumps(collection, indent=2)
            
            if filename:
                with open(filename, 'w') as f:
                    f.write(json_content)
                logger.info(f"Postman collection exported to {filename}")
            
            return json_content
        except Exception as e:
            logger.error(f"Error exporting Postman collection: {e}")
            raise


# Convenience functions
def generate_openapi_spec(app: FastAPI, level: DocumentationLevel = DocumentationLevel.STANDARD) -> Dict[str, Any]:
    """Generate OpenAPI specification."""
    generator = OpenAPIGenerator(app)
    return generator.generate_spec(level)


def generate_postman_collection(openapi_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Generate Postman collection from OpenAPI spec."""
    generator = PostmanGenerator(openapi_spec)
    return generator.generate_collection()


def export_documentation(app: FastAPI, output_dir: str = "docs", 
                        level: DocumentationLevel = DocumentationLevel.STANDARD):
    """Export all documentation formats."""
    import os
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate OpenAPI spec
    generator = OpenAPIGenerator(app)
    spec = generator.generate_spec(level)
    
    # Export formats
    generator.export_yaml(spec, os.path.join(output_dir, "openapi.yaml"))
    generator.export_json(spec, os.path.join(output_dir, "openapi.json"))
    
    # Generate Postman collection
    postman_generator = PostmanGenerator(spec)
    postman_generator.export(os.path.join(output_dir, "postman_collection.json"))
    
    logger.info(f"Documentation exported to {output_dir}")


def validate_api_spec(spec: Dict[str, Any]) -> List[str]:
    """Validate OpenAPI specification."""
    errors = []
    
    # Basic validation
    required_fields = ["openapi", "info", "paths"]
    for field in required_fields:
        if field not in spec:
            errors.append(f"Missing required field: {field}")
    
    # Validate info
    if "info" in spec:
        info = spec["info"]
        if "title" not in info:
            errors.append("Missing info.title")
        if "version" not in info:
            errors.append("Missing info.version")
    
    # Validate paths
    if "paths" in spec:
        paths = spec["paths"]
        if not paths:
            errors.append("No paths defined")
        
        for path, methods in paths.items():
            for method, operation in methods.items():
                if isinstance(operation, dict):
                    if "responses" not in operation:
                        errors.append(f"Missing responses for {method.upper()} {path}")
    
    return errors