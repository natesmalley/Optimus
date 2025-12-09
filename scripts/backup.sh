#!/bin/bash
# Backup script for Optimus application data

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ENVIRONMENT="${1:-dev}"
BACKUP_NAME="optimus_backup_${ENVIRONMENT}_${TIMESTAMP}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
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

# Check dependencies
check_dependencies() {
    local deps=("docker" "gzip" "tar")
    local missing=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" >/dev/null 2>&1; then
            missing+=("$dep")
        fi
    done
    
    if [ ${#missing[@]} -ne 0 ]; then
        error "Missing dependencies: ${missing[*]}"
        exit 1
    fi
}

# Create backup directory
create_backup_dir() {
    mkdir -p "$BACKUP_DIR/$BACKUP_NAME"
    log "Created backup directory: $BACKUP_DIR/$BACKUP_NAME"
}

# Backup PostgreSQL database
backup_database() {
    log "Backing up PostgreSQL database..."
    
    local container_name
    case "$ENVIRONMENT" in
        "dev")
            container_name="optimus-postgres"
            ;;
        "staging"|"prod")
            # For production, use external backup method
            backup_external_database
            return
            ;;
        *)
            error "Unknown environment: $ENVIRONMENT"
            exit 1
            ;;
    esac
    
    if ! docker ps --format "table {{.Names}}" | grep -q "$container_name"; then
        error "Database container $container_name is not running"
        exit 1
    fi
    
    # Create database dump
    docker exec "$container_name" pg_dump -U postgres optimus_db | gzip > "$BACKUP_DIR/$BACKUP_NAME/database.sql.gz"
    
    # Backup database configuration
    docker exec "$container_name" cat /etc/postgresql/postgresql.conf > "$BACKUP_DIR/$BACKUP_NAME/postgresql.conf" 2>/dev/null || true
    
    log "Database backup completed"
}

# Backup external database (for production)
backup_external_database() {
    if [ -z "$DATABASE_URL" ]; then
        error "DATABASE_URL not set for external database backup"
        exit 1
    fi
    
    log "Backing up external PostgreSQL database..."
    
    # Extract database connection details from DATABASE_URL
    local db_url="$DATABASE_URL"
    local pg_dump_cmd="pg_dump $db_url"
    
    if command -v pg_dump >/dev/null 2>&1; then
        $pg_dump_cmd | gzip > "$BACKUP_DIR/$BACKUP_NAME/database.sql.gz"
        log "External database backup completed"
    else
        error "pg_dump not found. Please install PostgreSQL client tools."
        exit 1
    fi
}

# Backup Redis data
backup_redis() {
    log "Backing up Redis data..."
    
    local container_name
    case "$ENVIRONMENT" in
        "dev")
            container_name="optimus-redis"
            ;;
        "staging"|"prod")
            backup_external_redis
            return
            ;;
    esac
    
    if docker ps --format "table {{.Names}}" | grep -q "$container_name"; then
        # Create Redis snapshot
        docker exec "$container_name" redis-cli BGSAVE
        sleep 5
        
        # Copy the dump file
        docker cp "$container_name:/data/dump.rdb" "$BACKUP_DIR/$BACKUP_NAME/redis_dump.rdb"
        
        # Backup Redis configuration
        docker exec "$container_name" cat /etc/redis/redis.conf > "$BACKUP_DIR/$BACKUP_NAME/redis.conf" 2>/dev/null || true
        
        log "Redis backup completed"
    else
        warn "Redis container not found, skipping Redis backup"
    fi
}

# Backup external Redis (for production)
backup_external_redis() {
    if [ -z "$REDIS_URL" ]; then
        warn "REDIS_URL not set, skipping external Redis backup"
        return
    fi
    
    log "Backing up external Redis..."
    
    # For AWS ElastiCache, Redis backups are handled by AWS
    # For other Redis instances, implement specific backup logic
    info "External Redis backup depends on your Redis provider"
    info "For AWS ElastiCache, backups are automatic"
    info "For other providers, please implement custom backup logic"
}

# Backup application data
backup_app_data() {
    log "Backing up application data..."
    
    # Backup local data directories
    if [ -d "data" ]; then
        tar -czf "$BACKUP_DIR/$BACKUP_NAME/app_data.tar.gz" data/
        log "Application data backed up"
    else
        warn "Application data directory not found"
    fi
    
    # Backup configuration files
    local config_files=(".env" "config/" "docker-compose*.yml")
    for file in "${config_files[@]}"; do
        if [ -e "$file" ]; then
            cp -r "$file" "$BACKUP_DIR/$BACKUP_NAME/"
        fi
    done
    
    # Backup logs (last 7 days)
    if [ -d "logs" ]; then
        find logs/ -name "*.log" -mtime -7 -exec cp {} "$BACKUP_DIR/$BACKUP_NAME/" \;
    fi
    
    log "Configuration and logs backed up"
}

# Backup Docker volumes
backup_docker_volumes() {
    log "Backing up Docker volumes..."
    
    local volumes
    case "$ENVIRONMENT" in
        "dev")
            volumes=("postgres_dev_data" "redis_dev_data" "optimus_app_data")
            ;;
        "staging")
            volumes=("postgres_staging_data" "redis_staging_data" "optimus_staging_data")
            ;;
        "prod")
            volumes=("postgres_prod_data" "redis_prod_data" "optimus_prod_data")
            ;;
    esac
    
    for volume in "${volumes[@]}"; do
        if docker volume ls -q | grep -q "$volume"; then
            log "Backing up volume: $volume"
            docker run --rm \
                -v "$volume:/source:ro" \
                -v "$PWD/$BACKUP_DIR/$BACKUP_NAME:/backup" \
                alpine tar -czf "/backup/${volume}.tar.gz" -C /source .
        else
            warn "Volume $volume not found, skipping"
        fi
    done
    
    log "Docker volumes backup completed"
}

# Create backup metadata
create_metadata() {
    log "Creating backup metadata..."
    
    cat > "$BACKUP_DIR/$BACKUP_NAME/metadata.json" << EOF
{
  "backup_name": "$BACKUP_NAME",
  "environment": "$ENVIRONMENT",
  "timestamp": "$TIMESTAMP",
  "date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "version": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
  "hostname": "$(hostname)",
  "user": "$(whoami)",
  "backup_size": "$(du -sh $BACKUP_DIR/$BACKUP_NAME | cut -f1)",
  "components": [
    "database",
    "redis",
    "app_data",
    "docker_volumes",
    "configuration"
  ]
}
EOF
    
    log "Metadata created"
}

# Compress backup
compress_backup() {
    log "Compressing backup..."
    
    cd "$BACKUP_DIR"
    tar -czf "${BACKUP_NAME}.tar.gz" "$BACKUP_NAME"
    rm -rf "$BACKUP_NAME"
    
    local backup_size=$(du -sh "${BACKUP_NAME}.tar.gz" | cut -f1)
    log "Backup compressed: ${BACKUP_NAME}.tar.gz ($backup_size)"
}

# Upload to cloud storage (if configured)
upload_backup() {
    if [ -n "$AWS_S3_BACKUP_BUCKET" ]; then
        log "Uploading backup to AWS S3..."
        
        if command -v aws >/dev/null 2>&1; then
            aws s3 cp "$BACKUP_DIR/${BACKUP_NAME}.tar.gz" \
                "s3://$AWS_S3_BACKUP_BUCKET/optimus-backups/" \
                --storage-class STANDARD_IA
            log "Backup uploaded to S3"
        else
            warn "AWS CLI not found, skipping S3 upload"
        fi
    fi
    
    if [ -n "$BACKUP_WEBHOOK_URL" ]; then
        log "Sending backup notification..."
        
        curl -s -X POST "$BACKUP_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{
                \"text\": \"Optimus backup completed\",
                \"environment\": \"$ENVIRONMENT\",
                \"backup_name\": \"$BACKUP_NAME\",
                \"timestamp\": \"$TIMESTAMP\"
            }" >/dev/null || warn "Failed to send notification"
    fi
}

# Clean old backups
cleanup_old_backups() {
    log "Cleaning up old backups..."
    
    # Remove local backups older than retention period
    find "$BACKUP_DIR" -name "optimus_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true
    
    # Clean up S3 backups (if configured)
    if [ -n "$AWS_S3_BACKUP_BUCKET" ] && command -v aws >/dev/null 2>&1; then
        local cutoff_date=$(date -d "$RETENTION_DAYS days ago" +%Y-%m-%d)
        aws s3 ls "s3://$AWS_S3_BACKUP_BUCKET/optimus-backups/" \
            | awk '{print $4}' \
            | grep "optimus_backup_.*\.tar\.gz" \
            | while read backup_file; do
                local backup_date=$(echo "$backup_file" | grep -oE '[0-9]{8}' | head -1)
                if [ "$backup_date" -lt "${cutoff_date//[-]/}" ]; then
                    aws s3 rm "s3://$AWS_S3_BACKUP_BUCKET/optimus-backups/$backup_file"
                    log "Deleted old S3 backup: $backup_file"
                fi
            done
    fi
    
    log "Cleanup completed"
}

# Verify backup integrity
verify_backup() {
    log "Verifying backup integrity..."
    
    if [ -f "$BACKUP_DIR/${BACKUP_NAME}.tar.gz" ]; then
        if tar -tzf "$BACKUP_DIR/${BACKUP_NAME}.tar.gz" >/dev/null 2>&1; then
            log "✓ Backup file is valid"
        else
            error "✗ Backup file is corrupted"
            exit 1
        fi
    else
        error "Backup file not found"
        exit 1
    fi
}

# Main backup function
main() {
    echo -e "${BLUE}Optimus Backup Script${NC}"
    echo "===================="
    echo ""
    
    log "Starting backup for environment: $ENVIRONMENT"
    log "Backup name: $BACKUP_NAME"
    
    check_dependencies
    create_backup_dir
    
    backup_database
    backup_redis
    backup_app_data
    backup_docker_volumes
    
    create_metadata
    compress_backup
    verify_backup
    
    upload_backup
    cleanup_old_backups
    
    echo ""
    log "✓ Backup completed successfully!"
    info "Backup location: $BACKUP_DIR/${BACKUP_NAME}.tar.gz"
    info "Backup size: $(du -sh $BACKUP_DIR/${BACKUP_NAME}.tar.gz | cut -f1)"
    echo ""
}

# Handle script interruption
trap 'error "Backup interrupted"; exit 1' INT TERM

# Run main function
main "$@"