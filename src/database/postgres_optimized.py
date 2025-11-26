"""
Optimized PostgreSQL Database Operations

High-performance PostgreSQL operations with advanced indexing,
connection pooling, query optimization, and caching for the
Optimus project orchestrator system.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, Text, JSON,
    Index, ForeignKey, UniqueConstraint, CheckConstraint, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.sql import func
import uuid
from contextlib import asynccontextmanager

from .config import get_database_manager, DatabaseManager

Base = declarative_base()


class OptimizedProject(Base):
    """Optimized Project model with advanced indexing"""
    __tablename__ = 'projects'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    path = Column(Text, nullable=False, unique=True)
    description = Column(Text)
    tech_stack = Column(JSONB, default={})
    dependencies = Column(JSONB, default={})
    status = Column(String(20), default='discovered', nullable=False)
    git_url = Column(Text)
    default_branch = Column(String(100), default='main')
    last_commit_hash = Column(String(64))
    language_stats = Column(JSONB, default={})
    last_scanned = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Performance optimization fields
    scan_duration_ms = Column(Integer)  # Time taken for last scan
    file_count = Column(Integer, default=0)
    total_lines = Column(Integer, default=0)
    complexity_score = Column(Float, default=0.0)
    health_score = Column(Float, default=1.0)
    
    __table_args__ = (
        Index('idx_projects_status_active', 'status', postgresql_where=text("status IN ('active', 'discovered')")),
        Index('idx_projects_path_gin', 'path', postgresql_using='gin', postgresql_ops={'path': 'gin_trgm_ops'}),
        Index('idx_projects_name_gin', 'name', postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'}),
        Index('idx_projects_tech_stack_gin', 'tech_stack', postgresql_using='gin'),
        Index('idx_projects_dependencies_gin', 'dependencies', postgresql_using='gin'),
        Index('idx_projects_language_stats_gin', 'language_stats', postgresql_using='gin'),
        Index('idx_projects_health_score', 'health_score', 'last_scanned'),
        Index('idx_projects_complexity', 'complexity_score', 'file_count'),
        Index('idx_projects_scan_performance', 'scan_duration_ms', 'file_count'),
        CheckConstraint("status IN ('discovered', 'active', 'inactive', 'archived', 'error')", name='check_project_status'),
        CheckConstraint('health_score >= 0.0 AND health_score <= 1.0', name='check_health_score'),
    )


class OptimizedRuntimeStatus(Base):
    """Optimized Runtime Status model"""
    __tablename__ = 'runtime_status'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    process_name = Column(String(255), nullable=False)
    pid = Column(Integer)
    port = Column(Integer)
    status = Column(String(20), nullable=False)
    cpu_usage = Column(Float)
    memory_usage = Column(Integer)  # in bytes
    disk_usage = Column(Integer)   # in bytes (new field)
    network_io = Column(JSONB, default={})  # network I/O stats
    started_at = Column(DateTime, default=func.now())
    last_heartbeat = Column(DateTime, default=func.now())
    stopped_at = Column(DateTime)
    error_message = Column(Text)
    restart_count = Column(Integer, default=0)  # Track restarts
    
    __table_args__ = (
        Index('idx_runtime_project_status', 'project_id', 'status'),
        Index('idx_runtime_active_processes', 'project_id', 'status', 
              postgresql_where=text("status IN ('starting', 'running')")),
        Index('idx_runtime_port_active', 'port', postgresql_where=text("port IS NOT NULL AND status = 'running'")),
        Index('idx_runtime_heartbeat_stale', 'last_heartbeat', 
              postgresql_where=text("status IN ('running', 'starting')")),
        Index('idx_runtime_resource_usage', 'cpu_usage', 'memory_usage'),
        Index('idx_runtime_error_analysis', 'status', 'error_message', 
              postgresql_where=text("status IN ('error', 'crashed')")),
        CheckConstraint("status IN ('starting', 'running', 'stopped', 'error', 'crashed')", name='check_runtime_status'),
    )


class OptimizedAnalysisResults(Base):
    """Optimized Analysis Results model"""
    __tablename__ = 'analysis_results'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    analysis_type = Column(String(50), nullable=False)
    results = Column(JSONB, nullable=False)
    score = Column(Float)
    issues_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now())
    analyzer_version = Column(String(20))
    
    # Performance optimization fields
    analysis_duration_ms = Column(Integer)
    files_analyzed = Column(Integer, default=0)
    lines_analyzed = Column(Integer, default=0)
    
    __table_args__ = (
        Index('idx_analysis_project_type_latest', 'project_id', 'analysis_type', 'created_at'),
        Index('idx_analysis_score_ranking', 'analysis_type', 'score', 'created_at'),
        Index('idx_analysis_issues_critical', 'project_id', 'issues_count', 
              postgresql_where=text("issues_count > 0")),
        Index('idx_analysis_results_gin', 'results', postgresql_using='gin'),
        Index('idx_analysis_performance', 'analysis_duration_ms', 'files_analyzed'),
    )


class OptimizedErrorPatterns(Base):
    """Optimized Error Patterns model"""
    __tablename__ = 'error_patterns'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    error_hash = Column(String(64), nullable=False)
    error_message = Column(Text, nullable=False)
    stack_trace = Column(Text)
    file_path = Column(Text)
    line_number = Column(Integer)
    error_type = Column(String(100))
    occurrence_count = Column(Integer, default=1)
    first_seen = Column(DateTime, default=func.now())
    last_seen = Column(DateTime, default=func.now())
    resolution = Column(Text)
    resolution_confidence = Column(Float)
    auto_fixable = Column(Boolean, default=False)
    severity = Column(String(20), nullable=False)
    
    # AI/ML fields for pattern recognition
    error_signature = Column(JSONB, default={})  # ML feature vector
    similar_patterns = Column(ARRAY(String))     # Similar error hashes
    fix_suggestions = Column(JSONB, default=[])  # Automated fix suggestions
    
    __table_args__ = (
        Index('idx_error_project_hash_unique', 'project_id', 'error_hash', unique=True),
        Index('idx_error_frequency_analysis', 'error_type', 'occurrence_count', 'last_seen'),
        Index('idx_error_severity_recent', 'severity', 'last_seen'),
        Index('idx_error_auto_fixable', 'auto_fixable', postgresql_where=text("auto_fixable = true")),
        Index('idx_error_signature_gin', 'error_signature', postgresql_using='gin'),
        Index('idx_error_file_path_gin', 'file_path', postgresql_using='gin', postgresql_ops={'file_path': 'gin_trgm_ops'}),
        CheckConstraint("severity IN ('low', 'medium', 'high', 'critical')", name='check_error_severity'),
    )


class OptimizedProjectMetrics(Base):
    """Optimized Project Metrics model with time-series optimizations"""
    __tablename__ = 'project_metrics'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    metric_type = Column(String(50), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(20))
    metadata = Column(JSONB, default={})
    timestamp = Column(DateTime, default=func.now())
    
    __table_args__ = (
        # Time-series optimized indexes
        Index('idx_metrics_time_series', 'project_id', 'metric_type', 'timestamp'),
        Index('idx_metrics_latest_by_type', 'project_id', 'metric_type', 'timestamp', 
              postgresql_where=text("timestamp >= NOW() - INTERVAL '1 day'")),
        Index('idx_metrics_value_analysis', 'metric_type', 'value', 'timestamp'),
        Index('idx_metrics_metadata_gin', 'metadata', postgresql_using='gin'),
        
        # Partitioning preparation (can be used for table partitioning)
        Index('idx_metrics_partition_monthly', 'timestamp', postgresql_using='btree'),
    )


class PostgreSQLOptimizer:
    """
    High-performance PostgreSQL operations with advanced optimization features:
    - Async connection pooling
    - Query optimization and caching
    - Batch operations
    - Materialized views
    - Advanced indexing strategies
    - Performance monitoring
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager or get_database_manager()
        self.query_cache = {}
        self.performance_stats = {
            'queries_executed': 0,
            'cache_hits': 0,
            'avg_query_time': 0.0,
            'slow_queries': []
        }
    
    @asynccontextmanager
    async def get_session(self) -> AsyncSession:
        """Get an async database session with connection management"""
        session = await self.db_manager.get_postgres_session()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    async def create_optimized_indexes(self):
        """Create additional performance indexes"""
        async with self.get_session() as session:
            # Additional composite indexes for common query patterns
            indexes = [
                # Project analysis dashboard
                """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_projects_dashboard
                ON projects (status, health_score DESC, last_scanned DESC)
                WHERE status IN ('active', 'discovered')
                """,
                
                # Error pattern analysis
                """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_error_patterns_ml
                ON error_patterns (error_type, severity, auto_fixable, occurrence_count DESC)
                """,
                
                # Runtime monitoring
                """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_runtime_monitoring
                ON runtime_status (project_id, last_heartbeat DESC, cpu_usage DESC, memory_usage DESC)
                WHERE status IN ('running', 'starting')
                """,
                
                # Metrics trending
                """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_metrics_trending
                ON project_metrics (metric_type, timestamp DESC, value)
                WHERE timestamp >= NOW() - INTERVAL '7 days'
                """,
                
                # Analysis performance tracking
                """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_analysis_performance_tracking
                ON analysis_results (analysis_type, analysis_duration_ms, files_analyzed, created_at DESC)
                """
            ]
            
            for index_sql in indexes:
                try:
                    await session.execute(text(index_sql))
                    await session.commit()
                except Exception as e:
                    print(f"Index creation warning: {e}")
                    await session.rollback()
    
    async def create_materialized_views(self):
        """Create materialized views for dashboard queries"""
        async with self.get_session() as session:
            # Project health dashboard view
            await session.execute(text("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS mv_project_health AS
                SELECT 
                    p.id,
                    p.name,
                    p.path,
                    p.status,
                    p.health_score,
                    p.complexity_score,
                    p.last_scanned,
                    COALESCE(rs.active_processes, 0) as active_processes,
                    COALESCE(rs.total_cpu_usage, 0) as total_cpu_usage,
                    COALESCE(rs.total_memory_usage, 0) as total_memory_usage,
                    COALESCE(ep.critical_errors, 0) as critical_errors,
                    COALESCE(ep.recent_errors, 0) as recent_errors,
                    COALESCE(ar.latest_score, 0) as latest_analysis_score,
                    COALESCE(ar.issues_count, 0) as total_issues
                FROM projects p
                LEFT JOIN LATERAL (
                    SELECT 
                        COUNT(*) as active_processes,
                        SUM(cpu_usage) as total_cpu_usage,
                        SUM(memory_usage) as total_memory_usage
                    FROM runtime_status 
                    WHERE project_id = p.id 
                      AND status IN ('running', 'starting')
                      AND last_heartbeat >= NOW() - INTERVAL '5 minutes'
                ) rs ON true
                LEFT JOIN LATERAL (
                    SELECT 
                        COUNT(*) FILTER (WHERE severity = 'critical') as critical_errors,
                        COUNT(*) FILTER (WHERE last_seen >= NOW() - INTERVAL '24 hours') as recent_errors
                    FROM error_patterns 
                    WHERE project_id = p.id
                ) ep ON true
                LEFT JOIN LATERAL (
                    SELECT score as latest_score, issues_count
                    FROM analysis_results 
                    WHERE project_id = p.id 
                    ORDER BY created_at DESC 
                    LIMIT 1
                ) ar ON true
                WHERE p.status IN ('active', 'discovered')
            """))
            
            # Error pattern insights view
            await session.execute(text("""
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
                    AVG(resolution_confidence) FILTER (WHERE resolution IS NOT NULL) as avg_confidence
                FROM error_patterns 
                WHERE last_seen >= NOW() - INTERVAL '30 days'
                GROUP BY error_type, severity
                ORDER BY total_occurrences DESC
            """))
            
            # Performance metrics trends view  
            await session.execute(text("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS mv_performance_trends AS
                SELECT 
                    p.id as project_id,
                    p.name as project_name,
                    m.metric_type,
                    AVG(m.value) as avg_value,
                    MIN(m.value) as min_value,
                    MAX(m.value) as max_value,
                    STDDEV(m.value) as std_dev,
                    COUNT(*) as data_points,
                    DATE_TRUNC('hour', m.timestamp) as time_bucket
                FROM projects p
                JOIN project_metrics m ON p.id = m.project_id
                WHERE m.timestamp >= NOW() - INTERVAL '7 days'
                  AND p.status = 'active'
                GROUP BY p.id, p.name, m.metric_type, DATE_TRUNC('hour', m.timestamp)
                ORDER BY p.name, m.metric_type, time_bucket
            """))
            
            await session.commit()
    
    async def refresh_materialized_views(self):
        """Refresh materialized views for updated data"""
        async with self.get_session() as session:
            views = ['mv_project_health', 'mv_error_insights', 'mv_performance_trends']
            
            for view in views:
                try:
                    await session.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view}"))
                    await session.commit()
                except Exception as e:
                    print(f"View refresh warning for {view}: {e}")
                    await session.rollback()
    
    async def optimize_query_performance(self):
        """Apply PostgreSQL-specific performance optimizations"""
        async with self.get_session() as session:
            # Update PostgreSQL configuration for better performance
            optimizations = [
                # Increase work memory for complex queries
                "SET work_mem = '64MB'",
                
                # Optimize for analytics workloads
                "SET effective_cache_size = '2GB'",
                
                # Enable parallel query execution
                "SET max_parallel_workers_per_gather = 4",
                
                # Optimize random page cost for SSD
                "SET random_page_cost = 1.1",
                
                # Enable JIT for complex queries
                "SET jit = on"
            ]
            
            for optimization in optimizations:
                try:
                    await session.execute(text(optimization))
                except Exception as e:
                    print(f"Optimization warning: {e}")
    
    async def batch_insert_metrics(self, metrics_data: List[Dict[str, Any]]) -> int:
        """Optimized batch insert for metrics data"""
        if not metrics_data:
            return 0
        
        async with self.get_session() as session:
            # Prepare bulk insert
            values = []
            for metric in metrics_data:
                values.append({
                    'id': uuid.uuid4(),
                    'project_id': metric['project_id'],
                    'metric_type': metric['metric_type'],
                    'value': metric['value'],
                    'unit': metric.get('unit'),
                    'metadata': metric.get('metadata', {}),
                    'timestamp': metric.get('timestamp', datetime.now())
                })
            
            # Use bulk insert for better performance
            await session.execute(
                text("""
                    INSERT INTO project_metrics 
                    (id, project_id, metric_type, value, unit, metadata, timestamp)
                    SELECT 
                        (data->>'id')::uuid,
                        (data->>'project_id')::uuid,
                        data->>'metric_type',
                        (data->>'value')::float,
                        data->>'unit',
                        (data->>'metadata')::jsonb,
                        (data->>'timestamp')::timestamp
                    FROM jsonb_array_elements(:metrics_json) AS data
                """),
                {'metrics_json': json.dumps(values)}
            )
            
            await session.commit()
            return len(values)
    
    async def get_project_dashboard_data(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get optimized project dashboard data"""
        async with self.get_session() as session:
            # Use materialized view for performance
            result = await session.execute(text("""
                SELECT 
                    id::text,
                    name,
                    path,
                    status,
                    health_score,
                    complexity_score,
                    last_scanned,
                    active_processes,
                    total_cpu_usage,
                    total_memory_usage,
                    critical_errors,
                    recent_errors,
                    latest_analysis_score,
                    total_issues
                FROM mv_project_health
                ORDER BY 
                    CASE WHEN critical_errors > 0 THEN 0 ELSE 1 END,
                    health_score DESC,
                    latest_analysis_score DESC
                LIMIT :limit
            """), {'limit': limit})
            
            return [dict(row._mapping) for row in result.fetchall()]
    
    async def get_error_pattern_insights(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get error pattern insights with ML features"""
        async with self.get_session() as session:
            result = await session.execute(text("""
                SELECT 
                    ep.error_type,
                    ep.severity,
                    COUNT(*) as pattern_count,
                    SUM(ep.occurrence_count) as total_occurrences,
                    AVG(ep.occurrence_count) as avg_occurrences_per_pattern,
                    MAX(ep.last_seen) as most_recent_occurrence,
                    COUNT(*) FILTER (WHERE ep.auto_fixable = true) as auto_fixable_patterns,
                    COUNT(*) FILTER (WHERE ep.resolution IS NOT NULL) as resolved_patterns,
                    AVG(ep.resolution_confidence) FILTER (WHERE ep.resolution IS NOT NULL) as avg_resolution_confidence,
                    -- ML feature: error frequency trend
                    COUNT(*) FILTER (WHERE ep.last_seen >= NOW() - INTERVAL '24 hours') as last_24h_count,
                    COUNT(*) FILTER (WHERE ep.last_seen >= NOW() - INTERVAL '7 days') as last_7d_count,
                    -- Common fix suggestions
                    (
                        SELECT jsonb_agg(DISTINCT suggestion) 
                        FROM error_patterns ep2, jsonb_array_elements_text(ep2.fix_suggestions) as suggestion
                        WHERE ep2.error_type = ep.error_type AND ep2.severity = ep.severity
                        LIMIT 5
                    ) as common_fixes
                FROM error_patterns ep
                WHERE ep.last_seen >= NOW() - INTERVAL :days::text || ' days'
                GROUP BY ep.error_type, ep.severity
                HAVING SUM(ep.occurrence_count) > 5  -- Filter for significant patterns
                ORDER BY 
                    CASE ep.severity 
                        WHEN 'critical' THEN 1 
                        WHEN 'high' THEN 2 
                        WHEN 'medium' THEN 3 
                        ELSE 4 
                    END,
                    total_occurrences DESC
                LIMIT 100
            """), {'days': days})
            
            return [dict(row._mapping) for row in result.fetchall()]
    
    async def get_performance_trends(self, project_id: Optional[str] = None, hours: int = 24) -> List[Dict[str, Any]]:
        """Get performance metrics trends with statistical analysis"""
        async with self.get_session() as session:
            where_clause = ""
            params = {'hours': hours}
            
            if project_id:
                where_clause = "AND project_id = :project_id"
                params['project_id'] = project_id
            
            result = await session.execute(text(f"""
                WITH hourly_metrics AS (
                    SELECT 
                        project_id,
                        metric_type,
                        DATE_TRUNC('hour', timestamp) as hour,
                        AVG(value) as avg_value,
                        MIN(value) as min_value,
                        MAX(value) as max_value,
                        STDDEV(value) as stddev_value,
                        COUNT(*) as sample_count
                    FROM project_metrics
                    WHERE timestamp >= NOW() - INTERVAL :hours::text || ' hours' {where_clause}
                    GROUP BY project_id, metric_type, DATE_TRUNC('hour', timestamp)
                ),
                trend_analysis AS (
                    SELECT 
                        *,
                        -- Calculate trend using linear regression
                        REGR_SLOPE(avg_value, EXTRACT(EPOCH FROM hour)) as trend_slope,
                        REGR_R2(avg_value, EXTRACT(EPOCH FROM hour)) as trend_r2,
                        -- Detect anomalies (values > 2 standard deviations from mean)
                        CASE 
                            WHEN ABS(avg_value - AVG(avg_value) OVER (PARTITION BY project_id, metric_type)) 
                                 > 2 * STDDEV(avg_value) OVER (PARTITION BY project_id, metric_type)
                            THEN true 
                            ELSE false 
                        END as is_anomaly
                    FROM hourly_metrics
                )
                SELECT 
                    project_id::text,
                    metric_type,
                    hour,
                    avg_value,
                    min_value,
                    max_value,
                    stddev_value,
                    sample_count,
                    trend_slope,
                    trend_r2,
                    is_anomaly,
                    -- Performance classification
                    CASE 
                        WHEN trend_slope > 0.1 THEN 'improving'
                        WHEN trend_slope < -0.1 THEN 'degrading'
                        ELSE 'stable'
                    END as performance_trend
                FROM trend_analysis
                ORDER BY project_id, metric_type, hour
            """), params)
            
            return [dict(row._mapping) for row in result.fetchall()]
    
    async def analyze_slow_queries(self) -> List[Dict[str, Any]]:
        """Analyze slow queries using pg_stat_statements"""
        async with self.get_session() as session:
            try:
                # Enable pg_stat_statements if not already enabled
                await session.execute(text("CREATE EXTENSION IF NOT EXISTS pg_stat_statements"))
                
                result = await session.execute(text("""
                    SELECT 
                        query,
                        calls,
                        total_exec_time,
                        mean_exec_time,
                        max_exec_time,
                        rows,
                        100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) as hit_percent
                    FROM pg_stat_statements 
                    WHERE total_exec_time > 1000  -- queries taking more than 1 second total
                    ORDER BY mean_exec_time DESC
                    LIMIT 20
                """))
                
                return [dict(row._mapping) for row in result.fetchall()]
                
            except Exception as e:
                print(f"Could not analyze slow queries: {e}")
                return []
    
    async def vacuum_and_analyze(self, table_names: Optional[List[str]] = None):
        """Perform VACUUM and ANALYZE operations for performance maintenance"""
        tables = table_names or [
            'projects', 'runtime_status', 'analysis_results', 
            'error_patterns', 'project_metrics'
        ]
        
        async with self.get_session() as session:
            for table in tables:
                try:
                    # VACUUM ANALYZE updates statistics and reclaims space
                    await session.execute(text(f"VACUUM ANALYZE {table}"))
                    await session.commit()
                    print(f"Vacuumed and analyzed table: {table}")
                except Exception as e:
                    print(f"Maintenance warning for {table}: {e}")
                    await session.rollback()
    
    async def get_database_statistics(self) -> Dict[str, Any]:
        """Get comprehensive database performance statistics"""
        async with self.get_session() as session:
            # Database size and performance metrics
            stats = {}
            
            # Table sizes
            result = await session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes,
                    n_live_tup as live_rows,
                    n_dead_tup as dead_rows
                FROM pg_stat_user_tables
                ORDER BY size_bytes DESC
            """))
            
            stats['table_stats'] = [dict(row._mapping) for row in result.fetchall()]
            
            # Index usage
            result = await session.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_tup_read,
                    idx_tup_fetch,
                    idx_scan,
                    pg_relation_size(indexrelid) as index_size
                FROM pg_stat_user_indexes
                WHERE idx_scan > 0
                ORDER BY idx_scan DESC
                LIMIT 20
            """))
            
            stats['index_usage'] = [dict(row._mapping) for row in result.fetchall()]
            
            # Connection and activity stats
            result = await session.execute(text("""
                SELECT 
                    state,
                    COUNT(*) as connection_count,
                    AVG(EXTRACT(EPOCH FROM (NOW() - state_change))) as avg_duration_seconds
                FROM pg_stat_activity
                WHERE state IS NOT NULL
                GROUP BY state
            """))
            
            stats['connection_stats'] = [dict(row._mapping) for row in result.fetchall()]
            
            # Cache hit ratios
            result = await session.execute(text("""
                SELECT 
                    'database' as cache_type,
                    SUM(blks_hit) as hits,
                    SUM(blks_read) as reads,
                    SUM(blks_hit) * 100.0 / NULLIF(SUM(blks_hit + blks_read), 0) as hit_ratio
                FROM pg_stat_database
                WHERE datname = current_database()
                UNION ALL
                SELECT 
                    'table' as cache_type,
                    SUM(heap_blks_hit) as hits,
                    SUM(heap_blks_read) as reads,
                    SUM(heap_blks_hit) * 100.0 / NULLIF(SUM(heap_blks_hit + heap_blks_read), 0) as hit_ratio
                FROM pg_statio_user_tables
            """))
            
            stats['cache_stats'] = [dict(row._mapping) for row in result.fetchall()]
            
            return stats
    
    async def setup_automatic_maintenance(self):
        """Setup automatic database maintenance tasks"""
        async with self.get_session() as session:
            # Create maintenance functions
            maintenance_functions = [
                # Auto-refresh materialized views
                """
                CREATE OR REPLACE FUNCTION refresh_dashboard_views()
                RETURNS void AS $$
                BEGIN
                    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_project_health;
                    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_error_insights;
                    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_performance_trends;
                END;
                $$ LANGUAGE plpgsql;
                """,
                
                # Cleanup old metrics data
                """
                CREATE OR REPLACE FUNCTION cleanup_old_metrics()
                RETURNS integer AS $$
                DECLARE
                    deleted_count integer;
                BEGIN
                    DELETE FROM project_metrics 
                    WHERE timestamp < NOW() - INTERVAL '90 days';
                    GET DIAGNOSTICS deleted_count = ROW_COUNT;
                    RETURN deleted_count;
                END;
                $$ LANGUAGE plpgsql;
                """,
                
                # Auto-resolve old error patterns
                """
                CREATE OR REPLACE FUNCTION auto_resolve_patterns()
                RETURNS integer AS $$
                DECLARE
                    resolved_count integer;
                BEGIN
                    UPDATE error_patterns 
                    SET resolution = 'Auto-resolved: No occurrences in 30 days',
                        resolution_confidence = 0.7
                    WHERE last_seen < NOW() - INTERVAL '30 days'
                      AND resolution IS NULL
                      AND severity IN ('low', 'medium')
                      AND occurrence_count < 10;
                    GET DIAGNOSTICS resolved_count = ROW_COUNT;
                    RETURN resolved_count;
                END;
                $$ LANGUAGE plpgsql;
                """
            ]
            
            for func_sql in maintenance_functions:
                try:
                    await session.execute(text(func_sql))
                    await session.commit()
                except Exception as e:
                    print(f"Function creation warning: {e}")
                    await session.rollback()


# Global PostgreSQL optimizer instance
_postgres_optimizer: Optional[PostgreSQLOptimizer] = None


def get_postgres_optimizer() -> PostgreSQLOptimizer:
    """Get the global PostgreSQL optimizer instance"""
    global _postgres_optimizer
    if _postgres_optimizer is None:
        _postgres_optimizer = PostgreSQLOptimizer()
    return _postgres_optimizer