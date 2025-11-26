-- Optimus Database Schema
-- PostgreSQL 15+
-- Comprehensive project orchestrator database supporting project management,
-- runtime monitoring, code analysis, and monetization tracking

-- Create database
CREATE DATABASE optimus_db;
\c optimus_db;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- =============================================================================
-- CORE PROJECTS TABLE
-- =============================================================================
-- Central registry for all discovered and managed projects
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    path TEXT NOT NULL UNIQUE,
    description TEXT,
    tech_stack JSONB DEFAULT '{}', -- Store technology stack information
    dependencies JSONB DEFAULT '{}', -- Store project dependencies
    status VARCHAR(20) DEFAULT 'discovered' CHECK (status IN ('discovered', 'active', 'inactive', 'archived', 'error')),
    git_url TEXT, -- Repository URL
    default_branch VARCHAR(100) DEFAULT 'main', -- Default git branch
    last_commit_hash VARCHAR(64), -- SHA of last commit
    language_stats JSONB DEFAULT '{}', -- Programming language distribution
    last_scanned TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for projects table
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_path ON projects(path);
CREATE INDEX idx_projects_last_scanned ON projects(last_scanned);
CREATE INDEX idx_projects_tech_stack ON projects USING GIN (tech_stack);
CREATE INDEX idx_projects_dependencies ON projects USING GIN (dependencies);
CREATE INDEX idx_projects_language_stats ON projects USING GIN (language_stats);

-- =============================================================================
-- RUNTIME STATUS TABLE
-- =============================================================================
-- Track running processes and their resource consumption
CREATE TABLE runtime_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    process_name VARCHAR(255) NOT NULL, -- Name of the running process
    pid INTEGER, -- Process ID
    port INTEGER, -- Port number if applicable
    status VARCHAR(20) NOT NULL CHECK (status IN ('starting', 'running', 'stopped', 'error', 'crashed')),
    cpu_usage DECIMAL(5,2), -- CPU usage percentage
    memory_usage BIGINT, -- Memory usage in bytes
    started_at TIMESTAMP DEFAULT NOW(),
    last_heartbeat TIMESTAMP DEFAULT NOW(), -- Last health check timestamp
    stopped_at TIMESTAMP,
    error_message TEXT -- Error details if status is error/crashed
);

-- Indexes for runtime_status table
CREATE INDEX idx_runtime_project_id ON runtime_status(project_id);
CREATE INDEX idx_runtime_status ON runtime_status(status);
CREATE INDEX idx_runtime_active ON runtime_status(project_id, status) WHERE status IN ('starting', 'running');
CREATE INDEX idx_runtime_port ON runtime_status(port) WHERE port IS NOT NULL;
CREATE INDEX idx_runtime_heartbeat ON runtime_status(last_heartbeat DESC);

-- =============================================================================
-- ANALYSIS RESULTS TABLE
-- =============================================================================
-- Store code quality metrics and analysis outcomes
CREATE TABLE analysis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    analysis_type VARCHAR(50) NOT NULL, -- 'code_quality', 'security', 'performance', 'dependencies', etc.
    results JSONB NOT NULL, -- Detailed analysis results
    score DECIMAL(5,2), -- Numeric score (0-100)
    issues_count INTEGER DEFAULT 0, -- Number of issues found
    created_at TIMESTAMP DEFAULT NOW(),
    analyzer_version VARCHAR(20) -- Version of analysis tool used
);

-- Indexes for analysis_results table
CREATE INDEX idx_analysis_project_id ON analysis_results(project_id);
CREATE INDEX idx_analysis_type ON analysis_results(analysis_type);
CREATE INDEX idx_analysis_score ON analysis_results(score DESC);
CREATE INDEX idx_analysis_created_at ON analysis_results(created_at DESC);
CREATE INDEX idx_analysis_results ON analysis_results USING GIN (results);

-- =============================================================================
-- MONETIZATION OPPORTUNITIES TABLE
-- =============================================================================
-- Track revenue generation potential and business opportunities
CREATE TABLE monetization_opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    opportunity_type VARCHAR(50) NOT NULL, -- 'saas', 'marketplace', 'licensing', 'consulting', 'api', 'premium'
    description TEXT NOT NULL,
    potential_revenue DECIMAL(12,2), -- Estimated revenue potential
    effort_required VARCHAR(20) CHECK (effort_required IN ('low', 'medium', 'high', 'very_high')),
    priority INTEGER CHECK (priority BETWEEN 1 AND 10), -- Priority ranking 1-10
    status VARCHAR(20) DEFAULT 'identified' CHECK (status IN ('identified', 'evaluating', 'in_progress', 'implemented', 'on_hold', 'rejected')),
    confidence_score DECIMAL(3,2) CHECK (confidence_score BETWEEN 0 AND 1), -- Confidence in opportunity (0-1)
    market_analysis JSONB DEFAULT '{}', -- Market size, competition, etc.
    implementation_plan JSONB DEFAULT '{}', -- Steps to implement
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for monetization_opportunities table
CREATE INDEX idx_monetization_project_id ON monetization_opportunities(project_id);
CREATE INDEX idx_monetization_type ON monetization_opportunities(opportunity_type);
CREATE INDEX idx_monetization_status ON monetization_opportunities(status);
CREATE INDEX idx_monetization_priority ON monetization_opportunities(priority DESC);
CREATE INDEX idx_monetization_revenue ON monetization_opportunities(potential_revenue DESC);
CREATE INDEX idx_monetization_confidence ON monetization_opportunities(confidence_score DESC);

-- =============================================================================
-- ERROR PATTERNS TABLE
-- =============================================================================
-- Store and track common error patterns for intelligent troubleshooting
CREATE TABLE error_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    error_hash VARCHAR(64) NOT NULL, -- Hash of normalized error for deduplication
    error_message TEXT NOT NULL, -- Original error message
    stack_trace TEXT, -- Full stack trace if available
    file_path TEXT, -- File where error occurred
    line_number INTEGER, -- Line number of error
    error_type VARCHAR(100), -- Classification of error type
    occurrence_count INTEGER DEFAULT 1, -- Number of times this error occurred
    first_seen TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP DEFAULT NOW(),
    resolution TEXT, -- How this error was resolved (if resolved)
    resolution_confidence DECIMAL(3,2), -- Confidence in resolution (0-1)
    auto_fixable BOOLEAN DEFAULT FALSE, -- Whether this error can be auto-fixed
    severity VARCHAR(20) CHECK (severity IN ('low', 'medium', 'high', 'critical'))
);

-- Indexes for error_patterns table
CREATE INDEX idx_error_project_id ON error_patterns(project_id);
CREATE INDEX idx_error_hash ON error_patterns(error_hash);
CREATE INDEX idx_error_type ON error_patterns(error_type);
CREATE INDEX idx_error_occurrence ON error_patterns(occurrence_count DESC);
CREATE INDEX idx_error_last_seen ON error_patterns(last_seen DESC);
CREATE INDEX idx_error_severity ON error_patterns(severity);
CREATE UNIQUE INDEX idx_error_project_hash ON error_patterns(project_id, error_hash);

-- =============================================================================
-- PROJECT METRICS TABLE
-- =============================================================================
-- Time-series data for project performance and health metrics
CREATE TABLE project_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    metric_type VARCHAR(50) NOT NULL, -- 'performance', 'health', 'usage', 'code_quality', 'security'
    value DECIMAL(15,4) NOT NULL, -- Numeric metric value
    unit VARCHAR(20), -- Unit of measurement (ms, %, count, etc.)
    metadata JSONB DEFAULT '{}', -- Additional metric context
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Indexes for project_metrics table
CREATE INDEX idx_metrics_project_type ON project_metrics(project_id, metric_type);
CREATE INDEX idx_metrics_timestamp ON project_metrics(timestamp DESC);
CREATE INDEX idx_metrics_value ON project_metrics(value);
-- Partitioning index for time-series data
CREATE INDEX idx_metrics_time_partition ON project_metrics(timestamp, project_id);

-- =============================================================================
-- ADDITIONAL SUPPORTING TABLES
-- =============================================================================

-- Issues tracking (legacy compatibility - consider deprecating in favor of error_patterns)
CREATE TABLE issues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    category VARCHAR(50),
    description TEXT NOT NULL,
    error_message TEXT,
    stack_trace TEXT,
    file_path TEXT,
    line_number INTEGER,
    solution JSONB DEFAULT '{}',
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP,
    auto_fixed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for issues
CREATE INDEX idx_issues_project_severity ON issues(project_id, severity);
CREATE INDEX idx_issues_type ON issues(type);
CREATE INDEX idx_issues_resolved ON issues(resolved);

-- Learning patterns for troubleshooting
CREATE TABLE patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_type VARCHAR(50) NOT NULL, -- 'error', 'solution', 'optimization'
    pattern_signature VARCHAR(255) NOT NULL,
    pattern_data JSONB NOT NULL,
    solution_template JSONB DEFAULT '{}',
    success_rate DECIMAL(3,2) DEFAULT 0.0,
    usage_count INTEGER DEFAULT 0,
    last_used TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for patterns
CREATE INDEX idx_patterns_type ON patterns(pattern_type);
CREATE INDEX idx_patterns_signature ON patterns(pattern_signature);
CREATE INDEX idx_patterns_success ON patterns(success_rate DESC);

-- Project relationships and dependencies
CREATE TABLE project_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    depends_on_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    dependency_type VARCHAR(50), -- 'library', 'service', 'data', 'build'
    version VARCHAR(50),
    is_critical BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(project_id, depends_on_id, dependency_type)
);

-- Action history for audit
CREATE TABLE action_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    action_type VARCHAR(50) NOT NULL,
    action_details JSONB NOT NULL,
    initiated_by VARCHAR(50) DEFAULT 'system',
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    duration_ms INTEGER
);

-- Indexes for action history
CREATE INDEX idx_actions_project ON action_history(project_id);
CREATE INDEX idx_actions_timestamp ON action_history(started_at DESC);

-- Scheduled tasks
CREATE TABLE scheduled_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    task_type VARCHAR(50) NOT NULL,
    schedule_cron VARCHAR(50),
    next_run TIMESTAMP,
    last_run TIMESTAMP,
    enabled BOOLEAN DEFAULT TRUE,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

-- Voice interaction preparation (future)
CREATE TABLE conversation_context (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255) NOT NULL,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    user_input TEXT,
    system_response TEXT,
    intent VARCHAR(50),
    context JSONB DEFAULT '{}',
    timestamp TIMESTAMP DEFAULT NOW()
);

-- =============================================================================
-- TRIGGERS AND FUNCTIONS
-- =============================================================================

-- Function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

-- Function to update error pattern occurrence count and last_seen
CREATE OR REPLACE FUNCTION update_error_occurrence()
RETURNS TRIGGER AS $$
BEGIN
    -- If inserting and error hash already exists, update existing record
    IF TG_OP = 'INSERT' THEN
        UPDATE error_patterns 
        SET occurrence_count = occurrence_count + 1,
            last_seen = NOW()
        WHERE project_id = NEW.project_id 
        AND error_hash = NEW.error_hash;
        
        -- If update affected a row, don't insert the new record
        IF FOUND THEN
            RETURN NULL;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

-- Triggers for automatic timestamp updates
CREATE TRIGGER update_projects_modtime 
    BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER update_monetization_modtime 
    BEFORE UPDATE ON monetization_opportunities
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();

-- Trigger for error pattern deduplication
CREATE TRIGGER manage_error_patterns 
    BEFORE INSERT ON error_patterns
    FOR EACH ROW EXECUTE FUNCTION update_error_occurrence();

-- =============================================================================
-- VIEWS FOR EASY DATA ACCESS
-- =============================================================================

-- Comprehensive project dashboard view
CREATE VIEW project_dashboard AS
SELECT 
    p.id,
    p.name,
    p.path,
    p.description,
    p.status,
    p.tech_stack,
    p.git_url,
    p.default_branch,
    p.last_commit_hash,
    COALESCE(rs.is_running, FALSE) as is_running,
    COALESCE(rs.running_port, 0) as running_port,
    COALESCE(rs.process_count, 0) as process_count,
    COALESCE(i.open_issues, 0) as open_issues,
    COALESCE(i.critical_issues, 0) as critical_issues,
    COALESCE(e.error_count, 0) as recent_errors,
    COALESCE(m.opportunities_count, 0) as monetization_opportunities,
    COALESCE(m.total_potential_revenue, 0) as total_potential_revenue,
    COALESCE(a.latest_quality_score, 0) as latest_quality_score,
    p.last_scanned,
    p.updated_at
FROM projects p
LEFT JOIN LATERAL (
    SELECT 
        COUNT(*) > 0 as is_running, 
        MAX(port) as running_port,
        COUNT(*) as process_count
    FROM runtime_status 
    WHERE project_id = p.id AND status IN ('running', 'starting')
) rs ON TRUE
LEFT JOIN LATERAL (
    SELECT 
        COUNT(*) as open_issues,
        COUNT(*) FILTER (WHERE severity = 'critical') as critical_issues
    FROM issues 
    WHERE project_id = p.id AND resolved = FALSE
) i ON TRUE
LEFT JOIN LATERAL (
    SELECT COUNT(*) as error_count
    FROM error_patterns
    WHERE project_id = p.id AND last_seen > NOW() - INTERVAL '24 hours'
) e ON TRUE
LEFT JOIN LATERAL (
    SELECT 
        COUNT(*) as opportunities_count,
        SUM(potential_revenue) as total_potential_revenue
    FROM monetization_opportunities
    WHERE project_id = p.id AND status IN ('identified', 'evaluating', 'in_progress')
) m ON TRUE
LEFT JOIN LATERAL (
    SELECT score as latest_quality_score
    FROM analysis_results
    WHERE project_id = p.id AND analysis_type = 'code_quality'
    ORDER BY created_at DESC
    LIMIT 1
) a ON TRUE;

-- Error patterns summary view
CREATE VIEW error_patterns_summary AS
SELECT 
    p.name as project_name,
    ep.error_type,
    ep.severity,
    COUNT(*) as pattern_count,
    SUM(ep.occurrence_count) as total_occurrences,
    MAX(ep.last_seen) as most_recent_occurrence,
    COUNT(*) FILTER (WHERE ep.resolution IS NOT NULL) as resolved_patterns
FROM error_patterns ep
JOIN projects p ON ep.project_id = p.id
GROUP BY p.name, ep.error_type, ep.severity
ORDER BY total_occurrences DESC;

-- Monetization opportunities ranking view
CREATE VIEW monetization_ranking AS
SELECT 
    p.name as project_name,
    mo.opportunity_type,
    mo.description,
    mo.potential_revenue,
    mo.effort_required,
    mo.priority,
    mo.confidence_score,
    CASE 
        WHEN mo.effort_required = 'low' THEN mo.potential_revenue * mo.confidence_score * 1.5
        WHEN mo.effort_required = 'medium' THEN mo.potential_revenue * mo.confidence_score * 1.0
        WHEN mo.effort_required = 'high' THEN mo.potential_revenue * mo.confidence_score * 0.7
        ELSE mo.potential_revenue * mo.confidence_score * 0.5
    END as opportunity_score
FROM monetization_opportunities mo
JOIN projects p ON mo.project_id = p.id
WHERE mo.status IN ('identified', 'evaluating', 'in_progress')
ORDER BY opportunity_score DESC;

-- =============================================================================
-- SAMPLE DATA FOR DEVELOPMENT
-- =============================================================================

-- Sample projects
INSERT INTO projects (name, path, description, tech_stack, dependencies, status, git_url, default_branch, language_stats) VALUES
(
    'CoralCollective', 
    '/Users/nathanial.smalley/projects/coral_collective', 
    'AI development team framework with specialized agents',
    '{"language": "python", "framework": "fastapi", "database": "postgresql", "tools": ["claude", "openai"]}',
    '{"fastapi": "0.100.0", "uvicorn": "0.22.0", "sqlalchemy": "2.0.0", "pydantic": "2.0.0"}',
    'active',
    'https://github.com/user/coral_collective',
    'main',
    '{"python": 85.5, "yaml": 8.2, "markdown": 4.1, "shell": 2.2}'
),
(
    'Optimus', 
    '/Users/nathanial.smalley/projects/Optimus', 
    'Project orchestrator and management platform',
    '{"language": "python", "framework": "fastapi", "frontend": "react", "database": "postgresql"}',
    '{"fastapi": "0.100.0", "react": "18.2.0", "postgresql": "15.0", "redis": "7.0"}',
    'active',
    'https://github.com/user/Optimus',
    'main',
    '{"python": 78.3, "typescript": 15.7, "sql": 3.2, "css": 1.8, "html": 1.0}'
);

-- Sample analysis results
INSERT INTO analysis_results (project_id, analysis_type, results, score, issues_count) 
SELECT 
    p.id,
    'code_quality',
    '{"complexity": 3.2, "maintainability": 8.5, "test_coverage": 85.3, "duplication": 2.1}',
    85.3,
    12
FROM projects p WHERE p.name = 'CoralCollective';

-- Sample monetization opportunities
INSERT INTO monetization_opportunities 
(project_id, opportunity_type, description, potential_revenue, effort_required, priority, confidence_score, market_analysis)
SELECT 
    p.id,
    'saas',
    'AI agent marketplace subscription service',
    15000.00,
    'medium',
    8,
    0.75,
    '{"market_size": "large", "competition": "moderate", "growth_rate": "high"}'
FROM projects p WHERE p.name = 'CoralCollective';

-- Sample error patterns
INSERT INTO error_patterns (project_id, error_hash, error_message, error_type, occurrence_count, severity)
SELECT 
    p.id,
    'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    'Connection timeout to external API',
    'network_error',
    5,
    'medium'
FROM projects p WHERE p.name = 'Optimus';

-- =============================================================================
-- SECURITY AND PERMISSIONS
-- =============================================================================

-- Create application user (adjust credentials for production)
-- CREATE USER optimus_user WITH PASSWORD 'secure_password_here';

-- Grant appropriate permissions
-- GRANT CONNECT ON DATABASE optimus_db TO optimus_user;
-- GRANT USAGE ON SCHEMA public TO optimus_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO optimus_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO optimus_user;

-- Grant permissions on views
-- GRANT SELECT ON project_dashboard TO optimus_user;
-- GRANT SELECT ON error_patterns_summary TO optimus_user;
-- GRANT SELECT ON monetization_ranking TO optimus_user;

-- Row Level Security (RLS) can be added here for multi-tenant scenarios
-- ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY project_access ON projects FOR ALL TO optimus_user USING (true);

-- =============================================================================
-- PERFORMANCE AND MAINTENANCE
-- =============================================================================

-- Enable auto-vacuum for time-series tables
ALTER TABLE project_metrics SET (autovacuum_enabled = true, autovacuum_vacuum_scale_factor = 0.05);
ALTER TABLE runtime_status SET (autovacuum_enabled = true, autovacuum_vacuum_scale_factor = 0.1);

-- Consider partitioning for large time-series data (example for project_metrics)
-- CREATE TABLE project_metrics_y2024 PARTITION OF project_metrics 
-- FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

-- =============================================================================
-- SCHEMA DOCUMENTATION AND METADATA
-- =============================================================================

-- Add comments to tables for documentation
COMMENT ON TABLE projects IS 'Central registry of all discovered and managed projects';
COMMENT ON TABLE runtime_status IS 'Real-time tracking of running processes and resource consumption';
COMMENT ON TABLE analysis_results IS 'Results from automated code quality and security analysis';
COMMENT ON TABLE monetization_opportunities IS 'Identified revenue generation opportunities for projects';
COMMENT ON TABLE error_patterns IS 'Common error patterns for intelligent troubleshooting and auto-resolution';
COMMENT ON TABLE project_metrics IS 'Time-series performance and health metrics for projects';

-- Add column comments for key fields
COMMENT ON COLUMN projects.tech_stack IS 'JSON object containing technology stack information (languages, frameworks, tools)';
COMMENT ON COLUMN projects.dependencies IS 'JSON object containing project dependencies with versions';
COMMENT ON COLUMN projects.language_stats IS 'JSON object containing programming language distribution percentages';
COMMENT ON COLUMN runtime_status.last_heartbeat IS 'Timestamp of last health check - used for detecting stale processes';
COMMENT ON COLUMN error_patterns.error_hash IS 'SHA-256 hash of normalized error for deduplication';
COMMENT ON COLUMN monetization_opportunities.confidence_score IS 'AI confidence in opportunity viability (0.0 to 1.0)';

-- Schema version for migration tracking
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    description TEXT,
    applied_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO schema_version (version, description) VALUES 
(1, 'Initial comprehensive Optimus database schema with project orchestration support');