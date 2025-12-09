# Quick Start Deployment Guide

Get Optimus running in under 10 minutes with Docker Compose.

## Prerequisites

- Docker & Docker Compose installed
- Git installed
- 8GB+ RAM available
- Ports 3000, 8000, 5432, 6379 available

## 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-org/optimus.git
cd optimus

# Run the automated setup script
chmod +x scripts/setup.sh
./scripts/setup.sh
```

The setup script will:
- Check system requirements
- Install Python and Node.js dependencies
- Create environment configuration
- Set up Docker network

## 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit configuration (minimum required changes)
nano .env
```

**Required Changes:**
```bash
# Set your project directory
PROJECT_ROOT=/path/to/your/projects

# Add AI API keys (optional for testing)
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

## 3. Start Development Environment

```bash
# Start all services
make dev

# Or manually with Docker Compose
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

This will start:
- PostgreSQL database
- Redis cache
- Optimus backend API
- React frontend dashboard
- Development tools (Adminer, Redis Commander)

## 4. Verify Installation

```bash
# Check service status
make status

# Check health endpoints
curl http://localhost:8000/health
curl http://localhost:3000/health

# View logs
make logs
```

## 5. Access Applications

| Service | URL | Description |
|---------|-----|-------------|
| **Frontend Dashboard** | http://localhost:3000 | Main Optimus interface |
| **Backend API** | http://localhost:8000 | REST API endpoints |
| **API Documentation** | http://localhost:8000/docs | Interactive API docs |
| **Database Admin** | http://localhost:8080 | Adminer (PostgreSQL GUI) |
| **Redis Admin** | http://localhost:8081 | Redis Commander |

## 6. Test the System

```bash
# Run backend tests
make test-backend

# Run frontend tests
make test-frontend

# Run integration tests
make test-integration

# Or run all tests
make test
```

## 7. Development Workflow

```bash
# View real-time logs
make logs

# Restart services
make restart

# Stop all services
make stop

# Clean up (removes all data)
make clean

# Reset entire environment
make reset
```

## Common Issues

### Port Conflicts
If ports are in use:
```bash
# Check what's using the ports
lsof -i :3000
lsof -i :8000

# Stop conflicting services or change ports in .env
```

### Database Connection Issues
```bash
# Check database status
docker-compose logs postgres

# Reset database
make db-reset
```

### Memory Issues
```bash
# Check resource usage
docker stats

# Reduce workers in .env if needed
WORKERS=2
```

## Next Steps

Once running:

1. **Explore the Dashboard**: Navigate to http://localhost:3000
2. **Configure Project Scanning**: Update PROJECT_ROOT in .env
3. **Set up AI Integration**: Add API keys for enhanced features
4. **Review Documentation**: Check docs/ directory for detailed guides
5. **Production Setup**: Follow the [Kubernetes Deployment Guide](./KUBERNETES_DEPLOYMENT.md)

## Quick Commands Reference

```bash
# Development
make dev              # Start development environment
make dev-build        # Build and start with fresh images
make dev-stop         # Stop development environment
make dev-clean        # Clean development environment

# Testing
make test             # Run all tests
make test-backend     # Backend tests only
make test-frontend    # Frontend tests only
make lint             # Run code linting
make format           # Format code

# Monitoring
make logs             # View all logs
make logs-backend     # Backend logs only
make monitor          # Open monitoring dashboard
make health           # Check service health

# Database
make db-migrate       # Run database migrations
make db-seed          # Seed with test data
make db-reset         # Reset database

# Utilities
make backup           # Create backup
make clean            # Clean Docker resources
make help             # Show all available commands
```

## Support

If you encounter issues:

1. Check the [Troubleshooting Guide](./TROUBLESHOOTING.md)
2. Review logs: `make logs`
3. Verify environment: `make status`
4. Reset if needed: `make reset`
5. Create a GitHub issue with logs and system info