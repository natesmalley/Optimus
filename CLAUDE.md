# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Optimus** is an intelligent project orchestrator and monetization platform built with the CoralCollective AI framework. It monitors, analyzes, and optimizes your entire development portfolio while providing intelligent troubleshooting assistance and revenue opportunity alignment.

## Core Architecture

### System Design
- **Project Discovery & Monitoring**: Auto-discovers projects in ~/projects, tracks runtime status, analyzes tech stacks
- **Intelligence Engine**: Pattern recognition, technical debt assessment, security scanning, performance analysis
- **Monetization Advisor**: Evaluates revenue potential, suggests features based on market trends, proposes business models
- **Troubleshooting System**: Error pattern recognition, cross-project learning, automated fix attempts
- **Orchestration Engine**: Manages startup automation, environment handling, resource allocation

### Technology Stack
- **Backend**: Python with FastAPI for core services
- **Database**: PostgreSQL for project data, Redis for caching
- **AI Framework**: CoralCollective with 20+ specialized AI agents
- **MCP Integration**: Model Context Protocol for secure external service access
- **Frontend**: React dashboard (planned)
- **Infrastructure**: Docker containers, systemd services

## Development Commands

### Python Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt
pip install -e .  # Install package in development mode
```

### Database Setup
```bash
# Start PostgreSQL via Docker
docker run -d --name optimus-postgres \
  -e POSTGRES_PASSWORD=optimus123 \
  -e POSTGRES_DB=optimus_db \
  -p 5432:5432 \
  postgres:15

# Start Redis
docker run -d --name optimus-redis \
  -p 6379:6379 \
  redis:7-alpine
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_scanner.py

# Run with verbose output
pytest -v
```

### Code Quality
```bash
# Format code with Black
black src/ tests/

# Lint with Ruff
ruff check src/ tests/

# Type checking with MyPy
mypy src/
```

### Running Services
```bash
# Start the main application
python src/main.py

# Start with environment variables
export DATABASE_URL=postgresql://postgres:optimus123@localhost/optimus_db
export REDIS_URL=redis://localhost:6379
python src/main.py
```

## CoralCollective AI Agent System

### Using AI Agents
```bash
# Interactive workflow wizard
./coral workflow

# Run specific agent with task
./coral agent backend_developer "Build REST API for project scanning"
./coral agent frontend_developer "Create dashboard component"
./coral agent database_specialist "Design schema for metrics"

# Fast optimized execution
./coral_fast run backend_developer "Implement authentication"

# Parallel agent execution
./coral_fast parallel 'backend:API' 'frontend:UI' 'database:Schema'

# List all available agents
./coral list
```

### Key Agents for Optimus Development
- **project_architect**: System design and architecture planning
- **backend_developer**: API and service implementation
- **database_specialist**: Schema design and optimization
- **frontend_developer**: Dashboard and UI components
- **qa_testing**: Test implementation and quality assurance
- **security_specialist**: Security review and vulnerability assessment
- **devops_deployment**: Infrastructure and deployment setup
- **api_designer**: REST API design and documentation

### Agent Workflow Pattern
```bash
# 1. Design first
./coral agent api_designer "Design scanner service API"

# 2. Implement
./coral agent backend_developer "Implement scanner service"

# 3. Test
./coral agent qa_testing "Write tests for scanner service"

# 4. Review
./coral agent security_specialist "Review scanner for vulnerabilities"
```

## MCP (Model Context Protocol) Integration

### Available MCP Servers
- **GitHub**: Repository management, issues, pull requests
- **Filesystem**: Secure file operations within project
- **PostgreSQL**: Database operations
- **Docker**: Container management
- **E2B**: Secure code execution sandbox
- **Brave Search**: Web research capabilities

### MCP Client Usage
```python
from mcp.mcp_client import MCPClient, AgentMCPInterface

# Basic client usage
async with MCPClient('mcp/configs/mcp_config.yaml') as client:
    tools = await client.list_tools('filesystem')
    result = await client.call_tool('filesystem', 'read_file', {'path': 'README.md'})

# Agent-specific interface
interface = AgentMCPInterface('backend_developer')
content = await interface.filesystem_read('package.json')
users = await interface.database_query("SELECT * FROM users")
```

## Project Structure

```
Optimus/
├── .coral/                 # CoralCollective framework (AI agents)
│   ├── agents/            # Agent definitions and prompts
│   ├── mcp/               # Model Context Protocol integration
│   └── providers/         # AI model providers
├── src/                   # Source code
│   ├── api/              # FastAPI endpoints
│   ├── core/             # Core business logic
│   ├── models/           # Database models
│   ├── services/         # Service layer
│   │   ├── scanner.py    # Project discovery
│   │   ├── monitor.py    # Runtime monitoring
│   │   └── analyzer.py   # Code analysis
│   └── utils/            # Utilities
├── tests/                # Test files
├── docs/                 # Documentation
│   ├── database/         # Schema definitions
│   └── architecture/     # System design docs
├── config/               # Configuration files
├── coral                 # CoralCollective CLI wrapper
├── coral_fast           # Optimized async agent runner
└── pyproject.toml       # Project configuration
```

## Development Workflow

### Phase 1: Foundation (Current Focus)
1. Project scanner implementation
2. Database models and API endpoints
3. Runtime monitoring service
4. Basic web dashboard

### Phase 2: Intelligence
1. Code quality analyzer
2. Pattern recognition system
3. Troubleshooting knowledge base
4. Monetization analysis

### Phase 3: Automation
1. Automated fix attempts
2. Project orchestration
3. Deployment assistance
4. Advanced recommendations

## Environment Configuration

Create `.env` file in project root:
```env
DATABASE_URL=postgresql://postgres:optimus123@localhost/optimus_db
REDIS_URL=redis://localhost:6379
PROJECT_ROOT=/Users/nathanial.smalley/projects
API_PORT=8000
SCAN_INTERVAL=300  # 5 minutes
```

## Key Implementation Notes

### Database Schema Location
The main PostgreSQL schema is defined in `docs/database/schema.sql`

### API Design
FastAPI application structure follows RESTful principles with endpoints for:
- `/api/projects` - Project management
- `/api/runtime` - Runtime status
- `/api/analysis` - Code analysis results
- `/api/metrics` - Performance metrics
- `/api/monetization` - Revenue analysis

### Security Considerations
- All MCP operations are sandboxed to project directory
- Agent permissions are configured in `.coral/mcp/configs/mcp_config.yaml`
- Sensitive files (.env, .git, secrets/) are excluded from operations
- Database operations can be configured as read-only

### Testing Strategy
- Unit tests for individual services
- Integration tests for API endpoints
- Mock MCP servers for testing agent interactions
- Use pytest fixtures for database setup/teardown

## Quick Start Development Tasks

### Building Core Scanner
```bash
./coral agent backend_developer "Build the project scanner service that discovers all projects in ~/projects, analyzes their stack, and stores them in PostgreSQL using the schema in docs/database/schema.sql"
```

### Creating API Endpoints
```bash
./coral agent api_designer "Design RESTful API endpoints based on docs/TECHNICAL_ARCHITECTURE.md"
./coral agent backend_developer "Implement FastAPI endpoints for projects, runtime, and analysis"
```

### Runtime Monitor
```bash
./coral agent backend_developer "Create runtime monitor using psutil to detect processes and ports"
```

### Dashboard Development
```bash
./coral agent frontend_developer "Create React dashboard showing discovered projects, status, and metrics using the API endpoints"
```

## Important Conventions

1. **Code Style**: Follow PEP 8, use Black formatter, line length 100
2. **Type Hints**: Always use type hints in Python code
3. **Testing**: Write tests for all new services and endpoints
4. **Documentation**: Update docstrings for all public functions
5. **Git Commits**: Use conventional commit messages (feat:, fix:, docs:, etc.)
6. **Error Handling**: Implement comprehensive error handling with proper logging
7. **Async Operations**: Use async/await for I/O operations
8. **Security**: Never commit secrets, use environment variables

## Debugging Tips

1. **Enable Debug Logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Test MCP Connections**:
   ```bash
   python3 .coral/mcp/test_mcp_client.py
   ```

3. **Check Agent Permissions**:
   ```bash
   cat .coral/mcp/configs/mcp_config.yaml | grep -A5 "agent_permissions"
   ```

4. **Monitor Background Tasks**:
   ```bash
   ps aux | grep optimus
   lsof -i :8000  # Check API port
   ```