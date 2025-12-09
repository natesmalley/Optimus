# Docker Deployment Guide

Comprehensive guide for deploying Optimus using Docker and Docker Compose.

## Overview

Optimus uses a multi-container architecture with:
- **Backend**: Python FastAPI application
- **Frontend**: React TypeScript application served by Nginx
- **Database**: PostgreSQL 15 with optimizations
- **Cache**: Redis 7 with persistence
- **Monitoring**: Prometheus, Grafana, ELK Stack (optional)

## Docker Images

### Backend Image
- **Base**: Python 3.11-slim
- **Multi-stage build**: Optimized for production
- **Size**: ~500MB
- **Features**: Health checks, security hardening, non-root user

### Frontend Image
- **Build Stage**: Node 18-alpine
- **Serve Stage**: Nginx 1.25-alpine
- **Size**: ~50MB
- **Features**: Gzip compression, security headers, runtime configuration

## Environment Configurations

### Development Environment

```bash
# Start development environment
make dev

# Or manually
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

**Features:**
- Hot reloading for backend and frontend
- Debug ports exposed (5678 for backend)
- Development tools (Adminer, Redis Commander, Mailhog)
- Verbose logging
- Code mounted as volumes

**Services:**
```yaml
services:
  postgres:          # PostgreSQL 15
  redis:             # Redis 7
  optimus-backend:   # FastAPI application
  optimus-frontend:  # React development server
  adminer:           # Database admin
  redis-commander:   # Redis admin
  mailhog:           # Email testing
```

### Production Environment

```bash
# Start production environment
make deploy-prod ENV=prod

# Or manually
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

**Features:**
- Optimized production builds
- Resource limits and health checks
- Multiple replicas with load balancing
- Monitoring and logging
- SSL/TLS termination
- Auto-restart policies

**Additional Services:**
```yaml
services:
  nginx:           # Reverse proxy
  prometheus:      # Metrics collection
  grafana:         # Monitoring dashboards
  elasticsearch:   # Log aggregation
  logstash:        # Log processing
  kibana:          # Log visualization
```

## Configuration Files

### docker-compose.yml (Base)
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-optimus_db}
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-optimus123}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
```

### docker-compose.dev.yml (Development)
```yaml
version: '3.8'

services:
  optimus-backend:
    build:
      context: .
      target: runtime
    environment:
      ENV: development
      DEBUG: "true"
      LOG_LEVEL: debug
    volumes:
      - ./src:/app/src:ro
    ports:
      - "5678:5678"  # Debug port
```

### docker-compose.prod.yml (Production)
```yaml
version: '3.8'

services:
  optimus-backend:
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
      restart_policy:
        condition: on-failure
```

## Building Images

### Manual Build

```bash
# Build backend image
docker build -t optimus/backend:latest .

# Build frontend image
docker build -t optimus/frontend:latest -f frontend/Dockerfile .

# Build all images
make build
```

### Automated Build

```bash
# Build and tag with version
make build VERSION=v1.2.3

# Build and push to registry
make push DOCKER_REGISTRY=your-registry.com/optimus
```

### Multi-Architecture Build

```bash
# Build for multiple architectures
docker buildx build --platform linux/amd64,linux/arm64 \
  -t optimus/backend:latest --push .
```

## Environment Variables

### Core Configuration
```bash
# Application
ENV=production
DEBUG=false
LOG_LEVEL=info
WORKERS=4

# Database
DATABASE_URL=postgresql://user:pass@postgres:5432/optimus_db
POSTGRES_PASSWORD=secure_password

# Redis
REDIS_URL=redis://:password@redis:6379
REDIS_PASSWORD=secure_redis_password

# Security
JWT_SECRET=your-32-character-secret-key-here
CORS_ORIGINS=https://your-domain.com
```

### Production Overrides
```bash
# Performance
WORKERS=4
MAX_CONNECTIONS=100
CONNECTION_TIMEOUT=30

# Security
SSL_CERT_PATH=/etc/ssl/certs/app.crt
SSL_KEY_PATH=/etc/ssl/private/app.key

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_PASSWORD=secure_grafana_password

# AWS Integration
AWS_REGION=us-east-1
AWS_S3_BACKUP_BUCKET=optimus-backups
```

## Networking

### Development Network
```bash
# Create network
docker network create optimus-network

# Services communicate via service names:
# postgres:5432, redis:6379, optimus-backend:8000
```

### Production Network
```yaml
networks:
  optimus-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

## Storage and Volumes

### Development Volumes
```yaml
volumes:
  postgres_dev_data:
    driver: local
  redis_dev_data:
    driver: local
  # Code mounted for hot reloading
  - ./src:/app/src:ro
```

### Production Volumes
```yaml
volumes:
  postgres_prod_data:
    driver: local
  app_data:
    driver: local
  nginx_cache:
    driver: local
```

## Health Checks

### Backend Health Check
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:$PORT/health || exit 1
```

### Frontend Health Check
```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost/health || exit 1
```

### Database Health Check
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U postgres"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 10s
```

## Security Configuration

### Container Security
```dockerfile
# Run as non-root user
RUN groupadd --gid 1000 optimus && \
    useradd --uid 1000 --gid optimus --shell /bin/bash --create-home optimus
USER optimus

# Read-only root filesystem (where possible)
securityContext:
  readOnlyRootFilesystem: true
  runAsNonRoot: true
  runAsUser: 1000
```

### Network Security
```yaml
# Security groups
services:
  optimus-backend:
    networks:
      - optimus-network
    # Only expose necessary ports
    ports:
      - "8000:8000"
```

## Monitoring and Logging

### Log Aggregation
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### Metrics Collection
```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus:/etc/prometheus:ro
```

## Backup Strategies

### Database Backup
```bash
# Automated backup
docker exec postgres pg_dump -U postgres optimus_db | gzip > backup.sql.gz

# Using backup script
./scripts/backup.sh dev
```

### Volume Backup
```bash
# Backup Docker volumes
docker run --rm \
  -v postgres_data:/source:ro \
  -v /backup:/backup \
  alpine tar -czf /backup/postgres_backup.tar.gz -C /source .
```

## Performance Optimization

### Resource Limits
```yaml
deploy:
  resources:
    limits:
      memory: 2G
      cpus: '1.0'
    reservations:
      memory: 1G
      cpus: '0.5'
```

### Database Optimization
```yaml
environment:
  POSTGRES_SHARED_BUFFERS: 256MB
  POSTGRES_EFFECTIVE_CACHE_SIZE: 1GB
  POSTGRES_MAX_CONNECTIONS: 100
```

### Caching Strategy
```yaml
volumes:
  nginx_cache:/var/cache/nginx
environment:
  REDIS_MAXMEMORY: 512mb
  REDIS_MAXMEMORY_POLICY: allkeys-lru
```

## Troubleshooting

### Common Issues

1. **Container Won't Start**
```bash
# Check logs
docker-compose logs [service_name]

# Check resource usage
docker stats

# Verify configuration
docker-compose config
```

2. **Database Connection Issues**
```bash
# Test connection
docker-compose exec optimus-backend python -c "
import asyncpg
import asyncio
async def test():
    conn = await asyncpg.connect('postgresql://postgres:password@postgres/optimus_db')
    await conn.close()
asyncio.run(test())
"
```

3. **Image Build Issues**
```bash
# Clean build cache
docker system prune -f
docker builder prune

# Build with no cache
docker-compose build --no-cache
```

### Debugging Commands

```bash
# Enter container
docker-compose exec optimus-backend bash

# Check environment
docker-compose exec optimus-backend env

# Monitor resources
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Check networks
docker network ls
docker network inspect optimus-network
```

## Best Practices

1. **Use Multi-stage Builds** for smaller production images
2. **Pin Base Image Versions** for reproducible builds
3. **Scan Images** for vulnerabilities regularly
4. **Use Health Checks** for all services
5. **Implement Resource Limits** to prevent resource exhaustion
6. **Use Secrets Management** for sensitive data
7. **Enable Logging** with structured output
8. **Test Locally** before production deployment
9. **Backup Regularly** with automated scripts
10. **Monitor Performance** with metrics and alerts