# Optimus Backend Setup Guide

This guide walks you through setting up the Optimus backend infrastructure.

## Prerequisites

- Python 3.8+ 
- PostgreSQL 15+
- Redis 7.0+
- Git

## Installation

1. **Install Dependencies**
   ```bash
   pip install -e .
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your database and Redis credentials
   ```

3. **Setup Database**
   ```bash
   # Create database and run schema
   psql -U postgres -c "CREATE DATABASE optimus_db;"
   psql -U postgres -d optimus_db -f docs/database/schema.sql
   ```

4. **Start Redis**
   ```bash
   redis-server
   ```

## Running the Backend

### Development Mode
```bash
python run_backend.py
```

### Production Mode
```bash
# Set DEBUG=false in .env first
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## API Endpoints

Once running, the backend provides these endpoints:

### Core Endpoints
- `GET /health` - Health check
- `GET /` - API information

### Projects API (`/api/v1/projects`)
- `GET /` - List all projects (with pagination and filtering)
- `GET /{id}` - Get project details
- `POST /{id}/scan` - Trigger project scan
- `DELETE /{id}` - Archive project
- `GET /{id}/analysis` - Get analysis results
- `GET /{id}/monetization` - Get monetization opportunities

### Runtime API (`/api/v1/runtime`)
- `GET /` - System runtime overview
- `GET /project/{id}` - Project runtime status
- `POST /monitor` - Trigger monitoring cycle
- `GET /processes` - List all tracked processes
- `GET /stats` - Runtime statistics

### Metrics API (`/api/v1/metrics`)
- `GET /projects/{id}` - Project metrics
- `GET /` - System-wide metrics
- `GET /health/{id}` - Project health score
- `GET /trends` - Metrics trend analysis

### Manual Operations
- `POST /api/v1/scan` - Trigger project scan
- `POST /api/v1/monitor` - Trigger monitoring cycle

## Architecture

The backend consists of:

1. **Project Scanner Service** - Discovers and analyzes projects
2. **Runtime Monitor** - Tracks running processes and resource usage
3. **FastAPI Application** - REST API with proper routing and validation
4. **Database Models** - SQLAlchemy models for PostgreSQL
5. **Configuration Management** - Environment-based settings

## Key Features

- **Automatic Project Discovery** - Scans your projects directory to detect tech stacks
- **Real-time Process Monitoring** - Tracks CPU, memory, and port usage
- **Code Quality Analysis** - Integrates with analysis tools for quality metrics
- **Monetization Opportunities** - AI-powered revenue potential assessment
- **Error Pattern Recognition** - Learns from common errors for auto-resolution
- **Comprehensive Metrics** - Time-series performance and health tracking

## Configuration

Key environment variables in `.env`:

```bash
# Database
DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/optimus_db"

# Scanning
PROJECTS_BASE_PATH="~/projects"
SCAN_INTERVAL=300
EXCLUDED_DIRECTORIES=".git,__pycache__,node_modules,.venv"

# Monitoring  
MONITOR_INTERVAL=30
HEARTBEAT_THRESHOLD=180

# Logging
LOG_LEVEL="INFO"
DEBUG=false
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check PostgreSQL is running
   - Verify credentials in `.env`
   - Ensure database exists

2. **Redis Connection Failed**
   - Start Redis server: `redis-server`
   - Check Redis URL in `.env`

3. **Import Errors**
   - Install dependencies: `pip install -e .`
   - Check Python version (3.8+)

4. **Permission Errors during Scanning**
   - Check file permissions in projects directory
   - Run with appropriate user permissions

### Logs

Logs are written to:
- Console output (structured logging)
- `optimus.log` file (if configured)

Set `LOG_LEVEL=DEBUG` for verbose output.

## Next Steps

After the backend is running:

1. **Trigger Initial Scan**
   ```bash
   curl -X POST http://localhost:8000/api/v1/scan
   ```

2. **Check Projects**
   ```bash
   curl http://localhost:8000/api/v1/projects
   ```

3. **Monitor Runtime**
   ```bash
   curl http://localhost:8000/api/v1/runtime
   ```

The backend will automatically:
- Scan for new projects every 5 minutes
- Monitor running processes every 30 seconds
- Clean up old data periodically

## API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation (Swagger UI).