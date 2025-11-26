"""
Database Migration Definitions

Collection of all database migrations for schema evolution
and performance optimization across all database systems.
"""

from datetime import datetime
from .migrations import (
    MigrationRunner, PostgreSQLMigration, SQLiteMigration, DataMigration,
    MigrationInfo, create_migration_id, calculate_checksum
)
from .config import get_database_manager


def create_initial_optimizations_migration() -> PostgreSQLMigration:
    """Create initial PostgreSQL optimizations migration"""
    
    sql_up = """
    -- Enable required extensions
    CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
    CREATE EXTENSION IF NOT EXISTS pg_trgm;
    CREATE EXTENSION IF NOT EXISTS btree_gin;
    
    -- Create optimized indexes for projects table
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_health_dashboard 
    ON projects (status, health_score DESC, last_scanned DESC) 
    WHERE status IN ('active', 'discovered');
    
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_complexity_analysis 
    ON projects (complexity_score DESC, file_count DESC, total_lines DESC);
    
    -- Add new performance fields to projects table
    ALTER TABLE projects ADD COLUMN IF NOT EXISTS scan_duration_ms INTEGER;
    ALTER TABLE projects ADD COLUMN IF NOT EXISTS file_count INTEGER DEFAULT 0;
    ALTER TABLE projects ADD COLUMN IF NOT EXISTS total_lines INTEGER DEFAULT 0;
    ALTER TABLE projects ADD COLUMN IF NOT EXISTS complexity_score REAL DEFAULT 0.0;
    ALTER TABLE projects ADD COLUMN IF NOT EXISTS health_score REAL DEFAULT 1.0;
    
    -- Add constraints for new fields
    ALTER TABLE projects ADD CONSTRAINT IF NOT EXISTS check_health_score 
    CHECK (health_score >= 0.0 AND health_score <= 1.0);
    
    -- Optimize runtime_status table
    ALTER TABLE runtime_status ADD COLUMN IF NOT EXISTS disk_usage BIGINT;
    ALTER TABLE runtime_status ADD COLUMN IF NOT EXISTS network_io JSONB DEFAULT '{}';
    ALTER TABLE runtime_status ADD COLUMN IF NOT EXISTS restart_count INTEGER DEFAULT 0;
    
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_runtime_resource_monitoring 
    ON runtime_status (project_id, last_heartbeat DESC, cpu_usage DESC, memory_usage DESC)
    WHERE status IN ('running', 'starting');
    
    -- Enhance error_patterns table with ML features
    ALTER TABLE error_patterns ADD COLUMN IF NOT EXISTS error_signature JSONB DEFAULT '{}';
    ALTER TABLE error_patterns ADD COLUMN IF NOT EXISTS similar_patterns TEXT[];
    ALTER TABLE error_patterns ADD COLUMN IF NOT EXISTS fix_suggestions JSONB DEFAULT '[]';
    
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_error_patterns_ml_features 
    ON error_patterns USING gin (error_signature);
    
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_error_patterns_auto_fix 
    ON error_patterns (auto_fixable, severity, occurrence_count DESC) 
    WHERE auto_fixable = true;
    
    -- Enhance analysis_results with performance tracking
    ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS analysis_duration_ms INTEGER;
    ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS files_analyzed INTEGER DEFAULT 0;
    ALTER TABLE analysis_results ADD COLUMN IF NOT EXISTS lines_analyzed INTEGER DEFAULT 0;
    
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_analysis_performance_tracking 
    ON analysis_results (analysis_type, analysis_duration_ms, files_analyzed, created_at DESC);
    
    -- Optimize project_metrics for time-series queries
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_metrics_time_series_optimized 
    ON project_metrics (project_id, metric_type, timestamp DESC)
    INCLUDE (value, unit);
    
    CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_metrics_latest_values 
    ON project_metrics (project_id, metric_type, timestamp DESC) 
    WHERE timestamp >= NOW() - INTERVAL '1 day';
    
    -- Update table statistics
    ANALYZE projects;
    ANALYZE runtime_status;
    ANALYZE analysis_results;
    ANALYZE error_patterns;
    ANALYZE project_metrics;
    """
    
    sql_down = """
    -- Remove added columns (be careful with data loss)
    -- ALTER TABLE projects DROP COLUMN IF EXISTS scan_duration_ms;
    -- ALTER TABLE projects DROP COLUMN IF EXISTS file_count;
    -- ALTER TABLE projects DROP COLUMN IF EXISTS total_lines;
    -- ALTER TABLE projects DROP COLUMN IF EXISTS complexity_score;
    -- ALTER TABLE projects DROP COLUMN IF EXISTS health_score;
    
    -- Note: In production, consider keeping data and just removing indexes
    DROP INDEX CONCURRENTLY IF EXISTS idx_projects_health_dashboard;
    DROP INDEX CONCURRENTLY IF EXISTS idx_projects_complexity_analysis;
    DROP INDEX CONCURRENTLY IF EXISTS idx_runtime_resource_monitoring;
    DROP INDEX CONCURRENTLY IF EXISTS idx_error_patterns_ml_features;
    DROP INDEX CONCURRENTLY IF EXISTS idx_error_patterns_auto_fix;
    DROP INDEX CONCURRENTLY IF EXISTS idx_analysis_performance_tracking;
    DROP INDEX CONCURRENTLY IF EXISTS idx_metrics_time_series_optimized;
    DROP INDEX CONCURRENTLY IF EXISTS idx_metrics_latest_values;
    """
    
    migration_info = MigrationInfo(
        id=create_migration_id("initial_optimizations"),
        name="Initial Database Optimizations",
        description="Add performance fields and optimized indexes for enhanced monitoring",
        version="1.0.0",
        created_at=datetime.now(),
        checksum=calculate_checksum(sql_up),
        dependencies=[]
    )
    
    return PostgreSQLMigration(migration_info, sql_up, sql_down)


def create_materialized_views_migration() -> PostgreSQLMigration:
    """Create materialized views for dashboard performance"""
    
    sql_up = """
    -- Project health dashboard materialized view
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_project_health AS
    SELECT 
        p.id,
        p.name,
        p.path,
        p.status,
        p.health_score,
        p.complexity_score,
        p.last_scanned,
        p.file_count,
        p.total_lines,
        COALESCE(rs.active_processes, 0) as active_processes,
        COALESCE(rs.total_cpu_usage, 0) as total_cpu_usage,
        COALESCE(rs.total_memory_usage, 0) as total_memory_usage,
        COALESCE(rs.avg_restart_count, 0) as avg_restart_count,
        COALESCE(ep.critical_errors, 0) as critical_errors,
        COALESCE(ep.recent_errors, 0) as recent_errors,
        COALESCE(ep.auto_fixable_errors, 0) as auto_fixable_errors,
        COALESCE(ar.latest_score, 0) as latest_analysis_score,
        COALESCE(ar.issues_count, 0) as total_issues,
        COALESCE(ar.analysis_duration, 0) as last_analysis_duration
    FROM projects p
    LEFT JOIN LATERAL (
        SELECT 
            COUNT(*) as active_processes,
            SUM(cpu_usage) as total_cpu_usage,
            SUM(memory_usage) as total_memory_usage,
            AVG(restart_count) as avg_restart_count
        FROM runtime_status 
        WHERE project_id = p.id 
          AND status IN ('running', 'starting')
          AND last_heartbeat >= NOW() - INTERVAL '5 minutes'
    ) rs ON true
    LEFT JOIN LATERAL (
        SELECT 
            COUNT(*) FILTER (WHERE severity = 'critical') as critical_errors,
            COUNT(*) FILTER (WHERE last_seen >= NOW() - INTERVAL '24 hours') as recent_errors,
            COUNT(*) FILTER (WHERE auto_fixable = true AND resolution IS NULL) as auto_fixable_errors
        FROM error_patterns 
        WHERE project_id = p.id
    ) ep ON true
    LEFT JOIN LATERAL (
        SELECT 
            score as latest_score, 
            issues_count,
            analysis_duration_ms as analysis_duration
        FROM analysis_results 
        WHERE project_id = p.id 
        ORDER BY created_at DESC 
        LIMIT 1
    ) ar ON true
    WHERE p.status IN ('active', 'discovered');
    
    -- Create unique index for concurrent refresh
    CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_project_health_id ON mv_project_health (id);
    
    -- Error patterns insights materialized view
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_error_insights AS
    SELECT 
        error_type,
        severity,
        COUNT(*) as pattern_count,
        SUM(occurrence_count) as total_occurrences,
        AVG(occurrence_count) as avg_occurrences,
        MAX(last_seen) as most_recent,
        COUNT(*) FILTER (WHERE auto_fixable = true) as auto_fixable_count,
        COUNT(*) FILTER (WHERE resolution IS NOT NULL) as resolved_count,
        AVG(resolution_confidence) FILTER (WHERE resolution IS NOT NULL) as avg_confidence,
        -- Top fix suggestions
        (
            SELECT jsonb_agg(DISTINCT suggestion ORDER BY suggestion) 
            FROM error_patterns ep2, 
                 jsonb_array_elements_text(ep2.fix_suggestions) as suggestion
            WHERE ep2.error_type = ep.error_type 
              AND ep2.severity = ep.severity
              AND ep2.last_seen >= NOW() - INTERVAL '30 days'
            LIMIT 5
        ) as common_fixes
    FROM error_patterns ep
    WHERE last_seen >= NOW() - INTERVAL '30 days'
    GROUP BY error_type, severity
    ORDER BY total_occurrences DESC;
    
    -- Performance trends materialized view
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_performance_trends AS
    SELECT 
        p.id as project_id,
        p.name as project_name,
        m.metric_type,
        DATE_TRUNC('hour', m.timestamp) as time_bucket,
        AVG(m.value) as avg_value,
        MIN(m.value) as min_value,
        MAX(m.value) as max_value,
        STDDEV(m.value) as std_dev,
        COUNT(*) as data_points,
        -- Trend calculation (linear regression slope)
        CASE 
            WHEN COUNT(*) > 1 THEN
                (COUNT(*) * SUM(EXTRACT(EPOCH FROM m.timestamp) * m.value) - 
                 SUM(EXTRACT(EPOCH FROM m.timestamp)) * SUM(m.value)) /
                NULLIF(COUNT(*) * SUM(POWER(EXTRACT(EPOCH FROM m.timestamp), 2)) - 
                       POWER(SUM(EXTRACT(EPOCH FROM m.timestamp)), 2), 0)
            ELSE 0
        END as trend_slope
    FROM projects p
    JOIN project_metrics m ON p.id = m.project_id
    WHERE m.timestamp >= NOW() - INTERVAL '7 days'
      AND p.status = 'active'
    GROUP BY p.id, p.name, m.metric_type, DATE_TRUNC('hour', m.timestamp)
    ORDER BY p.name, m.metric_type, time_bucket;
    
    -- System performance summary view
    CREATE MATERIALIZED VIEW IF NOT EXISTS mv_system_performance AS
    SELECT 
        COUNT(DISTINCT p.id) as total_active_projects,
        COUNT(DISTINCT rs.id) as total_running_processes,
        SUM(rs.cpu_usage) as total_cpu_usage,
        SUM(rs.memory_usage) as total_memory_usage,
        COUNT(*) FILTER (WHERE ep.severity = 'critical') as critical_errors,
        COUNT(*) FILTER (WHERE ep.last_seen >= NOW() - INTERVAL '1 hour') as recent_errors,
        AVG(ar.score) as avg_code_quality_score,
        NOW() as last_updated
    FROM projects p
    LEFT JOIN runtime_status rs ON p.id = rs.project_id 
        AND rs.status IN ('running', 'starting')
        AND rs.last_heartbeat >= NOW() - INTERVAL '5 minutes'
    LEFT JOIN error_patterns ep ON p.id = ep.project_id 
        AND ep.last_seen >= NOW() - INTERVAL '24 hours'
    LEFT JOIN LATERAL (
        SELECT score 
        FROM analysis_results 
        WHERE project_id = p.id 
        ORDER BY created_at DESC 
        LIMIT 1
    ) ar ON true
    WHERE p.status = 'active';
    
    -- Refresh materialized views initially
    REFRESH MATERIALIZED VIEW mv_project_health;
    REFRESH MATERIALIZED VIEW mv_error_insights;
    REFRESH MATERIALIZED VIEW mv_performance_trends;
    REFRESH MATERIALIZED VIEW mv_system_performance;
    """
    
    sql_down = """
    DROP MATERIALIZED VIEW IF EXISTS mv_system_performance;
    DROP MATERIALIZED VIEW IF EXISTS mv_performance_trends;
    DROP MATERIALIZED VIEW IF EXISTS mv_error_insights;
    DROP MATERIALIZED VIEW IF EXISTS mv_project_health;
    """
    
    migration_info = MigrationInfo(
        id=create_migration_id("materialized_views"),
        name="Dashboard Materialized Views",
        description="Create materialized views for high-performance dashboard queries",
        version="1.0.0",
        created_at=datetime.now(),
        checksum=calculate_checksum(sql_up),
        dependencies=[]
    )
    
    return PostgreSQLMigration(migration_info, sql_up, sql_down)


def create_memory_db_optimization_migration() -> SQLiteMigration:
    """Create Memory database optimizations"""
    
    sql_up = """
    -- Add performance optimization fields to memories table
    ALTER TABLE memories ADD COLUMN content_hash TEXT;
    ALTER TABLE memories ADD COLUMN word_count INTEGER;
    ALTER TABLE memories ADD COLUMN compressed BOOLEAN DEFAULT 0;
    ALTER TABLE memories ADD COLUMN content_compressed BLOB;
    ALTER TABLE memories ADD COLUMN timestamp_unix INTEGER;
    ALTER TABLE memories ADD COLUMN last_accessed_unix INTEGER;
    
    -- Update existing records with computed values
    UPDATE memories SET 
        timestamp_unix = strftime('%s', timestamp),
        last_accessed_unix = strftime('%s', last_accessed),
        word_count = length(content) - length(replace(content, ' ', '')) + 1
    WHERE timestamp_unix IS NULL;
    
    -- Create optimized indexes
    CREATE INDEX IF NOT EXISTS idx_memories_persona_timestamp_opt 
    ON memories(persona_id, timestamp_unix DESC, importance DESC);
    
    CREATE INDEX IF NOT EXISTS idx_memories_persona_access_opt 
    ON memories(persona_id, access_count DESC, importance DESC);
    
    CREATE INDEX IF NOT EXISTS idx_memories_content_hash 
    ON memories(content_hash) WHERE content_hash IS NOT NULL;
    
    CREATE INDEX IF NOT EXISTS idx_memories_compressed 
    ON memories(compressed, timestamp_unix) WHERE compressed = 1;
    
    CREATE INDEX IF NOT EXISTS idx_memories_word_count 
    ON memories(word_count) WHERE word_count IS NOT NULL;
    
    -- Enhanced memory correlations with performance fields
    ALTER TABLE memory_correlations ADD COLUMN created_at_unix INTEGER;
    ALTER TABLE memory_correlations ADD COLUMN last_reinforced_unix INTEGER;
    ALTER TABLE memory_correlations ADD COLUMN reinforcement_count INTEGER DEFAULT 1;
    
    UPDATE memory_correlations SET 
        created_at_unix = strftime('%s', created_at),
        last_reinforced_unix = strftime('%s', created_at)
    WHERE created_at_unix IS NULL;
    
    CREATE INDEX IF NOT EXISTS idx_correlations_reinforcement 
    ON memory_correlations(reinforcement_count DESC, correlation_strength DESC);
    
    -- Query cache table for frequent memory queries
    CREATE TABLE IF NOT EXISTS query_cache (
        query_hash TEXT PRIMARY KEY,
        query_text TEXT,
        result_ids TEXT,
        cache_timestamp TEXT,
        cache_timestamp_unix INTEGER,
        hit_count INTEGER DEFAULT 1,
        persona_id TEXT
    );
    
    CREATE INDEX IF NOT EXISTS idx_cache_persona_hits 
    ON query_cache(persona_id, hit_count DESC);
    
    CREATE INDEX IF NOT EXISTS idx_cache_timestamp 
    ON query_cache(cache_timestamp_unix DESC);
    
    -- Memory statistics table for analytics
    CREATE TABLE IF NOT EXISTS memory_stats (
        persona_id TEXT PRIMARY KEY,
        total_memories INTEGER DEFAULT 0,
        compressed_memories INTEGER DEFAULT 0,
        avg_importance REAL DEFAULT 0.5,
        last_consolidation TEXT,
        last_consolidation_unix INTEGER,
        query_count INTEGER DEFAULT 0,
        last_query TEXT,
        last_query_unix INTEGER
    );
    
    -- Triggers for automatic maintenance
    CREATE TRIGGER IF NOT EXISTS update_memory_timestamp
    AFTER UPDATE OF access_count ON memories
    FOR EACH ROW
    BEGIN
        UPDATE memories SET 
            last_accessed_unix = strftime('%s', 'now'),
            last_accessed = datetime('now')
        WHERE id = NEW.id;
    END;
    
    -- Optimize SQLite settings
    PRAGMA optimize;
    ANALYZE;
    """
    
    sql_down = """
    -- Remove triggers
    DROP TRIGGER IF EXISTS update_memory_timestamp;
    
    -- Remove new tables
    DROP TABLE IF EXISTS memory_stats;
    DROP TABLE IF EXISTS query_cache;
    
    -- Remove indexes
    DROP INDEX IF EXISTS idx_memories_persona_timestamp_opt;
    DROP INDEX IF EXISTS idx_memories_persona_access_opt;
    DROP INDEX IF EXISTS idx_memories_content_hash;
    DROP INDEX IF EXISTS idx_memories_compressed;
    DROP INDEX IF EXISTS idx_memories_word_count;
    DROP INDEX IF EXISTS idx_correlations_reinforcement;
    DROP INDEX IF EXISTS idx_cache_persona_hits;
    DROP INDEX IF EXISTS idx_cache_timestamp;
    
    -- Note: Removing columns in SQLite requires recreating the table
    -- In production, consider keeping the columns for data preservation
    """
    
    migration_info = MigrationInfo(
        id=create_migration_id("memory_db_optimization"),
        name="Memory Database Optimization", 
        description="Add performance optimizations to SQLite memory database",
        version="1.0.0",
        created_at=datetime.now(),
        checksum=calculate_checksum(sql_up),
        dependencies=[]
    )
    
    return SQLiteMigration(migration_info, sql_up, sql_down, "memory")


def create_knowledge_graph_optimization_migration() -> SQLiteMigration:
    """Create Knowledge Graph database optimizations"""
    
    sql_up = """
    -- Add performance fields to nodes table
    ALTER TABLE nodes ADD COLUMN created_at_unix INTEGER;
    ALTER TABLE nodes ADD COLUMN updated_at_unix INTEGER;
    ALTER TABLE nodes ADD COLUMN last_accessed_unix INTEGER;
    ALTER TABLE nodes ADD COLUMN access_count INTEGER DEFAULT 0;
    ALTER TABLE nodes ADD COLUMN version INTEGER DEFAULT 1;
    ALTER TABLE nodes ADD COLUMN embedding_vector BLOB;
    ALTER TABLE nodes ADD COLUMN name_lower TEXT;
    ALTER TABLE nodes ADD COLUMN search_terms TEXT;
    
    -- Update existing records
    UPDATE nodes SET 
        created_at_unix = strftime('%s', created_at),
        updated_at_unix = strftime('%s', updated_at),
        name_lower = lower(name),
        search_terms = lower(name || ' ' || node_type)
    WHERE created_at_unix IS NULL;
    
    -- Add performance fields to edges table
    ALTER TABLE edges ADD COLUMN created_at_unix INTEGER;
    ALTER TABLE edges ADD COLUMN last_reinforced_unix INTEGER;
    ALTER TABLE edges ADD COLUMN last_reinforced TEXT;
    ALTER TABLE edges ADD COLUMN reinforcement_count INTEGER DEFAULT 1;
    ALTER TABLE edges ADD COLUMN decay_rate REAL DEFAULT 0.01;
    
    UPDATE edges SET 
        created_at_unix = strftime('%s', created_at),
        last_reinforced = created_at,
        last_reinforced_unix = strftime('%s', created_at)
    WHERE created_at_unix IS NULL;
    
    -- Create optimized indexes for graph traversal
    CREATE INDEX IF NOT EXISTS idx_nodes_type_importance 
    ON nodes(node_type, importance DESC, updated_at_unix DESC);
    
    CREATE INDEX IF NOT EXISTS idx_nodes_access_popularity 
    ON nodes(access_count DESC, importance DESC);
    
    CREATE INDEX IF NOT EXISTS idx_nodes_name_search 
    ON nodes(name_lower);
    
    CREATE INDEX IF NOT EXISTS idx_nodes_recent_important 
    ON nodes(updated_at_unix DESC, importance DESC) 
    WHERE importance > 0.5;
    
    -- Graph traversal optimized edge indexes
    CREATE INDEX IF NOT EXISTS idx_edges_source_type_weight 
    ON edges(source_id, edge_type, weight DESC);
    
    CREATE INDEX IF NOT EXISTS idx_edges_target_type_weight 
    ON edges(target_id, edge_type, weight DESC);
    
    CREATE INDEX IF NOT EXISTS idx_edges_bidirectional 
    ON edges(source_id, target_id, edge_type);
    
    CREATE INDEX IF NOT EXISTS idx_edges_weight_confidence 
    ON edges(weight DESC, confidence DESC, reinforcement_count DESC);
    
    -- Graph statistics table
    CREATE TABLE IF NOT EXISTS graph_stats (
        id INTEGER PRIMARY KEY,
        total_nodes INTEGER,
        total_edges INTEGER,
        avg_node_degree REAL,
        max_node_degree INTEGER,
        graph_density REAL,
        connected_components INTEGER,
        largest_component_size INTEGER,
        calculated_at TEXT,
        calculated_at_unix INTEGER
    );
    
    -- Subgraph cache for frequently accessed patterns
    CREATE TABLE IF NOT EXISTS subgraph_cache (
        cache_key TEXT PRIMARY KEY,
        subgraph_data BLOB,
        node_count INTEGER,
        edge_count INTEGER,
        created_at TEXT,
        created_at_unix INTEGER,
        access_count INTEGER DEFAULT 1,
        last_accessed TEXT,
        last_accessed_unix INTEGER
    );
    
    CREATE INDEX IF NOT EXISTS idx_subgraph_cache_access 
    ON subgraph_cache(access_count DESC, created_at_unix DESC);
    
    CREATE INDEX IF NOT EXISTS idx_subgraph_cache_size 
    ON subgraph_cache(node_count DESC, edge_count DESC);
    
    -- Node connectivity view for centrality calculations
    CREATE VIEW IF NOT EXISTS node_connectivity AS
    SELECT 
        n.id,
        n.name,
        n.node_type,
        n.importance,
        n.access_count,
        COUNT(DISTINCT e1.target_id) as out_degree,
        COUNT(DISTINCT e2.source_id) as in_degree,
        COUNT(DISTINCT e1.target_id) + COUNT(DISTINCT e2.source_id) as total_degree,
        AVG(e1.weight) as avg_out_weight,
        AVG(e2.weight) as avg_in_weight
    FROM nodes n
    LEFT JOIN edges e1 ON n.id = e1.source_id
    LEFT JOIN edges e2 ON n.id = e2.target_id
    GROUP BY n.id, n.name, n.node_type, n.importance, n.access_count;
    
    -- Triggers for automatic updates
    CREATE TRIGGER IF NOT EXISTS update_node_access
    AFTER UPDATE OF access_count ON nodes
    FOR EACH ROW
    BEGIN
        UPDATE nodes SET 
            last_accessed_unix = strftime('%s', 'now')
        WHERE id = NEW.id;
    END;
    
    CREATE TRIGGER IF NOT EXISTS update_edge_reinforcement
    AFTER UPDATE OF reinforcement_count ON edges
    FOR EACH ROW
    BEGIN
        UPDATE edges SET 
            last_reinforced = datetime('now'),
            last_reinforced_unix = strftime('%s', 'now')
        WHERE id = NEW.id;
    END;
    
    -- Optimize and analyze
    PRAGMA optimize;
    ANALYZE;
    """
    
    sql_down = """
    -- Remove triggers
    DROP TRIGGER IF EXISTS update_edge_reinforcement;
    DROP TRIGGER IF EXISTS update_node_access;
    
    -- Remove views
    DROP VIEW IF EXISTS node_connectivity;
    
    -- Remove new tables
    DROP TABLE IF EXISTS subgraph_cache;
    DROP TABLE IF EXISTS graph_stats;
    
    -- Remove indexes
    DROP INDEX IF EXISTS idx_nodes_type_importance;
    DROP INDEX IF EXISTS idx_nodes_access_popularity;
    DROP INDEX IF EXISTS idx_nodes_name_search;
    DROP INDEX IF EXISTS idx_nodes_recent_important;
    DROP INDEX IF EXISTS idx_edges_source_type_weight;
    DROP INDEX IF EXISTS idx_edges_target_type_weight;
    DROP INDEX IF EXISTS idx_edges_bidirectional;
    DROP INDEX IF EXISTS idx_edges_weight_confidence;
    DROP INDEX IF EXISTS idx_subgraph_cache_access;
    DROP INDEX IF EXISTS idx_subgraph_cache_size;
    """
    
    migration_info = MigrationInfo(
        id=create_migration_id("knowledge_graph_optimization"),
        name="Knowledge Graph Database Optimization",
        description="Add performance optimizations to SQLite knowledge graph database",
        version="1.0.0",
        created_at=datetime.now(),
        checksum=calculate_checksum(sql_up),
        dependencies=[]
    )
    
    return SQLiteMigration(migration_info, sql_up, sql_down, "knowledge")


async def register_all_migrations():
    """Register all database migrations"""
    db_manager = get_database_manager()
    runner = MigrationRunner(db_manager)
    await runner.initialize()
    
    # Register all migrations
    migrations = [
        create_initial_optimizations_migration(),
        create_materialized_views_migration(),
        create_memory_db_optimization_migration(),
        create_knowledge_graph_optimization_migration()
    ]
    
    for migration in migrations:
        runner.register_migration(migration)
    
    return runner


async def run_all_migrations():
    """Run all pending migrations"""
    runner = await register_all_migrations()
    
    print("Running database migrations...")
    
    # Run migrations for each database type
    success = await runner.run_migrations("all")
    
    if success:
        print("All migrations completed successfully!")
        
        # Show migration status
        status = await runner.get_migration_status()
        for db_type, db_status in status.items():
            print(f"\n{db_type.upper()} Database:")
            print(f"  Applied: {db_status['applied_count']} migrations")
            print(f"  Pending: {db_status['pending_count']} migrations")
    else:
        print("Migration errors occurred. Check logs for details.")
    
    return success