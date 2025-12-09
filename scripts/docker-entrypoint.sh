#!/bin/bash
# Docker entrypoint script for Optimus backend

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] OPTIMUS:${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

# Default configuration
export DATABASE_URL=${DATABASE_URL:-"postgresql://postgres:optimus123@postgres:5432/optimus_db"}
export REDIS_URL=${REDIS_URL:-"redis://redis:6379"}
export PROJECT_ROOT=${PROJECT_ROOT:-"/app/projects"}
export API_PORT=${PORT:-8000}
export WORKERS=${WORKERS:-4}
export LOG_LEVEL=${LOG_LEVEL:-"info"}

log "Starting Optimus Backend Container"
log "Environment: ${ENV:-development}"
log "Port: $API_PORT"
log "Workers: $WORKERS"
log "Log Level: $LOG_LEVEL"

# Wait for database to be ready
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local max_attempts=30
    local attempt=1

    info "Waiting for $service_name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if nc -z $host $port 2>/dev/null; then
            log "$service_name is ready!"
            return 0
        fi
        
        warn "Attempt $attempt/$max_attempts: $service_name not ready yet, waiting..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    error "$service_name failed to become ready after $max_attempts attempts"
    return 1
}

# Extract host and port from DATABASE_URL
if [[ $DATABASE_URL =~ postgresql://[^@]+@([^:]+):([0-9]+)/ ]]; then
    DB_HOST="${BASH_REMATCH[1]}"
    DB_PORT="${BASH_REMATCH[2]}"
    wait_for_service "$DB_HOST" "$DB_PORT" "PostgreSQL Database"
else
    warn "Could not parse database URL for health check"
fi

# Extract host and port from REDIS_URL
if [[ $REDIS_URL =~ redis://([^:]+):([0-9]+) ]]; then
    REDIS_HOST="${BASH_REMATCH[1]}"
    REDIS_PORT="${BASH_REMATCH[2]}"
    wait_for_service "$REDIS_HOST" "$REDIS_PORT" "Redis Cache"
else
    warn "Could not parse Redis URL for health check"
fi

# Run database migrations
log "Running database migrations..."
if command -v alembic &> /dev/null; then
    cd /app && alembic upgrade head
    log "Database migrations completed"
else
    warn "Alembic not found, skipping migrations"
fi

# Initialize database if needed
log "Initializing database..."
python -c "
import asyncio
from src.database.initialize import initialize_database
asyncio.run(initialize_database())
" && log "Database initialization completed" || warn "Database initialization failed"

# Create necessary directories
mkdir -p /app/logs /app/data/memory /app/data/knowledge

# Set proper permissions
chmod -R 755 /app/logs /app/data

log "Container initialization complete"

# Execute the main command
info "Starting application with command: $*"
exec "$@"