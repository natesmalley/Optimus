# Optimus REST API Documentation

## Overview

The Optimus API provides comprehensive access to all system features including project analysis, runtime monitoring, AI insights, and real-time data streaming. The API is built with FastAPI and includes automatic OpenAPI documentation.

## API Base URL

```
http://localhost:8005/api/v1
```

## Authentication

Currently, the API operates without authentication for development. Production deployments should implement proper authentication and authorization.

## API Versioning

All endpoints are versioned using URL prefixes:
- Current version: `/api/v1`
- Upcoming version: `/api/v2` (planned)

## Rate Limiting

- WebSocket connections: 1000 messages per minute
- REST endpoints: No current limits (will be implemented in production)

## Response Format

All API responses follow a consistent format:

### Success Response
```json
{
  "data": {...},
  "timestamp": "2024-01-15T10:30:00Z",
  "status": "success"
}
```

### Error Response
```json
{
  "error": "Error description",
  "type": "error_type",
  "timestamp": "2024-01-15T10:30:00Z",
  "status": "error"
}
```

## Available API Modules

### 1. Projects API (`/api/v1/projects`)
Core project management and metadata.

**Key Endpoints:**
- `GET /projects` - List all projects
- `GET /projects/{id}` - Get project details
- `POST /projects` - Create new project
- `PUT /projects/{id}` - Update project

### 2. Scanner API (`/api/v1/scanner`)
Enhanced project analysis and discovery.

**Key Endpoints:**
- `GET /scanner/projects` - List discovered projects
- `GET /scanner/projects/{id}/analysis` - Deep project analysis
- `POST /scanner/scan` - Trigger project scan
- `GET /scanner/technologies` - Technology usage statistics
- `GET /scanner/dependencies` - Dependency analysis
- `GET /scanner/vulnerabilities` - Security vulnerabilities
- `GET /scanner/quality` - Code quality metrics
- `POST /scanner/compare` - Compare projects

### 3. Runtime Monitor API (`/api/v1/monitor`)
Real-time process and system monitoring.

**Key Endpoints:**
- `GET /monitor/processes` - Running processes
- `GET /monitor/services` - Active services
- `GET /monitor/containers` - Docker containers
- `GET /monitor/metrics` - System metrics
- `GET /monitor/alerts` - Performance alerts
- `GET /monitor/trends` - Performance trends
- `GET /monitor/projects/{id}/status` - Project runtime status
- `GET /monitor/projects/{id}/logs` - Project logs
- `GET /monitor/memory-leaks` - Memory leak detection
- `POST /monitor/start` - Start monitoring
- `POST /monitor/projects/{id}/track` - Track specific project

### 4. Memory System API (`/api/v1/memory`)
AI memory and learning system.

**Key Endpoints:**
- `GET /memory/deliberations` - Stored deliberations
- `GET /memory/deliberations/{id}` - Specific deliberation
- `GET /memory/personas/{name}/history` - Persona history
- `POST /memory/search` - Search memories
- `GET /memory/patterns` - Learning patterns
- `POST /memory/consolidate` - Trigger consolidation
- `GET /memory/stats` - Memory statistics
- `GET /memory/personas/{name}/summary` - Persona summary
- `GET /memory/similar` - Find similar memories
- `GET /memory/associations/{id}` - Memory associations

### 5. Knowledge Graph API (`/api/v1/graph`)
Cross-project intelligence and relationships.

**Key Endpoints:**
- `GET /graph/nodes` - Graph nodes with filtering
- `GET /graph/nodes/{id}` - Node details
- `POST /graph/nodes` - Create node
- `GET /graph/edges` - Graph edges
- `POST /graph/edges` - Create edge
- `GET /graph/insights` - Cross-project insights
- `GET /graph/technologies` - Technology patterns
- `GET /graph/clusters` - Community detection
- `GET /graph/path` - Find concept paths
- `GET /graph/stats` - Graph statistics
- `GET /graph/visualization` - Export for visualization
- `GET /graph/personas/expertise` - Persona expertise mapping
- `GET /graph/projects/{tech}/related` - Related projects
- `POST /graph/analyze` - Trigger analysis

### 6. Dashboard API (`/api/v1/dashboard`)
Aggregated insights and system overview.

**Key Endpoints:**
- `GET /dashboard/overview` - Complete system overview
- `GET /dashboard/health` - System health analysis
- `GET /dashboard/projects/health` - Project health analysis
- `GET /dashboard/projects/{id}/health` - Specific project health
- `GET /dashboard/insights` - AI-generated insights
- `GET /dashboard/recommendations` - Action recommendations
- `GET /dashboard/activity` - Recent activity feed
- `GET /dashboard/trends` - Performance trends
- `GET /dashboard/resources` - Resource utilization

### 7. Council API (`/api/v1/council`)
AI Council of Minds deliberation system.

**Key Endpoints:**
- `POST /council/deliberate` - Start deliberation
- `GET /council/deliberations/{id}` - Get deliberation
- `GET /council/personas` - List personas
- `GET /council/personas/{name}` - Persona details

## WebSocket Endpoints

Real-time data streaming via WebSocket connections.

### Available WebSocket Rooms

#### 1. System Metrics (`/ws/system/metrics`)
```javascript
// Connection
const ws = new WebSocket('ws://localhost:8005/ws/system/metrics');

// Messages received:
{
  "type": "metrics_update",
  "data": {
    "cpu_percent": 45.2,
    "memory_percent": 67.1,
    "disk_usage_percent": 42.8,
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

#### 2. Project Monitoring (`/ws/projects/monitoring`)
```javascript
// Connection
const ws = new WebSocket('ws://localhost:8005/ws/projects/monitoring');

// Subscribe to specific project
ws.send(JSON.stringify({
  "type": "subscribe_project", 
  "project_id": "proj_123"
}));

// Messages received:
{
  "type": "project_status",
  "project_id": "proj_123",
  "data": {
    "is_running": true,
    "processes": [...],
    "services": [...]
  }
}
```

#### 3. Scanner Progress (`/ws/scanner/progress`)
```javascript
// Connection and scan trigger
const ws = new WebSocket('ws://localhost:8005/ws/scanner/progress');

ws.send(JSON.stringify({
  "type": "start_scan",
  "base_path": "/Users/dev/projects"
}));

// Progress updates:
{
  "type": "scan_progress",
  "progress_percent": 60,
  "current_step": "Analyzing dependencies"
}
```

#### 4. Live Dashboard (`/ws/dashboard/live`)
```javascript
// Real-time dashboard updates
const ws = new WebSocket('ws://localhost:8005/ws/dashboard/live');

// Request specific widget update
ws.send(JSON.stringify({
  "type": "request_update",
  "widget": "health"
}));
```

#### 5. Deliberation Progress (`/ws/deliberations/{id}`)
```javascript
// Monitor deliberation progress
const deliberationId = "delib_123";
const ws = new WebSocket(`ws://localhost:8005/ws/deliberations/${deliberationId}`);
```

#### 6. Live Alerts (`/ws/alerts/live`)
```javascript
// Real-time alerts and notifications
const ws = new WebSocket('ws://localhost:8005/ws/alerts/live');

// Set alert filters
ws.send(JSON.stringify({
  "type": "set_filters",
  "filters": {
    "severity": ["high", "critical"],
    "type": ["security", "performance"]
  }
}));
```

## Common Query Parameters

### Pagination
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum records to return (default: 50, max: 200)

### Sorting
- `sort_by`: Field to sort by
- `sort_desc`: Sort descending (default: true)

### Filtering
- `search`: Text search in relevant fields
- `since`: Get records since timestamp
- `project_id`: Filter by specific project
- `status`: Filter by status

### Examples
```bash
# Get recent projects with pagination
GET /api/v1/projects?skip=0&limit=20&sort_by=last_scanned&sort_desc=true

# Search projects by technology
GET /api/v1/scanner/projects?technology=react&limit=50

# Get high severity alerts
GET /api/v1/monitor/alerts?severity=high&since=2024-01-15T00:00:00Z

# Search memories by persona
POST /api/v1/memory/search
{
  "query": "performance optimization",
  "persona_name": "system_architect",
  "limit": 10
}
```

## Error Handling

The API uses standard HTTP status codes:

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error

### Error Response Examples

#### Validation Error (422)
```json
{
  "error": "Validation failed",
  "type": "validation_error",
  "details": [
    {
      "field": "project_id",
      "message": "Invalid UUID format"
    }
  ]
}
```

#### Not Found (404)
```json
{
  "error": "Project not found",
  "type": "not_found",
  "resource": "project",
  "resource_id": "invalid_id"
}
```

## Interactive Documentation

FastAPI provides automatic interactive documentation:

- **Swagger UI**: `http://localhost:8005/docs`
- **ReDoc**: `http://localhost:8005/redoc`
- **OpenAPI JSON**: `http://localhost:8005/openapi.json`

## SDK Examples

### Python SDK Usage
```python
import requests
import asyncio
import websockets
import json

# REST API calls
base_url = "http://localhost:8005/api/v1"

# Get system overview
response = requests.get(f"{base_url}/dashboard/overview")
overview = response.json()

# Trigger project scan
scan_response = requests.post(f"{base_url}/scanner/scan", json={
    "base_path": "/Users/dev/projects",
    "include_analysis": True
})

# WebSocket connection
async def monitor_metrics():
    uri = "ws://localhost:8005/ws/system/metrics"
    
    async with websockets.connect(uri) as websocket:
        # Send heartbeat
        await websocket.send(json.dumps({"type": "heartbeat"}))
        
        # Listen for metrics
        async for message in websocket:
            data = json.loads(message)
            print(f"Metrics: {data}")
```

### JavaScript SDK Usage
```javascript
// REST API calls
const baseUrl = 'http://localhost:8005/api/v1';

// Get projects
async function getProjects() {
  const response = await fetch(`${baseUrl}/projects`);
  const projects = await response.json();
  return projects;
}

// WebSocket monitoring
const ws = new WebSocket('ws://localhost:8005/ws/system/metrics');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('System metrics:', data);
};

// Send heartbeat every 30 seconds
setInterval(() => {
  ws.send(JSON.stringify({ type: 'heartbeat' }));
}, 30000);
```

## Performance Considerations

### REST API
- Use pagination for large datasets
- Implement client-side caching for static data
- Use appropriate filters to reduce response size
- Monitor rate limits in production

### WebSocket
- Implement heartbeat to detect disconnections
- Handle reconnection logic for resilience
- Use appropriate filters to reduce message volume
- Respect rate limits (1000 messages/minute)

### Bulk Operations
- Use background tasks for long-running operations
- Monitor progress via WebSocket updates
- Implement proper error handling and retries

## Security Considerations

### Development Environment
- API runs without authentication
- All endpoints are publicly accessible
- WebSocket connections are unprotected

### Production Requirements
- Implement JWT or API key authentication
- Add role-based access control (RBAC)
- Enable HTTPS/WSS for secure connections
- Add input validation and sanitization
- Implement rate limiting and DDoS protection
- Add audit logging for sensitive operations

## Testing

### Health Check
```bash
curl http://localhost:8005/health
```

### API Endpoints Test
```bash
# Test projects endpoint
curl http://localhost:8005/api/v1/projects

# Test dashboard overview
curl http://localhost:8005/api/v1/dashboard/overview

# Test scanner health
curl http://localhost:8005/api/v1/scanner/health
```

### WebSocket Test
```javascript
// Simple WebSocket test
const ws = new WebSocket('ws://localhost:8005/ws/system/metrics');
ws.onopen = () => console.log('Connected');
ws.onmessage = (e) => console.log('Message:', e.data);
ws.onerror = (e) => console.error('Error:', e);
```

## Support and Documentation

- **Interactive Docs**: `http://localhost:8005/docs`
- **API Schema**: `http://localhost:8005/openapi.json`
- **Health Status**: `http://localhost:8005/health`
- **System Status**: `http://localhost:8005/api/v1/dashboard/health`

For additional support and detailed examples, refer to the complete API documentation in the `/docs/api/` directory.