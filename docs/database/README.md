# Optimus Database Schema

This document describes the PostgreSQL database schema for the Optimus project orchestrator platform.

## Overview

The Optimus database is designed to support comprehensive project management, real-time monitoring, code analysis, error tracking, and monetization opportunity identification. The schema is optimized for performance with proper indexing, JSONB fields for flexible data storage, and automated triggers for data consistency.

## Core Tables

### 1. `projects`
Central registry for all discovered and managed projects.

**Key Fields:**
- `tech_stack` (JSONB): Technology stack information (languages, frameworks, tools)
- `dependencies` (JSONB): Project dependencies with versions
- `language_stats` (JSONB): Programming language distribution percentages
- `git_url`: Repository URL
- `last_commit_hash`: SHA of the last commit
- `status`: Project status (discovered, active, inactive, archived, error)

### 2. `runtime_status`
Real-time tracking of running processes and resource consumption.

**Key Fields:**
- `process_name`: Name of the running process
- `pid`: System process ID
- `port`: Port number if applicable
- `cpu_usage`: CPU usage percentage
- `memory_usage`: Memory usage in bytes
- `last_heartbeat`: Last health check timestamp

### 3. `analysis_results`
Results from automated code quality and security analysis.

**Key Fields:**
- `analysis_type`: Type of analysis (code_quality, security, performance, dependencies)
- `results` (JSONB): Detailed analysis results
- `score`: Numeric score (0-100)
- `issues_count`: Number of issues found

### 4. `monetization_opportunities`
Identified revenue generation opportunities for projects.

**Key Fields:**
- `opportunity_type`: Type of opportunity (saas, marketplace, licensing, etc.)
- `potential_revenue`: Estimated revenue potential
- `effort_required`: Implementation effort level (low, medium, high, very_high)
- `priority`: Priority ranking (1-10)
- `confidence_score`: AI confidence in opportunity viability (0.0-1.0)

### 5. `error_patterns`
Common error patterns for intelligent troubleshooting and auto-resolution.

**Key Fields:**
- `error_hash`: SHA-256 hash of normalized error for deduplication
- `occurrence_count`: Number of times this error occurred
- `resolution`: How this error was resolved
- `auto_fixable`: Whether this error can be auto-fixed
- `severity`: Error severity level

### 6. `project_metrics`
Time-series performance and health metrics for projects.

**Key Fields:**
- `metric_type`: Type of metric (performance, health, usage, etc.)
- `value`: Numeric metric value
- `unit`: Unit of measurement (ms, %, count, etc.)
- `metadata` (JSONB): Additional metric context

## Views

### `project_dashboard`
Comprehensive view combining project information with runtime status, issues, and opportunities.

### `error_patterns_summary`
Aggregated view of error patterns by project and type.

### `monetization_ranking`
Ranked monetization opportunities with calculated opportunity scores.

## Example Queries

### Get Project Overview
```sql
SELECT * FROM project_dashboard 
WHERE name = 'Optimus';
```

### Find High-Priority Monetization Opportunities
```sql
SELECT project_name, description, potential_revenue, opportunity_score
FROM monetization_ranking
WHERE opportunity_score > 10000
ORDER BY opportunity_score DESC
LIMIT 10;
```

### Track Recent Errors
```sql
SELECT p.name, ep.error_type, ep.error_message, ep.occurrence_count
FROM error_patterns ep
JOIN projects p ON ep.project_id = p.id
WHERE ep.last_seen > NOW() - INTERVAL '24 hours'
ORDER BY ep.occurrence_count DESC;
```

### Monitor Running Processes
```sql
SELECT p.name, rs.process_name, rs.port, rs.cpu_usage, rs.memory_usage
FROM runtime_status rs
JOIN projects p ON rs.project_id = p.id
WHERE rs.status = 'running'
ORDER BY rs.cpu_usage DESC;
```

### Get Latest Analysis Scores
```sql
SELECT p.name, ar.analysis_type, ar.score, ar.issues_count
FROM analysis_results ar
JOIN projects p ON ar.project_id = p.id
WHERE ar.created_at = (
    SELECT MAX(created_at) 
    FROM analysis_results ar2 
    WHERE ar2.project_id = ar.project_id 
    AND ar2.analysis_type = ar.analysis_type
)
ORDER BY p.name, ar.analysis_type;
```

## Performance Considerations

### Indexing Strategy
- GIN indexes on JSONB columns for efficient JSON queries
- Composite indexes on frequently queried column combinations
- Partial indexes for filtered queries (e.g., active projects only)
- Time-based indexes for time-series data

### Auto-Vacuum Configuration
- Aggressive auto-vacuum settings for high-frequency tables
- Optimized vacuum settings for time-series tables

### Partitioning (Future)
- Consider partitioning project_metrics by time for large datasets
- Implement archival strategy for old data

## Security Features

### Row Level Security (RLS)
- Framework in place for multi-tenant scenarios
- Can be enabled per table as needed

### User Permissions
- Separate application user with minimal required permissions
- Read-only access for reporting users

## Triggers and Automation

### Automatic Timestamps
- `updated_at` fields automatically updated on record modification

### Error Deduplication
- Automatic error pattern deduplication based on error hash
- Occurrence count incrementation for duplicate errors

## Data Types and Constraints

### JSONB Usage
- Tech stack information
- Dependencies with versions
- Analysis results with flexible structure
- Market analysis data
- Configuration and metadata

### Validation Constraints
- CHECK constraints for enumerated values
- Foreign key constraints for data integrity
- UNIQUE constraints for preventing duplicates

## Migration and Versioning

### Schema Version Tracking
- `schema_version` table tracks applied migrations
- Incremental version numbering
- Migration descriptions and timestamps

### Future Considerations
- Plan for backward compatibility
- Data migration strategies for schema changes
- Backup and restore procedures

## Development and Testing

### Sample Data
- Representative test data included in schema
- Covers all major use cases and edge cases

### Local Development
- Docker Compose configuration available
- Seed data for realistic testing scenarios

## Monitoring and Maintenance

### Health Checks
- Monitor table sizes and growth rates
- Track query performance metrics
- Alert on unusual error patterns

### Regular Maintenance
- Scheduled VACUUM and ANALYZE operations
- Index usage monitoring
- Archive old data periodically

## API Integration

The schema is designed to support:
- RESTful API endpoints for all major entities
- GraphQL queries with efficient data fetching
- WebSocket real-time updates for runtime status
- Bulk operations for data imports/exports

## Related Documentation

- [Technical Architecture](../TECHNICAL_ARCHITECTURE.md)
- [API Documentation](../api/)
- [Development Setup Guide](../../README.md)