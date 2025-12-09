-- PostgreSQL development initialization script for Optimus

-- Create extensions for development
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create test database
CREATE DATABASE optimus_test_db;

-- Create development user
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'optimus_dev') THEN
      CREATE USER optimus_dev WITH PASSWORD 'dev_password' CREATEDB;
   END IF;
END
$$;

-- Grant permissions for development
GRANT ALL PRIVILEGES ON DATABASE optimus_dev_db TO optimus_dev;
GRANT ALL PRIVILEGES ON DATABASE optimus_test_db TO optimus_dev;

-- Connect to development database
\c optimus_dev_db;

GRANT ALL PRIVILEGES ON SCHEMA public TO optimus_dev;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO optimus_dev;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO optimus_dev;

-- Connect to test database
\c optimus_test_db;

GRANT ALL PRIVILEGES ON SCHEMA public TO optimus_dev;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO optimus_dev;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO optimus_dev;

-- Development optimizations
ALTER SYSTEM SET fsync = off;
ALTER SYSTEM SET synchronous_commit = off;
ALTER SYSTEM SET full_page_writes = off;
ALTER SYSTEM SET checkpoint_segments = 32;
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';

-- Detailed logging for development
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_min_duration_statement = 0;
ALTER SYSTEM SET log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h ';

-- Reload configuration
SELECT pg_reload_conf();